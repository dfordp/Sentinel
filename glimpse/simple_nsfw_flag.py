#!/usr/bin/env python3
"""
Simple NSFW flagging script based on text content analysis
"""

import os
import logging
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
import re
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# NSFW keywords to search for
NSFW_KEYWORDS = [
    # Explicit content
    'porn', 'pornography', 'xxx', 'adult', 'nude', 'naked', 'sex', 'sexual',
    'erotic', 'fetish', 'bdsm', 'kink', 'masturbat', 'orgasm', 'penis', 'vagina',
    'breast', 'boob', 'ass', 'butt', 'dick', 'cock', 'pussy', 'tits', 'titties',
    
    # Violence and disturbing content
    'gore', 'blood', 'violence', 'murder', 'kill', 'death', 'suicide', 'torture',
    'rape', 'abuse', 'pedophil', 'child porn', 'underage',
    
    # Drugs and illegal content
    'cocaine', 'heroin', 'meth', 'crack', 'drugs', 'weed', 'marijuana', 'cannabis',
    'lsd', 'ecstasy', 'mdma', 'pills', 'overdose',
    
    # Hate speech and discrimination
    'nazi', 'hitler', 'fascist', 'racist', 'sexist', 'homophobic', 'transphobic',
    'slur', 'hate speech', 'discrimination',
    
    # Other inappropriate content
    'scam', 'fraud', 'illegal', 'stolen', 'hack', 'malware', 'virus', 'phishing'
]

# Safe content indicators (if these are present, might be educational/medical)
SAFE_CONTEXT = [
    'educational', 'medical', 'research', 'study', 'academic', 'news', 'article',
    'documentary', 'history', 'science', 'health', 'therapy', 'treatment'
]

CHROMA_PERSIST_DIR = os.path.join("index_data", "chroma_db")

def is_nsfw_content(text: str, url: str = "") -> Dict[str, Any]:
    """
    Simple text-based NSFW detection
    """
    if not text:
        return {"is_nsfw": False, "nsfw_score": 0.0, "nsfw_confidence": 0.0, "matched_keywords": []}
    
    text_lower = text.lower()
    url_lower = url.lower() if url else ""
    combined_text = f"{text_lower} {url_lower}"
    
    matched_keywords = []
    nsfw_score = 0.0
    
    # Check for NSFW keywords
    for keyword in NSFW_KEYWORDS:
        if keyword in combined_text:
            matched_keywords.append(keyword)
            # Weight different types of content
            if keyword in ['porn', 'pornography', 'xxx', 'adult']:
                nsfw_score += 0.8
            elif keyword in ['nude', 'naked', 'sex', 'sexual']:
                nsfw_score += 0.6
            elif keyword in ['gore', 'violence', 'murder', 'kill']:
                nsfw_score += 0.7
            elif keyword in ['drugs', 'cocaine', 'heroin']:
                nsfw_score += 0.5
            else:
                nsfw_score += 0.4
    
    # Check for safe context (reduce score if present)
    safe_context_found = False
    for safe_word in SAFE_CONTEXT:
        if safe_word in combined_text:
            safe_context_found = True
            nsfw_score *= 0.3  # Reduce score significantly if safe context is present
            break
    
    # Normalize score to 0-1 range
    nsfw_score = min(nsfw_score, 1.0)
    
    # Determine if NSFW based on score and keywords
    is_nsfw = nsfw_score > 0.3 and len(matched_keywords) > 0
    
    # Calculate confidence based on score and number of matches
    confidence = min(nsfw_score + (len(matched_keywords) * 0.1), 1.0)
    
    return {
        "is_nsfw": is_nsfw,
        "nsfw_score": round(nsfw_score, 3),
        "nsfw_confidence": round(confidence, 3),
        "matched_keywords": matched_keywords
    }

def process_collection(collection, collection_name: str):
    """
    Process a single collection to add NSFW flags
    """
    logger.info(f"🔄 Processing collection: {collection_name}")
    
    # Get total count
    total_count = collection.count()
    logger.info(f"📊 Total entries: {total_count}")
    
    if total_count == 0:
        logger.info(f"⏭️  Skipping empty collection: {collection_name}")
        return
    
    processed = 0
    flagged = 0
    
    # Process in batches
    batch_size = 100
    offset = 0
    
    # Create progress bar
    pbar = tqdm(total=total_count, desc=f"Processing {collection_name}", unit="entries")
    
    while offset < total_count:
        try:
            # Get batch of entries
            results = collection.get(
                limit=batch_size,
                offset=offset,
                include=['metadatas', 'documents']
            )
            
            if not results['ids']:
                break
            
            batch_updates = []
            
            for i, (entry_id, metadata, document) in enumerate(zip(
                results['ids'], 
                results['metadatas'], 
                results['documents']
            )):
                # Skip if already processed
                if metadata and 'is_nsfw' in metadata:
                    continue
                
                # Extract text content for analysis
                text_content = ""
                url = ""
                
                if document:
                    text_content = str(document)
                
                if metadata:
                    url = metadata.get('url', '')
                    # Also check title, description, etc.
                    if 'title' in metadata:
                        text_content += f" {metadata['title']}"
                    if 'description' in metadata:
                        text_content += f" {metadata['description']}"
                
                # Analyze for NSFW content
                nsfw_result = is_nsfw_content(text_content, url)
                
                # Prepare metadata update
                updated_metadata = metadata.copy() if metadata else {}
                updated_metadata.update({
                    'is_nsfw': nsfw_result['is_nsfw'],
                    'nsfw_score': nsfw_result['nsfw_score'],
                    'nsfw_confidence': nsfw_result['nsfw_confidence'],
                    'nsfw_keywords': ','.join(nsfw_result['matched_keywords']) if nsfw_result['matched_keywords'] else ''
                })
                
                batch_updates.append({
                    'id': entry_id,
                    'metadata': updated_metadata
                })
                
                if nsfw_result['is_nsfw']:
                    flagged += 1
                    logger.info(f"🚩 Flagged: {entry_id[:50]}... (score: {nsfw_result['nsfw_score']}, keywords: {nsfw_result['matched_keywords']})")
                
                processed += 1
                
                # Update progress bar
                pbar.update(1)
                pbar.set_postfix({"Flagged": flagged})
            
            # Update batch in ChromaDB
            if batch_updates:
                for update in batch_updates:
                    try:
                        collection.update(
                            ids=[update['id']],
                            metadatas=[update['metadata']]
                        )
                    except Exception as e:
                        logger.error(f"Failed to update {update['id']}: {e}")
            
            offset += batch_size
            
        except Exception as e:
            logger.error(f"Error processing batch at offset {offset}: {e}")
            offset += batch_size
            continue
    
    # Close progress bar
    pbar.close()
    
    logger.info(f"✅ Completed {collection_name}: {processed} processed, {flagged} flagged")

def main():
    """
    Main function to process all collections
    """
    logger.info("🚀 Starting simple NSFW flagging based on text content")
    logger.info(f"🔍 NSFW keywords: {len(NSFW_KEYWORDS)}")
    
    # Connect to ChromaDB
    logger.info("🔄 Connecting to ChromaDB...")
    client = chromadb.PersistentClient(
        path=CHROMA_PERSIST_DIR,
        settings=Settings(anonymized_telemetry=False)
    )
    
    # Get all collections
    collections = client.list_collections()
    logger.info(f"📚 Found {len(collections)} collections")
    
    total_processed = 0
    total_flagged = 0
    
    # Create overall progress bar for collections
    collection_pbar = tqdm(collections, desc="Processing collections", unit="collection")
    
    for collection_info in collection_pbar:
        collection_name = collection_info.name
        collection = client.get_collection(collection_name)
        
        try:
            process_collection(collection, collection_name)
            # Update collection progress bar
            collection_pbar.set_postfix({"Total Flagged": total_flagged})
        except Exception as e:
            logger.error(f"Failed to process collection {collection_name}: {e}")
            continue
    
    # Close collection progress bar
    collection_pbar.close()
    
    logger.info("🎉 NSFW flagging completed!")
    logger.info(f"📊 Total processed: {total_processed}, Total flagged: {total_flagged}")

if __name__ == "__main__":
    main()
