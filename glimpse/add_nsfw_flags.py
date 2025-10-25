#!/usr/bin/env python3
"""
Minimal, fast NSFW flagging using the hosted search endpoints.

- Queries the main service (per modality, per tag)
- Maps results back to Chroma items by url/txid/title
- Writes 'is_nsfw', 'nsfw_keywords', and confidence
"""

import chromadb
from chromadb.config import Settings
import os
import requests
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BATCH_SIZE = int(os.getenv("NSFW_UPDATE_BATCH", "100"))
NSFW_THRESHOLD = float(os.getenv("NSFW_THRESHOLD", "0.24"))
USE_REMOTE_SEARCH = True

# Remote search configuration
REMOTE_BASE_URL = os.getenv("REMOTE_SEARCH_BASE_URL", "https://arfetch.adityaberry.me")
REMOTE_TIMEOUT = float(os.getenv("REMOTE_SEARCH_TIMEOUT", "20"))

DEFAULT_TAGS = [
    "nsfw", "porn", "xxx", "adult", "explicit", "sexual", "nude", "naked",
    "erotic", "fetish", "bdsm", "hentai", "boobs", "breasts", "nipples",
    "cumshot", "blowjob", "anal", "pussy", "vagina", "dick", "penis",
    "lingerie", "pornstar", "lewd"
]
TAGS = [t.strip() for t in os.getenv("NSFW_TAGS", ",".join(DEFAULT_TAGS)).split(",") if t.strip()]

# No local model needed in remote-search mode

# Local embedding helpers removed

# Local zero-shot path removed for minimalism and speed

def _collection_to_modality(collection_name: str) -> str:
    name = collection_name.lower()
    if "image" in name:
        return "image"
    if "video" in name:
        return "video"
    if "audio" in name:
        return "audio"
    if "web" in name or "all" in name:
        return "web"
    return "web"

def _remote_search(modality: str, query: str, n_results: int) -> list:
    endpoint_map = {
        "image": "/searchimage",
        "video": "/searchvideo",
        "audio": "/searchaudio",
        "web": "/searchweb",
    }
    path = endpoint_map.get(modality, "/searchweb")
    url = f"{REMOTE_BASE_URL}{path}"
    params = {
        "q": query,
        "n_results": n_results,
        "filter_nsfw": "false",
    }
    resp = requests.get(url, params=params, timeout=REMOTE_TIMEOUT)
    resp.raise_for_status()
    data_json = resp.json() or {}
    return data_json.get("results", [])

def _find_ids_by_urls(collection, urls: list) -> list:
    found_ids = []
    for u in urls:
        try:
            # Try match by exact url in metadata
            got = collection.get(where={"url": u}) or {}
            ids = got.get("ids") or []
            if ids:
                found_ids.extend(ids)
                continue
            # Fallback: sometimes txid equals url
            got2 = collection.get(where={"txid": u}) or {}
            ids2 = got2.get("ids") or []
            if ids2:
                found_ids.extend(ids2)
                continue
            # Fallback by title/description exact
            got3 = collection.get(where={"title": u}) or {}
            ids3 = got3.get("ids") or []
            if ids3:
                found_ids.extend(ids3)
                continue
            got4 = collection.get(where={"description": u}) or {}
            ids4 = got4.get("ids") or []
            if ids4:
                found_ids.extend(ids4)
        except Exception as e:
            logger.error(f"Lookup by url failed for {u}: {e}")
    return found_ids

def process_collection(collection, model, collection_name):
    """Process a single collection to add NSFW flags"""
    print(f"\n🔄 Processing collection: {collection_name}")
    
    # Get total count
    total_count = collection.count()
    print(f"📊 Total entries: {total_count}")
    
    if total_count == 0:
        print("⚠️ Collection is empty, skipping...")
        return
    
    # Remote main-service search (only path)
    if USE_REMOTE_SEARCH:
        modality = _collection_to_modality(collection_name)
        print(f"⚡ Using remote search on '{modality}' for NSFW tagging")
        id_to_tags = {}
        # wider result pool to catch borderline
        top_k = max(1000, min(10000, int(total_count * 0.10)))
        for tag in TAGS:
            try:
                results = _remote_search(modality, tag, top_k)
            except Exception as e:
                logger.error(f"Remote search failed for tag '{tag}': {e}")
                continue
            # collect urls above threshold
            urls = []
            for r in results:
                try:
                    score = float(r.get("score", 0.0))
                    url_val = r.get("url") or r.get("txid") or r.get("title")
                    if not url_val:
                        continue
                    if score >= NSFW_THRESHOLD:
                        urls.append(url_val)
                except Exception:
                    continue
            if not urls:
                continue
            ids = _find_ids_by_urls(collection, urls)
            for _id in ids:
                id_to_tags.setdefault(_id, set()).add(tag)
        if not id_to_tags:
            print("ℹ️  No NSFW matches found via remote search for this collection")
            return
        updated_ids = []
        updated_metadatas = []
        ids_list = list(id_to_tags.keys())
        print(f"📝 Updating {len(ids_list)} items flagged by remote search")
        for i in range(0, len(ids_list), BATCH_SIZE):
            batch_ids = ids_list[i:i+BATCH_SIZE]
            batch = collection.get(ids=batch_ids, include=["metadatas"]) or {}
            metas = (batch.get('metadatas') or [])
            batch_updated_ids = []
            batch_updated_metas = []
            for j, _id in enumerate(batch_ids):
                md = metas[j] if j < len(metas) and metas[j] else {}
                tags = sorted(list(id_to_tags[_id]))
                md.update({
                    'is_nsfw': True,
                    'nsfw_score': 1.0,
                    'nsfw_confidence': 1.0,
                    'nsfw_keywords': ','.join(tags)
                })
                batch_updated_ids.append(_id)
                batch_updated_metas.append(md)
            if batch_updated_ids:
                collection.update(ids=batch_updated_ids, metadatas=batch_updated_metas)
                print(f"✅ Updated {len(batch_updated_ids)} items via remote search")
        return
    # No local fallback paths

def main():
    """Main function to process all collections"""
    print("🚀 Starting NSFW flagging (remote search mode)")
    print(f"📏 Update batch: {BATCH_SIZE}")
    print(f"🎯 NSFW threshold: {NSFW_THRESHOLD}")
    print(f"🌐 Remote base: {REMOTE_BASE_URL}")
    
    # Initialize ChromaDB client
    print("\n🔄 Connecting to ChromaDB...")
    chroma_client = chromadb.PersistentClient(
        path="index_data/chroma_db",
        settings=Settings(anonymized_telemetry=False, allow_reset=True)
    )
    
    # Get all collections
    collections = chroma_client.list_collections()
    print(f"📚 Found {len(collections)} collections")
    
    # Process each collection
    for collection_info in collections:
        collection_name = collection_info.name
        collection = chroma_client.get_collection(collection_name)
        
        # Skip ARNS collection if it's empty
        if collection_name == "arweave_arns" and collection.count() == 0:
            print(f"⏭️ Skipping empty collection: {collection_name}")
            continue
        
        process_collection(collection, None, collection_name)
    
    print("\n🎉 NSFW flagging complete!")
    print("💡 Updated 'is_nsfw' flags written to metadata")

if __name__ == "__main__":
    main()
