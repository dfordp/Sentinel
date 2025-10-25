# Complete Multimodal Arweave Indexer using ImageBind + ChromaDB

import os
import io
import json
import time
import threading
import requests
import numpy as np
from PIL import Image
from bs4 import BeautifulSoup
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import torchaudio
import av
import torch
from imagebind import data
from imagebind.models import imagebind_model
from imagebind.models.imagebind_model import ModalityType
from imagebind.data import load_and_transform_audio_data
import chromadb
from chromadb.config import Settings
import mimetypes
import logging
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
import soundfile as sf
import librosa
import subprocess
import uuid
import re
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
from contextlib import asynccontextmanager

print("✅ All imports completed successfully")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
)
logger = logging.getLogger(__name__)

# Suppress PostHog/telemetry warnings
logging.getLogger("posthog").setLevel(logging.ERROR)
logging.getLogger("chromadb.telemetry").setLevel(logging.ERROR)

# Add file handler for logging to 'indexer.log'
file_handler = logging.FileHandler('indexer.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s'))
logger.addHandler(file_handler)

# ==== Config ====
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DATA_DIR = "index_data"
os.makedirs(DATA_DIR, exist_ok=True)
MODALITIES = ["web", "image", "audio", "video", "all"]

# CUDA optimization settings
if torch.cuda.is_available():
    torch.backends.cudnn.benchmark = True
    torch.backends.cudnn.deterministic = False
    print("✅ CUDA optimizations enabled")

# Check if ffmpeg is available for audio/video processing
def check_ffmpeg():
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

FFMPEG_AVAILABLE = check_ffmpeg()
if FFMPEG_AVAILABLE:
    logger.info("✅ FFmpeg is available for audio/video processing")
else:
    logger.warning("⚠️ FFmpeg not available - some audio/video formats may not be supported")

# ChromaDB Configuration
CHROMA_PERSIST_DIR = os.path.join(DATA_DIR, "chroma_db")
os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)

# Initialize ChromaDB client with telemetry disabled
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY_ENABLED"] = "False"

chroma_client = chromadb.PersistentClient(
    path=CHROMA_PERSIST_DIR,
    settings=Settings(
        anonymized_telemetry=False,
        allow_reset=True,
        is_persistent=True
    )
)

# Create collections for each modality
collections = {}
for modality in MODALITIES:
    try:
        collections[modality] = chroma_client.get_or_create_collection(
            name=f"arweave_{modality}",
            metadata={"description": f"Arweave {modality} content embeddings"}
        )
        logger.info(f"✅ ChromaDB collection 'arweave_{modality}' initialized")
    except Exception as e:
        logger.error(f"Failed to initialize ChromaDB collection for {modality}: {e}")

# ARNS-specific collection
try:
    arns_collection = chroma_client.get_or_create_collection(
        name="arweave_arns",
        metadata={"description": "Arweave ARNS content embeddings"}
    )
    logger.info("✅ ChromaDB ARNS collection initialized")
except Exception as e:
    logger.error(f"Failed to initialize ChromaDB ARNS collection: {e}")

BATCH_SIZE = 100
TOP_K = 10
POLL_INTERVAL = 60

# ==== Load ImageBind with Enhanced CUDA Support ====
print("🔄 Loading ImageBind model...")
print(f"🔍 PyTorch version: {torch.__version__}")
print(f"🔍 CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"🔍 CUDA version: {torch.version.cuda}")
    print(f"🔍 Device count: {torch.cuda.device_count()}")
    print(f"🔍 Current device: {torch.cuda.current_device()}")
    print(f"🔍 Device name: {torch.cuda.get_device_name(0)}")
    print(f"🔍 Memory allocated: {torch.cuda.memory_allocated(0) / 1024**3:.2f} GB")
    print(f"🔍 Memory cached: {torch.cuda.memory_reserved(0) / 1024**3:.2f} GB")

try:
    print(f"🚀 Attempting to load ImageBind on {DEVICE}...")
    model = imagebind_model.imagebind_huge(pretrained=True)
    print("✅ Model loaded from pretrained weights")
    
    model.eval()
    print("✅ Model set to evaluation mode")
    
    model = model.to(DEVICE)
    print(f"✅ Model moved to {DEVICE}")
    
    # Test CUDA memory allocation
    if DEVICE == "cuda":
        test_input = torch.randn(1, 3, 224, 224).to(DEVICE)
        with torch.no_grad():
            _ = model.modality_preprocessors[ModalityType.VISION](test_input)
        print("✅ CUDA forward pass test successful")
        print(f"🔍 Final memory allocated: {torch.cuda.memory_allocated(0) / 1024**3:.2f} GB")
    
    print(f"✅ ImageBind model loaded successfully on {DEVICE}")
    
except Exception as e:
    print(f"❌ Failed to load ImageBind on {DEVICE}")
    print(f"❌ Error details: {str(e)}")
    print(f"❌ Error type: {type(e).__name__}")
    
    if DEVICE == "cuda":
        print("🔄 Attempting CUDA memory cleanup...")
        try:
            torch.cuda.empty_cache()
            print("✅ CUDA cache cleared")
        except Exception as cleanup_error:
            print(f"⚠️ CUDA cleanup failed: {cleanup_error}")
    
    print("🔄 Falling back to CPU...")
    DEVICE = "cpu"
    try:
        model = imagebind_model.imagebind_huge(pretrained=True)
        model.eval().to(DEVICE)
        print("✅ ImageBind model loaded successfully on CPU")
    except Exception as cpu_error:
        print(f"❌ Failed to load on CPU as well: {cpu_error}")
        raise RuntimeError(f"Failed to load ImageBind on both CUDA and CPU: {e} -> {cpu_error}")

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
print("✅ Text splitter initialized")

# ==== NSFW Detection using Zero-Shot Classification ====
NSFW_LABELS = [
    "nude person", "sexual content", "explicit content", "adult content",
    "inappropriate content", "nsfw content", "pornographic content",
    "violence", "graphic content", "disturbing content"
]

SAFE_LABELS = [
    "safe content", "appropriate content", "family friendly content",
    "clean content", "professional content", "educational content",
    "artistic content", "nature content", "technology content"
]

def detect_nsfw_zero_shot(content_embedding, modality="text"):
    """
    Detect NSFW content using zero-shot classification with existing embeddings
    """
    try:
        # Get text embeddings for NSFW and safe labels
        nsfw_texts = NSFW_LABELS
        safe_texts = SAFE_LABELS
        
        # Create text embeddings for labels
        nsfw_embeddings = []
        safe_embeddings = []
        
        for text in nsfw_texts:
            text_inputs = data.load_and_transform_text([text], DEVICE)
            with torch.no_grad():
                text_embedding = model.modality_preprocessors[ModalityType.TEXT](text_inputs)
                nsfw_embeddings.append(text_embedding.cpu().numpy())
        
        for text in safe_texts:
            text_inputs = data.load_and_transform_text([text], DEVICE)
            with torch.no_grad():
                text_embedding = model.modality_preprocessors[ModalityType.TEXT](text_inputs)
                safe_embeddings.append(text_embedding.cpu().numpy())
        
        # Calculate similarities
        content_embedding_np = content_embedding.cpu().numpy() if hasattr(content_embedding, 'cpu') else content_embedding
        
        # Calculate cosine similarity with NSFW labels
        nsfw_similarities = []
        for nsfw_emb in nsfw_embeddings:
            similarity = np.dot(content_embedding_np.flatten(), nsfw_emb.flatten()) / (
                np.linalg.norm(content_embedding_np) * np.linalg.norm(nsfw_emb)
            )
            nsfw_similarities.append(similarity)
        
        # Calculate cosine similarity with safe labels
        safe_similarities = []
        for safe_emb in safe_embeddings:
            similarity = np.dot(content_embedding_np.flatten(), safe_emb.flatten()) / (
                np.linalg.norm(content_embedding_np) * np.linalg.norm(safe_emb)
            )
            safe_similarities.append(similarity)
        
        # Calculate NSFW score
        max_nsfw_similarity = max(nsfw_similarities) if nsfw_similarities else 0
        max_safe_similarity = max(safe_similarities) if safe_similarities else 0
        
        # NSFW score is the difference between max NSFW similarity and max safe similarity
        nsfw_score = max_nsfw_similarity - max_safe_similarity
        
        # Normalize to 0-1 range
        nsfw_score = (nsfw_score + 1) / 2  # Convert from [-1,1] to [0,1]
        
        # Determine if content is NSFW (threshold can be adjusted)
        is_nsfw = nsfw_score > 0.6
        
        return {
            "is_nsfw": is_nsfw,
            "nsfw_score": float(nsfw_score),
            "max_nsfw_similarity": float(max_nsfw_similarity),
            "max_safe_similarity": float(max_safe_similarity),
            "confidence": float(abs(max_nsfw_similarity - max_safe_similarity))
        }
        
    except Exception as e:
        logger.error(f"NSFW detection failed: {e}")
        return {
            "is_nsfw": False,
            "nsfw_score": 0.0,
            "max_nsfw_similarity": 0.0,
            "max_safe_similarity": 0.0,
            "confidence": 0.0,
            "error": str(e)
        }

print("✅ NSFW detection using zero-shot classification initialized")

# ==== Index Handling ====
def load_index(path):
    try:
        if os.path.exists(path):
            arr = np.load(path)
            if arr.shape[1] != 1024:
                logger.warning(f"Index file {path} has wrong shape {arr.shape}, recreating.")
                return np.empty((0, 1024), dtype=np.float32)
            return arr
        else:
            return np.empty((0, 1024), dtype=np.float32)
    except Exception as e:
        logger.error(f"Failed to load index file {path}: {e}. Recreating empty index.")
        return np.empty((0, 1024), dtype=np.float32)

def save_index(index, path):
    try:
        np.save(path, index)
        logger.info(f"Index file saved: {path}")
    except Exception as e:
        logger.error(f"Failed to save index file {path}: {e}")

def save_meta(meta, path):
    try:
        with open(path, "w") as f:
            json.dump(meta, f)
        logger.info(f"Meta file saved: {path}")
    except Exception as e:
        logger.error(f"Failed to save meta file {path}: {e}")

def load_meta(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {}

def save_cursor(cursor, modality):
    with open(os.path.join(DATA_DIR, f"{modality}_cursor.txt"), "w") as f:
        f.write(cursor or "")

def load_cursor(modality):
    path = os.path.join(DATA_DIR, f"{modality}_cursor.txt")
    return open(path).read().strip() if os.path.exists(path) else None

# Example: a larger list (expand as needed)
ARWEAVE_DOMAINS = [
    "arweave.net", "arnode.asia", "ar.io", "arweave.dev", "arweave.live", "arweave-search.goldsky.com"
    # ...add more from the community list
]

from urllib.parse import urlparse, urlunparse

# Robots.txt functionality
def get_robots_txt_url(url):
    """
    Get the robots.txt URL for a given URL.
    """
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    return robots_url

def parse_robots_txt(robots_url):
    """
    Parse robots.txt content and return a RobotFileParser object.
    """
    try:
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp
    except Exception as e:
        logger.warning(f"Failed to parse robots.txt from {robots_url}: {e}")
        return None

def can_fetch_url(url, user_agent="ArweaveIndexer/1.0"):
    """
    Check if the URL can be fetched according to robots.txt.
    Returns True if allowed, False if disallowed, None if robots.txt is unavailable.
    """
    try:
        robots_url = get_robots_txt_url(url)
        rp = parse_robots_txt(robots_url)
        
        if rp is None:
            # If robots.txt is unavailable, assume allowed
            logger.info(f"Robots.txt unavailable for {url}, assuming allowed")
            return True
        
        can_fetch = rp.can_fetch(user_agent, url)
        if can_fetch:
            logger.info(f"Robots.txt allows fetching {url}")
        else:
            logger.warning(f"Robots.txt disallows fetching {url}")
        
        return can_fetch
        
    except Exception as e:
        logger.warning(f"Error checking robots.txt for {url}: {e}")
        # On error, assume allowed to avoid blocking legitimate content
        return True

def get_crawl_delay(url, user_agent="ArweaveIndexer/1.0"):
    """
    Get the crawl delay specified in robots.txt for a URL.
    Returns the delay in seconds, or 0 if not specified.
    """
    try:
        robots_url = get_robots_txt_url(url)
        rp = parse_robots_txt(robots_url)
        
        if rp is None:
            return 0
        
        # RobotFileParser doesn't directly expose crawl_delay, so we need to parse it manually
        try:
            response = requests.get(robots_url, timeout=10)
            if response.status_code == 200:
                content = response.text.lower()
                lines = content.split('\n')
                
                for line in lines:
                    if line.startswith('crawl-delay:'):
                        try:
                            delay = float(line.split(':', 1)[1].strip())
                            logger.info(f"Crawl delay for {url}: {delay} seconds")
                            return delay
                        except ValueError:
                            continue
        except Exception as e:
            logger.warning(f"Failed to get crawl delay from {robots_url}: {e}")
        
        return 0
        
    except Exception as e:
        logger.warning(f"Error getting crawl delay for {url}: {e}")
        return 0

def arweave_domain_fallback_urls(url):
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    # If it's a subdomain (e.g., foo.arweave.net)
    for domain in ARWEAVE_DOMAINS:
        if any(hostname.endswith(f'.{d}') for d in ARWEAVE_DOMAINS):
            # Replace the root domain, keep the subdomain prefix
            parts = hostname.split(".")
            if len(parts) > 2:
                sub = ".".join(parts[:-2])
                new_host = f"{sub}.{domain}"
            else:
                new_host = domain
            new_url = urlunparse(parsed._replace(netloc=new_host))
            yield new_url
        else:
            # Root-level, just swap the domain
            new_url = urlunparse(parsed._replace(netloc=domain))
            yield new_url


RETRY_COUNT = 3
RETRY_SLEEP = 2  # seconds

def get_magic_bytes(url, num_bytes=16):
    if "cu.ardrive.io" in url:
        for attempt in range(RETRY_COUNT):
            try:
                resp = requests.get(url, stream=True, timeout=15)
                chunk = resp.raw.read(num_bytes)
                resp.close()
                return chunk
            except Exception as e:
                logger.warning(f"[get_magic_bytes] Attempt {attempt+1} failed for {url}: {e}")
                time.sleep(RETRY_SLEEP)
        return b""
    for test_url in arweave_domain_fallback_urls(url):
        for attempt in range(RETRY_COUNT):
            try:
                resp = requests.get(test_url, stream=True, timeout=15)
                chunk = resp.raw.read(num_bytes)
                resp.close()
                return chunk
            except Exception as e:
                logger.warning(f"[get_magic_bytes] Attempt {attempt+1} failed for {test_url}: {e}")
                time.sleep(RETRY_SLEEP)
    return b""

def detect_file_type(url):
    ext = os.path.splitext(url.split("?")[0])[1].lower()
    if ext == '.pdf':
        return "pdf"
    # Content-Type header check
    for domain in ARWEAVE_DOMAINS:
        try:
            test_url = url
            for d in ARWEAVE_DOMAINS:
                if d in url:
                    test_url = url.replace(d, domain)
                    break
            resp = requests.head(test_url, timeout=10, allow_redirects=True)
            content_type = resp.headers.get('content-type', '').lower()
            if 'application/pdf' in content_type:
                return "pdf"
            if 'text/html' in content_type or 'application/xhtml+xml' in content_type or 'text/plain' in content_type:
                return "web"
            if 'image/' in content_type:
                return "image"
            if 'audio/' in content_type:
                return "audio"
            if 'video/' in content_type:
                return "video"
        except Exception:
            continue
    # Magic bytes check for PDF
    magic = get_magic_bytes(url, 64)
    if magic.startswith(b'%PDF'):
        return "pdf"
    # 1. Check extension first for web types
    if ext in ['.html', '.htm', '.xml', '.json', '.txt']:
        return "web"
    if ext in ['.mp3', '.wav', '.wave', '.flac', '.aac', '.ogg', '.m4a', '.wma', '.webm']:
        return "audio"
    if ext in ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv', '.3gp', '.m4v']:
        return "video"
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg']:
        return "image"
    # 2. Check Content-Type header for HTML (try all fallback domains)
    for domain in ARWEAVE_DOMAINS:
        try:
            test_url = url
            for d in ARWEAVE_DOMAINS:
                if d in url:
                    test_url = url.replace(d, domain)
                    break
            resp = requests.head(test_url, timeout=10, allow_redirects=True)
            content_type = resp.headers.get('content-type', '').lower()
            if 'text/html' in content_type or 'application/xhtml+xml' in content_type or 'text/plain' in content_type:
                return "web"
            if 'image/' in content_type:
                return "image"
            if 'audio/' in content_type:
                return "audio"
            if 'video/' in content_type:
                return "video"
        except Exception:
            continue
    # 3. Fallback to magic bytes if extension and content-type are missing or ambiguous
    magic = get_magic_bytes(url, 64)
    # Images
    if (magic.startswith(b'\x89PNG') or magic.startswith(b'\xff\xd8\xff') or 
        magic.startswith(b'GIF87a') or magic.startswith(b'GIF89a') or
        magic.startswith(b'BM') or magic.startswith(b'II*\x00') or magic.startswith(b'MM\x00*') or
        (magic[:4] == b'RIFF' and magic[8:12] == b'WEBP') or 
        magic.startswith(b'\x00\x00\x01\x00') or magic.startswith(b'\x00\x00\x02\x00')):
        return "image"
    # Audio
    if (magic[:3] == b'ID3' or magic[:2] == b'\xff\xfb' or magic[:2] == b'\xff\xf3' or
        magic[:2] == b'\xff\xf1' or magic[:2] == b'\xff\xf9' or
        (magic[:4] == b'RIFF' and magic[8:12] == b'WAVE') or
        magic.startswith(b'OggS') or magic.startswith(b'fLaC') or
        magic.startswith(b'FORM') or magic.startswith(b'FLAC') or
        b'ftypM4A' in magic or b'ftypmp4' in magic or
        magic.startswith(b'\xff\xfe') or magic.startswith(b'\xfe\xff') or
        magic.startswith(b'UklGRg==') or magic.startswith(b'SUQzBAAAAAA')):
        return "audio"
    # Video
    if ((magic[:4] == b'\x00\x00\x00\x18' or magic[:4] == b'\x00\x00\x00\x20') and 
         (magic[4:8] == b'ftyp' or b'ftyp' in magic[:16])) or \
       b'ftypqt' in magic or b'ftypisom' in magic or b'ftypmp4' in magic or \
       (magic[:4] == b'RIFF' and magic[8:12] == b'AVI ') or \
       magic.startswith(b'\x1A\x45\xDF\xA3') or magic.startswith(b'FLV') or \
       magic.startswith(b'0&\xB2u\x8Ef\xCF\x11') or \
       magic.startswith(b'\x00\x00\x00\x14') or magic.startswith(b'\x00\x00\x00\x1C'):
        return "video"
    # Web/HTML content (robust check: anywhere in first 64 bytes)
    if (b'<html' in magic.lower() or b'<!doctype' in magic.lower() or b'<HTML' in magic or b'<?xml' in magic or
        magic.startswith(b'{') or magic.startswith(b'[') or
        b'found' in magic.lower() or b'redirect' in magic.lower() or b'error' in magic.lower() or
        b'cdn77' in magic.lower() or b'302' in magic or b'404' in magic or b'not found' in magic.lower() or
        b'temporarily moved' in magic.lower() or b'new location' in magic.lower() or b'page not found' in magic.lower()):
        return "web"
    return "binary"


# ==== Embedding Functions ====
def embed_text(text):
    inputs = {ModalityType.TEXT: data.load_and_transform_text([text], device=DEVICE)}
    with torch.no_grad():
        emb = model(inputs)[ModalityType.TEXT]
        emb /= emb.norm(dim=-1, keepdim=True)
    return emb[0].cpu().numpy()

def embed_image(url):
    try:
        # First, try to get headers to validate content type
        try:
            headers = requests.head(url, timeout=10).headers
            content_type = headers.get('content-type', '').lower()
            if not content_type.startswith('image/'):
                logger.warning(f"URL {url} has non-image content-type: {content_type}")
                # Check if it's actually HTML/redirect content
                if 'text/html' in content_type or 'text/plain' in content_type:
                    logger.warning(f"URL {url} is HTML/text content, not image - skipping")
                    return None
        except Exception as e:
            logger.warning(f"Could not check headers for {url}: {e}")
        
        img_bytes = requests.get(url, timeout=30).content
        
        # Validate that we actually got image data
        if len(img_bytes) < 100:  # Too small to be a valid image
            logger.warning(f"Image file too small for {url}: {len(img_bytes)} bytes")
            return None
        
        # Additional validation: check if content is actually HTML/redirect
        if len(img_bytes) > 64:
            magic = img_bytes[:64].lower()
            if (b'<html' in magic or b'<!doctype' in magic or b'found' in magic or 
                b'redirect' in magic or b'error' in magic or b'cdn77' in magic or
                b'302' in magic or b'404' in magic or b'not found' in magic or
                b'temporarily moved' in magic or b'new location' in magic):
                logger.warning(f"URL {url} contains HTML/redirect content, not image - skipping")
                return None
            
        temp_dir = os.path.join(DATA_DIR, "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Use a more descriptive filename with extension detection
        filename = url.split("/")[-1]
        if not filename or "." not in filename:
            # Try to detect format from magic bytes
            if img_bytes.startswith(b'\xff\xd8\xff'):
                filename = f"image_{uuid.uuid4().hex[:8]}.jpg"
            elif img_bytes.startswith(b'\x89PNG'):
                filename = f"image_{uuid.uuid4().hex[:8]}.png"
            elif img_bytes.startswith(b'GIF87a') or img_bytes.startswith(b'GIF89a'):
                filename = f"image_{uuid.uuid4().hex[:8]}.gif"
            else:
                filename = f"image_{uuid.uuid4().hex[:8]}.bin"
        
        temp_path = os.path.join(temp_dir, filename)
        
        with open(temp_path, 'wb') as f:
            f.write(img_bytes)
        
        logger.info(f"load image from {temp_path}")
        
        try:
            # Validate the image file before processing
            try:
                with Image.open(temp_path) as img:
                    # Force load to catch any corruption
                    img.load()
                    # Convert to RGB if necessary
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    # Save as a clean JPEG for processing
                    clean_path = os.path.join(temp_dir, f"clean_{filename}")
                    img.save(clean_path, 'JPEG', quality=95)
                    temp_path = clean_path
            except Exception as img_error:
                logger.error(f"Image validation failed for {url}: {img_error}")
                return None
            
            # Now try to embed the validated image
            inputs = {ModalityType.VISION: data.load_and_transform_vision_data([temp_path], device=DEVICE)}
            with torch.no_grad():
                emb = model(inputs)[ModalityType.VISION]
                emb /= emb.norm(dim=-1, keepdim=True)
            return emb[0].cpu().numpy()
        finally:
            # Clean up all temporary files
            if os.path.exists(temp_path):
                os.remove(temp_path)
            # Also clean up the original temp file if it was different
            original_temp = os.path.join(temp_dir, filename)
            if os.path.exists(original_temp) and original_temp != temp_path:
                os.remove(original_temp)
    except Exception as e:
        logger.error(f"[embed_image] Failed to embed image from {url}: {e}")
        return None

def embed_audio(url):
    try:
        # First, try to get headers to validate content type
        try:
            headers = requests.head(url, timeout=10).headers
            content_type = headers.get('content-type', '').lower()
            if not content_type.startswith('audio/'):
                logger.warning(f"URL {url} has non-audio content-type: {content_type}")
                # Check if it's actually HTML/redirect content
                if 'text/html' in content_type or 'text/plain' in content_type:
                    logger.warning(f"URL {url} is HTML/text content, not audio - skipping")
                    return None
        except Exception as e:
            logger.warning(f"Could not check headers for {url}: {e}")
        
        audio_bytes = requests.get(url, timeout=30).content
        
        # Validate that we actually got audio data
        if len(audio_bytes) < 100:  # Too small to be a valid audio file
            logger.warning(f"Audio file too small for {url}: {len(audio_bytes)} bytes")
            return None
        
        # Additional validation: check if content is actually HTML/redirect
        if len(audio_bytes) > 64:
            magic = audio_bytes[:64].lower()
            if (b'<html' in magic or b'<!doctype' in magic or b'found' in magic or 
                b'redirect' in magic or b'error' in magic or b'cdn77' in magic or
                b'302' in magic or b'404' in magic or b'not found' in magic or
                b'temporarily moved' in magic or b'new location' in magic):
                logger.warning(f"URL {url} contains HTML/redirect content, not audio - skipping")
                return None
            
        temp_dir = os.path.join(DATA_DIR, "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        unique_id = str(uuid.uuid4())
        temp_in_path = os.path.join(temp_dir, f"input_audio_{unique_id}")
        temp_wav_path = os.path.join(temp_dir, f"temp_{unique_id}.wav")
        
        # Save the original audio bytes to a temp file
        with open(temp_in_path, 'wb') as f:
            f.write(audio_bytes)
        
        try:
            # Try multiple audio loading approaches
            y, sr = None, None
            
            # Approach 1: Try librosa first (handles most formats)
            try:
                y, sr = librosa.load(temp_in_path, sr=None, mono=True)
                logger.info(f"Successfully loaded audio with librosa: {url}")
            except Exception as librosa_error:
                logger.warning(f"Librosa failed for {url}: {librosa_error}")
                
                # Approach 2: Try soundfile as fallback
                try:
                    y, sr = sf.read(temp_in_path)
                    if len(y.shape) > 1:  # Convert stereo to mono
                        y = np.mean(y, axis=1)
                    logger.info(f"Successfully loaded audio with soundfile: {url}")
                except Exception as sf_error:
                    logger.warning(f"Soundfile failed for {url}: {sf_error}")
                    
                    # Approach 3: Try ffmpeg as last resort (only if available)
                    if FFMPEG_AVAILABLE:
                        try:
                            ffmpeg_path = os.path.join(temp_dir, f"ffmpeg_{unique_id}.wav")
                            result = subprocess.run([
                                'ffmpeg', '-y', '-i', temp_in_path, 
                                '-ac', '1', '-ar', '16000', '-f', 'wav', ffmpeg_path
                            ], capture_output=True, timeout=30)
                            
                            if result.returncode == 0 and os.path.exists(ffmpeg_path):
                                y, sr = librosa.load(ffmpeg_path, sr=16000, mono=True)
                                logger.info(f"Successfully loaded audio with ffmpeg: {url}")
                                # Clean up ffmpeg temp file
                                os.remove(ffmpeg_path)
                            else:
                                logger.error(f"FFmpeg conversion failed for {url}: {result.stderr.decode()}")
                                return None
                        except Exception as ffmpeg_error:
                            logger.error(f"FFmpeg approach failed for {url}: {ffmpeg_error}")
                            return None
                    else:
                        logger.warning(f"FFmpeg not available, cannot try conversion for {url}")
                        return None
            
            if y is None or sr is None:
                logger.error(f"All audio loading approaches failed for {url}")
                return None
            
            # Validate audio data
            if len(y) < sr * 0.1:  # Less than 0.1 seconds
                logger.warning(f"Audio file too short for {url}: {len(y)/sr:.2f} seconds")
                return None
            
            # Save as wav using soundfile
            sf.write(temp_wav_path, y, sr, format='WAV')
            logger.info(f"Audio converted and saved as WAV: {temp_wav_path}")
            
            # Now use your embedding logic on temp_wav_path
            inputs = {ModalityType.AUDIO: data.load_and_transform_audio_data([temp_wav_path], device=DEVICE)}
            with torch.no_grad():
                emb = model(inputs)[ModalityType.AUDIO]
                emb /= emb.norm(dim=-1, keepdim=True)
            return emb[0].cpu().numpy()
        finally:
            # Clean up all temporary files
            if os.path.exists(temp_in_path):
                os.remove(temp_in_path)
            if os.path.exists(temp_wav_path):
                os.remove(temp_wav_path)
    except Exception as e:
        logger.error(f"[embed_audio] Failed to embed audio from {url}: {e}")
        return None

def ensure_tensor(data):
    # Recursively convert nested lists/arrays to a torch.Tensor
    if isinstance(data, torch.Tensor):
        return data
    if isinstance(data, np.ndarray):
        return torch.from_numpy(data)
    if isinstance(data, (list, tuple)) and len(data) > 0:
        return ensure_tensor(data[0])
    return None

def embed_video(url):
    try:
        # First, try to get headers to validate content type
        try:
            headers = requests.head(url, timeout=10).headers
            content_type = headers.get('content-type', '').lower()
            if not content_type.startswith('video/'):
                logger.warning(f"URL {url} has non-video content-type: {content_type}")
                # Check if it's actually HTML/redirect content
                if 'text/html' in content_type or 'text/plain' in content_type:
                    logger.warning(f"URL {url} is HTML/text content, not video - skipping")
                    return None
        except Exception as e:
            logger.warning(f"Could not check headers for {url}: {e}")
        
        video_bytes = requests.get(url, timeout=30).content
        
        # Validate that we actually got video data
        if len(video_bytes) < 1000:  # Too small to be a valid video file
            logger.warning(f"Video file too small for {url}: {len(video_bytes)} bytes")
            return None
        
        # Additional validation: check if content is actually HTML/redirect
        if len(video_bytes) > 64:
            magic = video_bytes[:64].lower()
            if (b'<html' in magic or b'<!doctype' in magic or b'found' in magic or 
                b'redirect' in magic or b'error' in magic or b'cdn77' in magic or
                b'302' in magic or b'404' in magic or b'not found' in magic or
                b'temporarily moved' in magic or b'new location' in magic):
                logger.warning(f"URL {url} contains HTML/redirect content, not video - skipping")
                return None
            
        temp_dir = os.path.join(DATA_DIR, "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Use a more descriptive filename with extension detection
        filename = url.split("/")[-1]
        if not filename or "." not in filename:
            # Try to detect format from magic bytes
            if video_bytes.startswith(b'\x00\x00\x00\x18') or video_bytes.startswith(b'\x00\x00\x00\x20'):
                filename = f"video_{uuid.uuid4().hex[:8]}.mp4"
            elif video_bytes.startswith(b'RIFF') and b'AVI ' in video_bytes[8:12]:
                filename = f"video_{uuid.uuid4().hex[:8]}.avi"
            elif video_bytes.startswith(b'\x1A\x45\xDF\xA3'):
                filename = f"video_{uuid.uuid4().hex[:8]}.mkv"
            else:
                filename = f"video_{uuid.uuid4().hex[:8]}.mp4"
        
        temp_path = os.path.join(temp_dir, filename)
        
        with open(temp_path, 'wb') as f:
            f.write(video_bytes)
        
        logger.info(f"load video from {temp_path}")
        
        try:
            vision_data = None
            
            # Use PyAV for video processing (more reliable than ImageBind's video loading)
            try:
                import av
                container = av.open(temp_path)
                stream = container.streams.video[0]
                
                # Extract frames for processing - limit to fewer frames to save memory
                frames = []
                frame_count = 0
                for frame in container.decode(video=0):
                    if frame_count < 4:  # Reduced from 8 to 4 frames to save memory
                        # Resize frame to smaller dimensions to save memory
                        frame_array = frame.to_ndarray(format='rgb24')
                        if frame_array.shape[0] > 224 or frame_array.shape[1] > 224:
                            # Resize to 224x224 to match ImageBind's expected input size
                            import cv2
                            frame_array = cv2.resize(frame_array, (224, 224))
                        
                        # Convert frame to tensor
                        frame_tensor = torch.from_numpy(frame_array).float()
                        frame_tensor = frame_tensor.permute(2, 0, 1)  # HWC to CHW
                        frame_tensor = frame_tensor.unsqueeze(0)  # Add batch dimension
                        frames.append(frame_tensor)
                        frame_count += 1
                    else:
                        break
                
                if frames:
                    # Stack frames and normalize
                    vision_data = torch.cat(frames, dim=0)
                    vision_data = vision_data / 255.0  # Normalize to 0-1
                    logger.info(f"Successfully loaded video with PyAV: {url}")
                else:
                    logger.error(f"No frames extracted with PyAV for {url}")
                    return None
                    
            except Exception as av_error:
                logger.error(f"PyAV video processing failed for {url}: {av_error}")
                return None
            
            # Force tensor conversion for all cases
            if not torch.is_tensor(vision_data):
                try:
                    vision_data = torch.from_numpy(np.array(vision_data))
                except Exception as e:
                    logger.error(f"[embed_video] Could not convert vision_data to tensor for {url}: {e}")
                    return None
            
            # Ensure tensor is on correct device
            if hasattr(vision_data, 'device') and vision_data.device != torch.device(DEVICE):
                vision_data = vision_data.to(DEVICE)
            
            # Memory management: Clear cache before processing
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # Create inputs for the model
            inputs = {ModalityType.VISION: vision_data}
            
            with torch.no_grad():
                emb = model(inputs)[ModalityType.VISION]
                
            # Memory management: Clear cache after processing
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                emb /= emb.norm(dim=-1, keepdim=True)
            return emb[0].cpu().numpy()
        finally:
            # Clean up temporary files
            if os.path.exists(temp_path):
                os.remove(temp_path)
    except Exception as e:
        logger.error(f"[embed_video] Failed to embed video from {url}: {e}")
        return None

# ==== Redundant Fetch Helpers ====
def fetch_with_redundancy(path, method="get", is_arns=False, **kwargs):
    errors = []
    for domain in ARWEAVE_DOMAINS:
        try:
            if is_arns:
                url = f"https://arns.{domain}{path}"
            else:
                url = f"https://{domain}{path}"
            if method == "post":
                resp = requests.post(url, timeout=20, **kwargs)
            else:
                resp = requests.get(url, timeout=20, **kwargs)
            resp.raise_for_status()
            return resp
        except Exception as e:
            errors.append(f"{domain}: {e}")
    raise Exception(f"All domains failed: {errors}")

def fetch_graphql(query, variables=None):
    for domain in ARWEAVE_DOMAINS:
        url = f"https://{domain}/graphql"
        for attempt in range(RETRY_COUNT):
            try:
                resp = requests.post(url, json={"query": query, "variables": variables or {}}, timeout=20)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.warning(f"GraphQL fetch attempt {attempt+1} failed on {domain}: {e}")
                time.sleep(RETRY_SLEEP)
    raise Exception("All GraphQL endpoints failed")

def fetch_file(txid):
    for domain in ARWEAVE_DOMAINS:
        url = f"https://{domain}/{txid}"
        for test_url in arweave_domain_fallback_urls(url):
            for attempt in range(RETRY_COUNT):
                try:
                    resp = requests.get(test_url, timeout=30)
                    resp.raise_for_status()
                    return resp.content
                except Exception as e:
                    logger.warning(f"File fetch attempt {attempt+1} failed on {test_url}: {e}")
                    time.sleep(RETRY_SLEEP)
    raise Exception("All file endpoints failed")

def fetch_arns(name):
    for domain in ARWEAVE_DOMAINS:
        url = f"https://arns.{domain}/{name}"
        for test_url in arweave_domain_fallback_urls(url):
            for attempt in range(RETRY_COUNT):
                try:
                    resp = requests.get(test_url, timeout=20)
                    resp.raise_for_status()
                    return resp.content
                except Exception as e:
                    logger.warning(f"ARNS fetch attempt {attempt+1} failed on {test_url}: {e}")
                    time.sleep(RETRY_SLEEP)
    raise Exception("All ARNS endpoints failed")

# ==== Enhanced Content Parsing ====
def fetch_webpage_text(url):
    if "cu.ardrive.io" in url:
        for attempt in range(RETRY_COUNT):
            try:
                loader = WebBaseLoader(url)
                docs = loader.load()
                content = "\n".join([doc.page_content for doc in docs])
                title = docs[0].metadata.get("title", url) if docs and hasattr(docs[0], 'metadata') else url
                description = content[:200] if content else ""
                logger.info(f"Fetched and parsed webpage: {url} (title: {title})")
                return title, content, description
            except Exception as e:
                logger.warning(f"[Fallback] Attempt {attempt+1} failed for cu.ardrive.io: {e}")
                time.sleep(RETRY_SLEEP)
        return "", "", ""
    for test_url in arweave_domain_fallback_urls(url):
        for attempt in range(RETRY_COUNT):
            try:
                loader = WebBaseLoader(test_url)
                docs = loader.load()
                content = "\n".join([doc.page_content for doc in docs])
                title = docs[0].metadata.get("title", test_url) if docs and hasattr(docs[0], 'metadata') else test_url
                description = content[:200] if content else ""
                logger.info(f"Fetched and parsed webpage: {test_url} (title: {title})")
                return title, content, description
            except Exception as e:
                logger.warning(f"[Fallback] Attempt {attempt+1} failed for {test_url}: {e}")
                time.sleep(RETRY_SLEEP)
    return "", "", ""

def is_valid_content(text, min_length=50, max_length=100000):
    """Validate content quality and length."""
    if not text or not isinstance(text, str):
        return False
    
    # Check length
    if len(text.strip()) < min_length:
        return False
    
    if len(text) > max_length:
        return False
    
    # Check for common low-quality indicators
    text_lower = text.lower()
    
    # Skip if too much code/technical content
    code_indicators = ['function(', 'var ', 'const ', 'let ', 'import ', 'export ', 'class ', 'public class']
    code_count = sum(1 for indicator in code_indicators if indicator in text_lower)
    if code_count > 3:
        return False
    
    # Skip if too much HTML/XML markup
    markup_count = text.count('<') + text.count('>')
    if markup_count > len(text) * 0.1:  # More than 10% markup
        return False
    
    # Skip if too much whitespace
    if len(text.strip()) / len(text) < 0.7:
        return False
    
    return True

def extract_rich_metadata(soup, url):
    """Extract comprehensive metadata from webpage."""
    metadata = {}
    
    # Title extraction with fallbacks
    title = ""
    title_selectors = [
        'meta[property="og:title"]',
        'meta[name="twitter:title"]',
        'meta[name="title"]',
        'title'
    ]
    
    for selector in title_selectors:
        tag = soup.select_one(selector)
        if tag:
            if tag.name == 'meta':
                title = tag.get('content', '').strip()
            else:
                title = tag.get_text(strip=True)
            if title:
                break
    
    metadata['title'] = title or url
    
    # Description extraction
    desc_selectors = [
        'meta[name="description"]',
        'meta[property="og:description"]',
        'meta[name="twitter:description"]'
    ]
    
    for selector in desc_selectors:
        tag = soup.select_one(selector)
        if tag and tag.get('content'):
            metadata['description'] = tag['content'].strip()
            break
    
    # Author extraction
    author_selectors = [
        'meta[name="author"]',
        'meta[property="article:author"]',
        'meta[name="twitter:creator"]'
    ]
    
    for selector in author_selectors:
        tag = soup.select_one(selector)
        if tag and tag.get('content'):
            metadata['author'] = tag['content'].strip()
            break
    
    # Keywords/tags
    keywords_tag = soup.select_one('meta[name="keywords"]')
    if keywords_tag and keywords_tag.get('content'):
        metadata['keywords'] = keywords_tag['content'].strip()
    
    # Language detection
    lang_tag = soup.select_one('html[lang]')
    if lang_tag:
        metadata['language'] = lang_tag['lang']
    
    return metadata

def clean_text(text):
    """Clean and normalize text content."""
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = ' '.join(text.split())
    
    # Remove common unwanted patterns
    unwanted_patterns = [
        r'\s+',  # Multiple spaces
        r'\[.*?\]',  # Square brackets content
        r'\(.*?\)',  # Parentheses content (optional)
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',  # URLs
    ]
    
    for pattern in unwanted_patterns:
        text = re.sub(pattern, ' ', text)
    
    # Final cleanup
    text = ' '.join(text.split())
    return text.strip()

def parse_webpage(html):
    """Enhanced webpage parsing with better content extraction and validation."""
    try:
        soup = BeautifulSoup(html, "html.parser")
        
        # Extract rich metadata
        metadata = extract_rich_metadata(soup, "")
        
        # Remove unnecessary tags but keep some structure
        for tag in soup([
            "script", "style", "noscript", "header", "footer", "nav", "aside", 
            "form", "input", "svg", "canvas", "iframe", "button", "figure", 
            "img", "link", "meta", "object", "embed", "applet", "base", 
            "map", "area", "track", "audio", "video", "noscript"
        ]):
            tag.decompose()
        
        # Extract content from various text elements
        text_elements = []
        
        # Get all text-containing elements
        for elem in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "div", "span", "li", "td", "th"]):
            text = elem.get_text(" ", strip=True)
            if text and len(text.strip()) > 10:  # Minimum meaningful length
                text_elements.append({
                    'tag': elem.name,
                    'text': clean_text(text),
                    'level': int(elem.name[1]) if elem.name.startswith('h') else 0
                })
        
        # Create semantic chunks
        chunks = []
        current_section = metadata.get('title', '')
        current_level = 0
        
        for elem in text_elements:
            # Update section based on heading hierarchy
            if elem['tag'].startswith('h'):
                if elem['level'] <= current_level + 1:  # Only go deeper or same level
                    current_section = elem['text']
                    current_level = elem['level']
            elif elem['tag'] == 'p' and elem['text']:
                # Create chunk for paragraph content
                if is_valid_content(elem['text']):
                    chunk = {
                        "title": metadata.get('title', ''),
                        "section": current_section,
                        "text": elem['text'],
                        "meta_desc": metadata.get('description', ''),
                        "author": metadata.get('author', ''),
                        "keywords": metadata.get('keywords', ''),
                        "language": metadata.get('language', ''),
                        "tag": elem['tag']
                    }
                    chunks.append(chunk)
        
        # If no chunks from paragraphs, try to create chunks from other content
        if not chunks:
            all_text = soup.get_text(" ", strip=True)
            all_text = clean_text(all_text)
            
            if is_valid_content(all_text):
                # Split into reasonable chunks
                words = all_text.split()
                chunk_size = 200  # words per chunk
                
                for i in range(0, len(words), chunk_size):
                    chunk_text = " ".join(words[i:i + chunk_size])
                    if is_valid_content(chunk_text):
                        chunk = {
                            "title": metadata.get('title', ''),
                            "section": current_section,
                            "text": chunk_text,
                            "meta_desc": metadata.get('description', ''),
                            "author": metadata.get('author', ''),
                            "keywords": metadata.get('keywords', ''),
                            "language": metadata.get('language', ''),
                            "tag": "div"
                        }
                        chunks.append(chunk)
        
        logger.info(f"Parsed webpage: {len(chunks)} valid chunks, title: {metadata.get('title', '')}")
        return chunks
        
    except Exception as e:
        logger.error(f"Error parsing webpage: {e}")
        return []

def enhanced_index_file(url, is_arns=False, force_web=False):
    """Enhanced file indexing with better web content handling."""
    normalized_url = normalize_url(url)
    
    # Deduplication: skip if normalized_url already indexed
    with indexed_txids_lock:
        if normalized_url in indexed_txids:
            logger.info(f"Skipping already indexed normalized URL: {normalized_url}")
            return
    
    if force_web:
        filetype = "web"
    else:
        filetype = detect_file_type(url)
    
    if filetype == "pdf":
        logger.info(f"Skipping PDF file: {url}")
        return
    
    if filetype == "image":
        emb, modality = embed_image(url), "image"
        if emb is not None:
            meta = {"txid": extract_txid_or_arns_name(url), "url": url, "title": url, "chunk": "", "description": f"{modality} from {url}", "modality": modality}
            store(emb, meta, modality)
            logger.info(f"Indexed {modality} file: {url}")
        else:
            logger.error(f"Embedding failed for {modality} file: {url}")
        return
    elif filetype == "audio":
        emb, modality = embed_audio(url), "audio"
        if emb is not None:
            meta = {"txid": extract_txid_or_arns_name(url), "url": url, "title": url, "chunk": "", "description": f"{modality} from {url}", "modality": modality}
            store(emb, meta, modality)
            logger.info(f"Indexed {modality} file: {url}")
        else:
            logger.error(f"Embedding failed for {modality} file: {url}")
        return
    elif filetype == "video":
        emb, modality = embed_video(url), "video"
        if emb is not None:
            meta = {"txid": extract_txid_or_arns_name(url), "url": url, "title": url, "chunk": "", "description": f"{modality} from {url}", "modality": modality}
            store(emb, meta, modality)
            logger.info(f"Indexed {modality} file: {url}")
        else:
            logger.error(f"Embedding failed for {modality} file: {url}")
        return
    elif filetype == "web":
        try:
            # Use enhanced webpage indexing with comprehensive metadata
            weighted_results = enhanced_webpage_indexing_with_metadata(url, is_arns)
            
            if not weighted_results:
                logger.warning(f"No valid content extracted from {url}")
                return
            
            logger.info(f"Indexing {len(weighted_results)} enhanced web chunks from {url}")
            
            def store_weighted_result(result):
                try:
                    emb, meta = result
                    store(emb, meta, "web")
                except Exception as e:
                    logger.error(f"Error storing enhanced web result: {e}")
            
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(store_weighted_result, result) for result in weighted_results]
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"Error in enhanced web processing: {e}")
            
            logger.info(f"Successfully indexed web file with rich metadata: {url}")
            
        except Exception as e:
            logger.error(f"Web indexing failed for {url}: {e}")
        return
    else:
        logger.info(f"Skipping unsupported or binary file: {url} (detected type: {filetype})")
        return

def extract_txid_or_arns_name(url):
    # Match either a txid (43+ chars) or an ARNS name (subdomain)
    # Example: https://arweave.net/<txid>
    m = re.match(r"https?://(?:[a-zA-Z0-9_-]+\\.)?arweave\\.(?:net|asia|io|dev|live|search\\.goldsky\\.com)/([a-zA-Z0-9_-]{43,})", url)
    if m:
        return m.group(1)
    # Example: https://<name>.arweave.net
    m = re.match(r"https?://([a-zA-Z0-9_-]+)\\.arweave\\.(?:net|asia|io|dev|live|search\\.goldsky\\.com)", url)
    if m:
        return m.group(1)
    return url  # fallback: use the whole url as unique id

def normalize_url(url):
    parsed = urlparse(url)
    # Remove query and fragment, lowercase scheme and netloc, strip trailing slashes
    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        path=parsed.path.rstrip('/'),
        params='',
        query='',
        fragment=''
    )
    return urlunparse(normalized)

# ARNS functionality now handled by ChromaDB collections

def index_file(url, is_arns=False, force_web=False):
    """Enhanced file indexing with better web content handling."""
    return enhanced_index_file(url, is_arns, force_web)

# ==== Additional Web Indexing Improvements ====
def validate_web_content(url, html_content):
    """Validate that the content is actually a webpage and not an error page."""
    if not html_content or len(html_content.strip()) < 100:
        return False, "Content too short"
    
    # Check for common error indicators
    error_indicators = [
        "404", "not found", "error", "page not found", "access denied",
        "forbidden", "unauthorized", "server error", "maintenance"
    ]
    
    content_lower = html_content.lower()
    for indicator in error_indicators:
        if indicator in content_lower:
            return False, f"Error indicator found: {indicator}"
    
    # Check for basic HTML structure
    if not ('<html' in content_lower or '<body' in content_lower):
        return False, "No HTML structure found"
    
    return True, "Valid content"

def extract_main_content(soup):
    """Extract main content using various heuristics."""
    # Remove common non-content elements
    for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'advertisement']):
        tag.decompose()
    
    # Try to find main content area
    main_selectors = [
        'main',
        '[role="main"]',
        '.main-content',
        '.content',
        '#content',
        '#main',
        'article',
        '.post-content',
        '.entry-content'
    ]
    
    for selector in main_selectors:
        main_content = soup.select_one(selector)
        if main_content:
            return main_content
    
    # Fallback to body if no main content found
    return soup.find('body') or soup

def create_semantic_chunks(text_elements, max_chunk_size=1000, min_chunk_size=100):
    """Create semantic chunks from text elements."""
    chunks = []
    current_chunk = []
    current_size = 0
    
    for elem in text_elements:
        text = elem['text']
        text_size = len(text)
        
        # If adding this text would make chunk too large, save current chunk
        if current_size + text_size > max_chunk_size and current_chunk:
            chunk_text = ' '.join([e['text'] for e in current_chunk])
            if len(chunk_text) >= min_chunk_size:
                chunks.append({
                    'text': chunk_text,
                    'elements': current_chunk.copy()
                })
            current_chunk = []
            current_size = 0
        
        current_chunk.append(elem)
        current_size += text_size
    
    # Add final chunk
    if current_chunk:
        chunk_text = ' '.join([e['text'] for e in current_chunk])
        if len(chunk_text) >= min_chunk_size:
            chunks.append({
                'text': chunk_text,
                'elements': current_chunk
            })
    
    return chunks

def enhanced_parse_webpage(html, url):
    """Enhanced webpage parsing with better content extraction."""
    try:
        soup = BeautifulSoup(html, "html.parser")
        
        # Validate content
        is_valid, reason = validate_web_content(url, html)
        if not is_valid:
            logger.warning(f"Invalid web content for {url}: {reason}")
            return []
        
        # Extract rich metadata
        metadata = extract_rich_metadata(soup, url)
        
        # Extract main content
        main_content = extract_main_content(soup)
        
        # Get text elements with hierarchy
        text_elements = []
        
        for elem in main_content.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "div", "span", "li", "td", "th"]):
            text = elem.get_text(" ", strip=True)
            if text and len(text.strip()) > 10:
                # Determine heading level
                level = 0
                if elem.name.startswith('h'):
                    level = int(elem.name[1])
                
                text_elements.append({
                    'tag': elem.name,
                    'text': clean_text(text),
                    'level': level,
                    'element': elem
                })
        
        # Create semantic chunks
        chunks = create_semantic_chunks(text_elements)
        
        # Convert chunks to the expected format
        result_chunks = []
        for i, chunk in enumerate(chunks):
            # Find the most relevant heading for this chunk
            chunk_elements = chunk['elements']
            section = metadata.get('title', '')
            
            # Look for the closest heading
            for elem in chunk_elements:
                if elem['tag'].startswith('h'):
                    section = elem['text']
                    break
            
            result_chunk = {
                "title": metadata.get('title', ''),
                "section": section,
                "text": chunk['text'],
                "meta_desc": metadata.get('description', ''),
                "author": metadata.get('author', ''),
                "keywords": metadata.get('keywords', ''),
                "language": metadata.get('language', ''),
                "tag": "div",
                "chunk_index": i
            }
            result_chunks.append(result_chunk)
        
        logger.info(f"Enhanced parsing: {len(result_chunks)} chunks from {url}")
        return result_chunks
        
    except Exception as e:
        logger.error(f"Error in enhanced webpage parsing for {url}: {e}")
        return []

def robust_web_indexing(url, is_arns=False):
    """Robust web indexing with multiple fallback strategies."""
    try:
        # Strategy 1: Direct HTML fetch with enhanced parsing
        html_content = None
        for test_url in arweave_domain_fallback_urls(url):
            try:
                resp = requests.get(test_url, timeout=30, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                resp.raise_for_status()
                html_content = resp.text
                break
            except Exception as e:
                logger.warning(f"Direct fetch failed for {test_url}: {e}")
                continue
        
        if html_content:
            chunks = enhanced_parse_webpage(html_content, url)
            if chunks:
                return chunks
        
        # Strategy 2: WebBaseLoader fallback
        try:
            title, content, description = fetch_webpage_text(url)
            if content and len(content.strip()) > 100:
                # Create chunks from the content
                words = content.split()
                chunk_size = 200
                chunks = []
                
                for i in range(0, len(words), chunk_size):
                    chunk_text = " ".join(words[i:i + chunk_size])
                    if is_valid_content(chunk_text):
                        chunk = {
                            "title": title or url,
                            "section": "Content",
                            "text": chunk_text,
                            "meta_desc": description,
                            "author": "",
                            "keywords": "",
                            "language": "",
                            "tag": "div",
                            "chunk_index": len(chunks)
                        }
                        chunks.append(chunk)
                
                if chunks:
                    logger.info(f"WebBaseLoader fallback: {len(chunks)} chunks from {url}")
                    return chunks
        except Exception as e:
            logger.warning(f"WebBaseLoader fallback failed for {url}: {e}")
        
        # Strategy 3: Minimal content extraction
        try:
            # Try to extract any meaningful text
            if html_content:
                soup = BeautifulSoup(html_content, "html.parser")
                text = soup.get_text(" ", strip=True)
                text = clean_text(text)
                
                if is_valid_content(text):
                    chunk = {
                        "title": url,
                        "section": "Content",
                        "text": text[:2000],  # Limit length
                        "meta_desc": "",
                        "author": "",
                        "keywords": "",
                        "language": "",
                        "tag": "div",
                        "chunk_index": 0
                    }
                    logger.info(f"Minimal extraction: 1 chunk from {url}")
                    return [chunk]
        except Exception as e:
            logger.warning(f"Minimal extraction failed for {url}: {e}")
        
        logger.warning(f"All web indexing strategies failed for {url}")
        return []
        
    except Exception as e:
        logger.error(f"Robust web indexing failed for {url}: {e}")
        return []

# ==== Strict Webpage Detection and Content Validation ====
def is_valid_content(content):
    """
    Check if content is valid for indexing.
    Returns True if content is meaningful, False otherwise.
    """
    if not content:
        return False
    
    # Remove whitespace and check if empty
    stripped = content.strip()
    if not stripped:
        return False
    
    # Check if content is too short (likely not meaningful)
    if len(stripped) < 50:
        return False
    
    # Check if content is mostly whitespace or special characters
    text_ratio = len(re.findall(r'[a-zA-Z0-9]', stripped)) / len(stripped)
    if text_ratio < 0.3:  # Less than 30% actual text
        return False
    
    # Check for common meaningless patterns
    meaningless_patterns = [
        r'^\s*$',  # Only whitespace
        r'^[^\w]*$',  # Only special characters
        r'^(Loading|Error|404|Not Found|Access Denied)',  # Error pages
        r'^\s*(javascript|css|html|xml)\s*$',  # Just tech terms
    ]
    
    for pattern in meaningless_patterns:
        if re.match(pattern, stripped, re.IGNORECASE):
            return False
    
    return True

def check_webpage(url):
    """
    Checks if the given URL points to a webpage (HTML content).
    Returns True if the content appears to be a webpage, False otherwise.
    """
    try:
        resp = requests.get(url, timeout=5)
        text = resp.text
        if "<!doctype html" in text.lower() or "<html" in text.lower():
            return True
        if any(tag in text.lower() for tag in ["<head", "<body", "<title", "<meta"]):
            return True
        return False
    except Exception:
        return False

def extract_and_weight_content(soup, url):
    """
    Extract content with title weighting and optimal meta tag cleaning.
    Returns weighted content chunks optimized for embedding.
    """
    # Extract title with high priority
    title = ""
    title_selectors = [
        'meta[property="og:title"]',
        'meta[name="twitter:title"]', 
        'meta[name="title"]',
        'title'
    ]
    
    for selector in title_selectors:
        tag = soup.select_one(selector)
        if tag:
            if tag.name == 'meta':
                title = tag.get('content', '').strip()
            else:
                title = tag.get_text(strip=True)
            if title and is_valid_content(title):
                break
    
    # Clean and validate title
    if title:
        title = clean_text(title)
        if not is_valid_content(title):
            title = ""
    
    # Extract meta description
    meta_desc = ""
    desc_selectors = [
        'meta[name="description"]',
        'meta[property="og:description"]',
        'meta[name="twitter:description"]'
    ]
    
    for selector in desc_selectors:
        tag = soup.select_one(selector)
        if tag and tag.get('content'):
            meta_desc = clean_text(tag['content'].strip())
            if is_valid_content(meta_desc):
                break
    
    # Extract main content
    main_content = extract_main_content(soup)
    
    # Create weighted content chunks
    chunks = []
    
    # 1. Title chunk (highest weight)
    if title:
        chunks.append({
            'text': title,
            'weight': 3.0,  # High weight for title
            'type': 'title',
            'section': 'Title'
        })
    
    # 2. Meta description chunk (medium weight)
    if meta_desc:
        chunks.append({
            'text': meta_desc,
            'weight': 2.0,  # Medium weight for description
            'type': 'description',
            'section': 'Description'
        })
    
    # 3. Main content chunks (normal weight)
    text_elements = []
    for elem in main_content.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "div", "span", "li", "td", "th"]):
        text = elem.get_text(" ", strip=True)
        if text and len(text.strip()) > 10:
            level = 0
            if elem.name.startswith('h'):
                level = int(elem.name[1])
            
            text_elements.append({
                'tag': elem.name,
                'text': clean_text(text),
                'level': level,
                'element': elem
            })
    
    # Create semantic chunks from main content
    content_chunks = create_semantic_chunks(text_elements)
    
    for i, chunk in enumerate(content_chunks):
        if is_valid_content(chunk['text']):
            # Find relevant heading for this chunk
            section = title or "Content"
            for elem in chunk['elements']:
                if elem['tag'].startswith('h'):
                    section = elem['text']
                    break
            
            chunks.append({
                'text': chunk['text'],
                'weight': 1.0,  # Normal weight for content
                'type': 'content',
                'section': section,
                'chunk_index': i
            })
    
    return chunks, title, meta_desc

def create_weighted_embeddings(chunks, url, is_arns=False):
    """
    Optimized embedding creation with intelligent text processing and minimal redundancy.
    """
    results = []
    
    for chunk in chunks:
        try:
            original_text = chunk['text']
            
            # Optimized embedding text creation based on chunk type
            if chunk['type'] == 'title':
                # For titles, emphasize key terms without redundancy
                embedding_text = original_text
                # Add domain context if available
                if 'arlink' in url.lower() or 'arweave' in url.lower():
                    embedding_text = f"Arweave content: {embedding_text}"
            elif chunk['type'] == 'content':
                # For content, use as-is (already optimized by extract_key_content)
                embedding_text = original_text
            else:
                # For other types, use as-is
                embedding_text = original_text
            
            # Create embedding
            emb = embed_text(embedding_text)
            
            # Streamlined metadata creation
            meta = {
                "txid": extract_txid_or_arns_name(url),
                "url": url,
                "normalized_url": normalize_url(url),
                "title": chunk.get('section', ''),
                "section": chunk['section'],
                "chunk": chunk['text'],
                "description": chunk.get('text', ''),
                "content_type": chunk['type'],
                "weight": chunk['weight'],
                "chunk_index": chunk.get('chunk_index', 0),
                "content_quality": chunk.get('content_quality', 'normal'),
                "chunk_length": chunk.get('chunk_length', len(chunk['text'])),
                "modality": "web",
                "embedding_enhanced": True,
                "efficient_indexing": True,
                "processing_version": "2.0"  # Track optimization version
            }
            
            # Add essential WebBaseLoader metadata
            if 'web_loader_title' in chunk:
                meta.update({
                    "web_loader_title": chunk['web_loader_title'],
                    "web_loader_description": chunk['web_loader_description'],
                    "web_loader_content": chunk['web_loader_content']
                })
            
            results.append((emb, meta))
            
        except Exception as e:
            logger.error(f"Error creating optimized embedding for chunk: {e}")
    
    return results

def strict_webpage_indexing(url, is_arns=False):
    """
    Strict webpage indexing with title weighting and optimal content cleaning.
    """
    try:
        # First, check if it's actually a webpage
        if not check_webpage(url):
            logger.info(f"Skipping {url} - not a valid webpage")
            return []
        
        # Fetch content with multiple fallback strategies
        html_content = None
        
        # Strategy 1: Direct fetch
        for test_url in arweave_domain_fallback_urls(url):
            try:
                resp = requests.get(test_url, timeout=30, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                resp.raise_for_status()
                html_content = resp.text
                break
            except Exception as e:
                logger.warning(f"Direct fetch failed for {test_url}: {e}")
                continue
        
        if not html_content:
            # Strategy 2: WebBaseLoader fallback
            try:
                title, content, description = fetch_webpage_text(url)
                if content and is_valid_content(content):
                    # Create simple weighted chunks
                    chunks = []
                    if title and is_valid_content(title):
                        chunks.append({
                            'text': title,
                            'weight': 3.0,
                            'type': 'title',
                            'section': 'Title'
                        })
                    if description and is_valid_content(description):
                        chunks.append({
                            'text': description,
                            'weight': 2.0,
                            'type': 'description',
                            'section': 'Description'
                        })
                    if content and is_valid_content(content):
                        # Split content into chunks
                        words = content.split()
                        chunk_size = 200
                        for i in range(0, len(words), chunk_size):
                            chunk_text = " ".join(words[i:i + chunk_size])
                            if is_valid_content(chunk_text):
                                chunks.append({
                                    'text': chunk_text,
                                    'weight': 1.0,
                                    'type': 'content',
                                    'section': 'Content',
                                    'chunk_index': len(chunks)
                                })
                    
                    if chunks:
                        return create_weighted_embeddings(chunks, url, is_arns)
            except Exception as e:
                logger.warning(f"WebBaseLoader fallback failed for {url}: {e}")
        
        # Strategy 3: Enhanced parsing with weighting
        if html_content:
            soup = BeautifulSoup(html_content, "html.parser")
            chunks, title, meta_desc = extract_and_weight_content(soup, url)
            
            if chunks:
                return create_weighted_embeddings(chunks, url, is_arns)
        
        logger.warning(f"No valid content extracted from {url}")
        return []
        
    except Exception as e:
        logger.error(f"Strict webpage indexing failed for {url}: {e}")
        return []

# ==== Initialize ====
print("🔄 Initializing ChromaDB-based indexer...")

# Initialize indexed_txids for deduplication
indexed_txids = set()
indexed_txids_lock = threading.Lock()

# Load cursors for indexing loops
cursor_web = load_cursor("web")
cursor_image = load_cursor("image")
cursor_audio = load_cursor("audio")
cursor_video = load_cursor("video")

print(f"✅ ChromaDB collections initialized")
print(f"✅ Current cursors: web={cursor_web if cursor_web else 'None'}, image={cursor_image if cursor_image else 'None'}, audio={cursor_audio if cursor_audio else 'None'}, video={cursor_video if cursor_video else 'None'}")

# Initialize locks for thread safety
metas_locks = {m: threading.Lock() for m in MODALITIES}
metas_locks['all'] = threading.Lock()

def store(emb, meta, modality):
    """
    Store embedding and metadata in ChromaDB.
    """
    try:
        # Store in the appropriate collection
        success = store_in_chromadb(emb, meta, modality)
        
        if success:
            # Also store in 'all' collection if not already there
            if modality != "all":
                all_meta = meta.copy()
                all_meta["original_modality"] = modality
                store_in_chromadb(emb, all_meta, "all")
            
            # Add normalized_url to indexed_txids for deduplication
            normalized_url = meta.get("normalized_url", "")
            if normalized_url:
                with indexed_txids_lock:
                    indexed_txids.add(normalized_url)
            
            if modality not in ["image", "web"]:
                logger.info(f"Stored embedding for modality '{modality}' and url '{meta.get('url', '')}'")
        
        return success
        
    except Exception as e:
        logger.error(f"Error storing embedding for {modality}: {e}")
        return False

# ==== Lifespan Events (Modern FastAPI approach) ====
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting Multimodal Arweave Indexer...")
    logger.info("App startup: launching background indexers.")
    # arns_index_once()  # Run ARNS indexing once at startup
    threading.Thread(target=lambda: index_modality_loop("image", ["image/png", "image/jpeg", "image/webp"]), daemon=True).start()
    threading.Thread(target=lambda: index_modality_loop("audio", ["audio/mpeg", "audio/wav", "audio/mp3"]), daemon=True).start()
    threading.Thread(target=lambda: index_modality_loop("video", ["video/mp4", "video/webm"]), daemon=True).start()
    threading.Thread(target=lambda: index_modality_loop("web", ["application/x.arweave-manifest+json", "text/html"]), daemon=True).start()
    threading.Thread(target=arns_index_loop, daemon=True).start()
    
    yield
    
    # Shutdown
    logger.info("App shutdown: cleaning up resources.")
    print("🛑 Shutting down Multimodal Arweave Indexer...")

# ==== FastAPI ARNS flag endpoint ====
ENABLE_ARNS = os.getenv("ENABLE_ARNS", "true").lower() == "true"

app = FastAPI(
    title="Multimodal Arweave Indexer",
    description="A comprehensive multimodal content indexer for Arweave using ImageBind and ChromaDB",
    version="2.0.0",
    lifespan=lifespan
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class SearchRequest(BaseModel):
    query: str
    top_k: int = TOP_K

@app.get("/")
def root():
    logger.info("Root endpoint called.")
    return {"message": "Multimodal Arweave Search (CUVS + ImageBind)"}

@app.get("/status")
def status():
    logger.info("Status endpoint called.")
    status_data = {}
    
    try:
        for modality in MODALITIES:
            collection = collections.get(modality)
            if collection:
                count = collection.count()
                status_data[modality] = count
            else:
                status_data[modality] = 0
        
        # Add ARNS collection count
        if arns_collection:
            status_data["arns"] = arns_collection.count()
        else:
            status_data["arns"] = 0
            
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        status_data = {m: 0 for m in MODALITIES}
        status_data["arns"] = 0
    
    return status_data

# Old search_modality function removed - using enhanced_search_modality instead

def enhanced_search_modality(query: str, top_k: int, modality: str, filter_nsfw: bool = False):
    """
    Enhanced search with ChromaDB and improved weighting for better search results.
    """
    logger.info(f"Enhanced search called for modality '{modality}' with query '{query}' and top_k={top_k}")
    
    try:
        # Get the appropriate collection
        collection = collections.get(modality)
        if not collection:
            logger.warning(f"No ChromaDB collection for modality '{modality}'")
            return {"results": []}
        
        # Create query embedding with enhanced processing
        enhanced_query = query.strip()
        if modality == "web":
            # Add context to web queries for better matching
            enhanced_query = f"Search query: {enhanced_query}"
        
        query_embedding = embed_text(enhanced_query)
        
        # Search in ChromaDB with more results for better selection
        results = collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k * 5,  # Get more results for better filtering
            include=["metadatas", "documents", "distances"]
        )
        
        if not results['ids'] or not results['ids'][0]:
            logger.warning(f"No results found for modality '{modality}'")
            return {"results": []}
        
        # Process results with enhanced scoring
        raw_results = []
        for i, (id_val, metadata, document, distance) in enumerate(zip(
            results['ids'][0], 
            results['metadatas'][0], 
            results['documents'][0], 
            results['distances'][0]
        )):
            if metadata:  # Changed to handle images without text content
                # Convert distance to similarity score
                score = 1.0 - (distance / 2.0)  # Normalize distance to 0-1 score
                
                # Enhanced content type weighting for web results
                adjusted_score = score
                if modality == "web":
                    content_type = metadata.get("content_type", "")
                    content_quality = metadata.get("content_quality", "normal")
                    url = metadata.get("url", "")
                    
                    # Apply quality-based boosting
                    if content_quality == "high":
                        adjusted_score *= 1.3
                    elif content_quality == "medium":
                        adjusted_score *= 1.1
                    
                    # Apply content type boosting
                    if content_type == "title":
                        adjusted_score *= 1.8  # Highest boost for titles
                    elif content_type == "description":
                        adjusted_score *= 1.4  # High boost for descriptions
                    elif content_type == "summary":
                        adjusted_score *= 1.6  # High boost for summaries
                    
                    # Boost results with enhanced embeddings
                    if metadata.get("embedding_enhanced"):
                        adjusted_score *= 1.2
                    
                    # Special handling for ARNS domain searches with enhanced boosting
                    query_lower = query.lower()
                    url_lower = url.lower()
                    title_lower = metadata.get("web_loader_title", "").lower()
                    desc_lower = metadata.get("web_loader_description", "").lower()
                    chunk_lower = metadata.get("chunk", "").lower()
                    
                    # Check for exact domain match (highest priority)
                    if query_lower in url_lower:
                        # Exact domain match gets maximum priority
                        adjusted_score *= 5.0  # Increased from 3.0 to 5.0
                        logger.info(f"Exact domain mtch found: {query} in {url}")
                    # Check for domain boost metadata
                    elif metadata.get("domain_boost"):
                        adjusted_score *= metadata.get("domain_boost", 1.0)
                        logger.info(f"Domain boost applied: {metadata.get('domain_boost')}")
                    # Check for title match
                    elif query_lower in title_lower:
                        adjusted_score *= 2.5  # Increased from 2.0 to 2.5
                        logger.info(f"Title match found: {query} in title")
                    # Check for description match
                    elif query_lower in desc_lower:
                        adjusted_score *= 2.0  # Increased from 1.5 to 2.0
                        logger.info(f"Description match found: {query} in description")
                    # Check for content match
                    elif query_lower in chunk_lower:
                        adjusted_score *= 1.5  # Increased from 1.2 to 1.5
                        logger.info(f"Content match found: {query} in chunk")
                
                # Handle different content types for different modalities
                if modality == "image":
                    # For images, use description or title as content
                    content = metadata.get("description", "") or metadata.get("title", "") or "Image content"
                elif modality == "audio":
                    # For audio, use description or title as content
                    content = metadata.get("description", "") or metadata.get("title", "") or "Audio content"
                elif modality == "video":
                    # For video, use description or title as content
                    content = metadata.get("description", "") or metadata.get("title", "") or "Video content"
                else:
                    # For web content, use the document
                    content = document or metadata.get("chunk", "")
                
                raw_results.append({
                    "score": adjusted_score,
                    "original_score": score,
                    "content_quality": metadata.get("content_quality", "normal"),
                    "content_type": metadata.get("content_type", ""),
                    "is_nsfw": metadata.get("is_nsfw", False),
                    "nsfw_score": metadata.get("nsfw_score", 0.0),
                    "nsfw_confidence": metadata.get("nsfw_confidence", 0.0),
                    **metadata,
                    "chunk": content
                })
        
        # Apply NSFW filtering if requested
        if filter_nsfw:
            filtered_results = []
            for result in raw_results:
                is_nsfw = result.get('is_nsfw', False)
                if not is_nsfw:
                    filtered_results.append(result)
                else:
                    logger.info(f"Filtered NSFW content: {result.get('url', 'unknown')} (NSFW flag: {is_nsfw})")
            raw_results = filtered_results
            logger.info(f"NSFW filtering applied: {len(filtered_results)} results remaining out of {len(raw_results)}")
        
        # Sort by adjusted score for better grouping
        raw_results.sort(key=lambda x: -x['score'])
        
        # Group results by score (within threshold) with enhanced logic
        SCORE_GROUP_THRESHOLD = 0.02  # Slightly higher threshold for better grouping
        grouped = []
        used = [False] * len(raw_results)
        
        for i, res in enumerate(raw_results):
            if used[i]:
                continue
            group = [res]
            used[i] = True
            
            for j in range(i + 1, len(raw_results)):
                if used[j]:
                    continue
                # Group by similar scores and same URL for better organization
                if (abs(res['original_score'] - raw_results[j]['original_score']) < SCORE_GROUP_THRESHOLD and
                    res.get('url') == raw_results[j].get('url')):
                    group.append(raw_results[j])
                    used[j] = True
            
            # Sort group by adjusted score descending
            group.sort(key=lambda x: -x['score'])
            main = group[0]
            duplicates = group[1:]
            main['duplicates'] = duplicates
            main['has_duplicates'] = len(duplicates) > 0
            grouped.append(main)
        
        # Sort groups by main adjusted score descending and take top_k groups only
        grouped.sort(key=lambda x: -x['score'])
        grouped = grouped[:top_k]
        
        logger.info(f"Enhanced search for modality '{modality}' returned {len(grouped)} grouped results (top_k={top_k}).")
        return {"results": grouped}
        
    except Exception as e:
        logger.error(f"Error in enhanced search for modality '{modality}': {e}")
        return {"results": []}

def store_in_chromadb(emb, meta, modality, collection_name=None):
    """
    Store embedding and metadata in ChromaDB with simplified rich metadata.
    """
    try:
        # Validate embedding before proceeding
        if emb is None:
            logger.error(f"Cannot store None embedding for {modality} - {meta.get('url', '')}")
            return False
        
        # Ensure embedding is a numpy array or tensor
        if hasattr(emb, 'tolist'):
            embedding_list = emb.tolist()
        elif hasattr(emb, 'numpy'):
            embedding_list = emb.numpy().tolist()
        elif hasattr(emb, 'cpu'):
            embedding_list = emb.cpu().numpy().tolist()
        else:
            logger.error(f"Invalid embedding type for {modality}: {type(emb)}")
            return False
        
        # Determine which collection to use
        if collection_name == "arns":
            collection = arns_collection
        else:
            collection = collections.get(modality)
        
        if not collection:
            logger.error(f"No ChromaDB collection available for {modality}")
            return False
        
        # Prepare simplified but comprehensive metadata for ChromaDB
        chroma_metadata = {
            # Core identification
            "txid": meta.get("txid", ""),
            "url": meta.get("url", ""),
            "normalized_url": meta.get("normalized_url", ""),
            
            # Content information
            "title": meta.get("title", ""),
            "section": meta.get("section", ""),
            "description": meta.get("description", ""),
            "chunk": meta.get("chunk", ""),
            
            # Content classification
            "modality": modality,
            "content_type": meta.get("content_type", "content"),
            "weight": meta.get("weight", 1.0),
            "chunk_index": meta.get("chunk_index", 0),
            
            # Web-specific metadata
            "author": meta.get("author", ""),
            "keywords": meta.get("keywords", ""),
            "language": meta.get("language", ""),
            "tag": meta.get("tag", "div"),
            
            # WebBaseLoader metadata
            "web_loader_title": meta.get("web_loader_title", ""),
            "web_loader_description": meta.get("web_loader_description", ""),
            "web_loader_content": meta.get("web_loader_content", ""),
            
            # ARNS status
            "is_non_assigned_arns": meta.get("is_non_assigned_arns", False),
            "arns_status": meta.get("arns_status", "assigned"),
            
            # Processing information
            "processing_timestamp": str(int(time.time())),
            "is_arns": meta.get("is_arns", False),
            "original_modality": meta.get("original_modality", modality),
            
            # Content quality metrics
            "text_length": len(meta.get("chunk", "")),
            "word_count": len(meta.get("chunk", "").split()),
            "has_title": bool(meta.get("title")),
            "has_description": bool(meta.get("description")),
        }
        
        # Add optional fields if they exist
        optional_fields = [
            "canonical_url", "robots", "viewport", "charset",
            "domain", "path", "og_title", "og_description",
            "twitter_title", "twitter_description"
        ]
        
        for field in optional_fields:
            if field in meta:
                chroma_metadata[field] = meta[field]
        
        # Generate unique ID
        unique_id = f"{modality}_{meta.get('txid', '')}_{meta.get('chunk_index', 0)}_{int(time.time())}"
        
        # Store in ChromaDB
        collection.add(
            embeddings=[embedding_list],
            metadatas=[chroma_metadata],
            documents=[meta.get("chunk", "")],
            ids=[unique_id]
        )
        
        logger.info(f"✅ Stored embedding and metadata in ChromaDB: {modality} - {meta.get('url', '')} (dimensions: {len(embedding_list)})")
        return True
        
    except Exception as e:
        logger.error(f"Failed to store in ChromaDB: {e}")
        return False

def extract_enhanced_metadata(soup, url, web_loader_metadata=None):
    """
    Extract comprehensive metadata from both BeautifulSoup and WebBaseLoader.
    This function is now primarily used for BeautifulSoup fallback scenarios.
    """
    metadata = {}
    
    # Extract basic metadata from BeautifulSoup
    metadata.update(extract_rich_metadata(soup, url))
    
    # Add WebBaseLoader metadata if available
    if web_loader_metadata:
        metadata.update({
            "web_loader_title": web_loader_metadata.get("title", ""),
            "web_loader_description": web_loader_metadata.get("description", ""),
            "web_loader_content": web_loader_metadata.get("content", ""),
            "web_loader_language": web_loader_metadata.get("language", ""),
            "web_loader_source": web_loader_metadata.get("source", "")
        })
    
    # Detect non-assigned ARNS
    section_text = metadata.get("section", "")
    if "Future home of something rather bullish" in section_text:
        metadata["is_non_assigned_arns"] = True
        metadata["arns_status"] = "non_assigned"
        metadata["content_type"] = "non_assigned_arns"
    else:
        metadata["is_non_assigned_arns"] = False
        metadata["arns_status"] = "assigned"
    
    return metadata

def enhanced_webpage_indexing_with_metadata(url, is_arns=False):
    """
    Enhanced webpage indexing using Langchain WebBaseLoader as primary method.
    Falls back to BeautifulSoup only if WebBaseLoader fails.
    Respects robots.txt for web crawling etiquette.
    """
    try:
        # First, check if it's actually a webpage
        if not check_webpage(url):
            logger.info(f"Skipping {url} - not a valid webpage")
            return []
        
        # Check robots.txt before proceeding
        can_fetch = can_fetch_url(url)
        if can_fetch is False:
            logger.warning(f"Skipping {url} - robots.txt disallows crawling")
            return []
        elif can_fetch is True:
            # Apply crawl delay if specified
            crawl_delay = get_crawl_delay(url)
            if crawl_delay > 0:
                logger.info(f"Applying crawl delay of {crawl_delay} seconds for {url}")
                time.sleep(crawl_delay)
        
        # Try WebBaseLoader as primary method
        web_loader_metadata = None
        web_loader_content = None
        
        for test_url in arweave_domain_fallback_urls(url):
            try:
                logger.info(f"Attempting WebBaseLoader for {test_url}")
                loader = WebBaseLoader(test_url)
                docs = loader.load()
                
                if docs:
                    # Extract content from WebBaseLoader
                    content = "\n".join([doc.page_content for doc in docs])
                    
                    # Extract metadata from first document
                    first_doc = docs[0]
                    title = first_doc.metadata.get("title", "") if hasattr(first_doc, 'metadata') else ""
                    description = first_doc.metadata.get("description", "") if hasattr(first_doc, 'metadata') else ""
                    
                    # Create web loader metadata
                    web_loader_metadata = {
                        "title": title,
                        "description": description,
                        "content": content,
                        "source": test_url,
                        "language": first_doc.metadata.get("language", ""),
                        "url": test_url
                    }
                    
                    web_loader_content = content
                    
                    # Check if this is a standard unassigned ARNS page
                    if title.strip() == "ArNS - Arweave Name System":
                        logger.info(f"Skipping {test_url} - standard unassigned ARNS page")
                        return []
                    
                    logger.info(f"✅ WebBaseLoader successful for {test_url}")
                    break
                    
            except Exception as e:
                logger.warning(f"WebBaseLoader failed for {test_url}: {e}")
                continue
        
        # If WebBaseLoader failed, try BeautifulSoup as fallback
        if not web_loader_metadata:
            logger.info(f"WebBaseLoader failed, trying BeautifulSoup fallback for {url}")
            
            # Check robots.txt again for BeautifulSoup fallback (in case it changed)
            can_fetch_fallback = can_fetch_url(url)
            if can_fetch_fallback is False:
                logger.warning(f"Skipping {url} - robots.txt disallows crawling (fallback)")
                return []
            elif can_fetch_fallback is True:
                # Apply crawl delay if specified
                crawl_delay = get_crawl_delay(url)
                if crawl_delay > 0:
                    logger.info(f"Applying crawl delay of {crawl_delay} seconds for {url} (fallback)")
                    time.sleep(crawl_delay)
            
            # Fetch HTML content for BeautifulSoup
            html_content = None
            for test_url in arweave_domain_fallback_urls(url):
                try:
                    resp = requests.get(test_url, timeout=30, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    })
                    resp.raise_for_status()
                    html_content = resp.text
                    break
                except Exception as e:
                    logger.warning(f"Direct fetch failed for {test_url}: {e}")
                    continue
            
            if html_content:
                soup = BeautifulSoup(html_content, "html.parser")
                
                # Extract content using BeautifulSoup
                main_content = extract_main_content(soup)
                content = main_content.get_text(" ", strip=True) if main_content else ""
                
                # Extract metadata using BeautifulSoup
                title = ""
                title_selectors = [
                    'meta[property="og:title"]',
                    'meta[name="twitter:title"]', 
                    'meta[name="title"]',
                    'title'
                ]
                
                for selector in title_selectors:
                    tag = soup.select_one(selector)
                    if tag:
                        if tag.name == 'meta':
                            title = tag.get('content', '').strip()
                        else:
                            title = tag.get_text(strip=True)
                        if title and is_valid_content(title):
                            break
                
                # Extract description
                description = ""
                desc_selectors = [
                    'meta[name="description"]',
                    'meta[property="og:description"]',
                    'meta[name="twitter:description"]'
                ]
                
                for selector in desc_selectors:
                    tag = soup.select_one(selector)
                    if tag and tag.get('content'):
                        description = tag['content'].strip()
                        if is_valid_content(description):
                            break
                
                web_loader_metadata = {
                    "title": title,
                    "description": description,
                    "content": content,
                    "source": url,
                    "language": "",
                    "url": url
                }
                
                web_loader_content = content
                
                # Check if this is a standard unassigned ARNS page
                if title.strip() == "ArNS - Arweave Name System":
                    logger.info(f"Skipping {url} - standard unassigned ARNS page")
                    return []
                
                logger.info(f"✅ BeautifulSoup fallback successful for {url}")
        
        # If we have content, process it
        if web_loader_metadata and web_loader_content:
            # Create enhanced metadata
            enhanced_metadata = extract_enhanced_metadata_from_web_loader(web_loader_metadata, url)
            
            # Create weighted content chunks
            chunks = create_weighted_chunks_from_web_loader(web_loader_metadata, enhanced_metadata)
            
            if chunks:
                return create_weighted_embeddings(chunks, url, is_arns)
        
        logger.warning(f"No valid content extracted from {url}")
        return []
        
    except Exception as e:
        logger.error(f"Enhanced webpage indexing failed for {url}: {e}")
        return []

def extract_enhanced_metadata_from_web_loader(web_loader_metadata, url):
    """
    Extract enhanced metadata from WebBaseLoader results.
    """
    metadata = {
        "url": url,
        "web_loader_title": web_loader_metadata.get("title", ""),
        "web_loader_description": web_loader_metadata.get("description", ""),
        "web_loader_content": web_loader_metadata.get("content", ""),
        "web_loader_language": web_loader_metadata.get("language", ""),
        "web_loader_source": web_loader_metadata.get("source", ""),
        "title": web_loader_metadata.get("title", ""),
        "description": web_loader_metadata.get("description", ""),
        "content_type": "webpage",
        "domain": url.split("//")[-1].split("/")[0] if "//" in url else url,
        "path": "/" + "/".join(url.split("//")[-1].split("/")[1:]) if "//" in url and len(url.split("//")[-1].split("/")) > 1 else "/",
        "indexed_at": datetime.now().isoformat(),
        "processing_method": "web_loader_primary"
    }
    
    # Detect non-assigned ARNS
    content = web_loader_metadata.get("content", "")
    if "Future home of something rather bullish" in content:
        metadata["is_non_assigned_arns"] = True
        metadata["arns_status"] = "non_assigned"
        metadata["content_type"] = "non_assigned_arns"
    else:
        metadata["is_non_assigned_arns"] = False
        metadata["arns_status"] = "assigned"
    
    return metadata

def create_weighted_chunks_from_web_loader(web_loader_metadata, enhanced_metadata):
    """
    Create efficient, high-quality content chunks from WebBaseLoader results.
    Focus on the most important content with minimal redundancy.
    """
    chunks = []
    
    title = web_loader_metadata.get("title", "")
    description = web_loader_metadata.get("description", "")
    content = web_loader_metadata.get("content", "")
    
    def clean_and_enhance_text(text):
        """Enhanced text cleaning for embeddings - aggressively removes noise and normalizes content"""
        if not text:
            return ""
        
        # Ultra-aggressive newline and whitespace removal
        text = re.sub(r'\n+', ' ', text)
        text = re.sub(r'\r+', ' ', text)
        text = re.sub(r'\t+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Remove HTML entities and tags
        text = re.sub(r'&[a-zA-Z0-9#]+;', ' ', text)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        # Remove redundant content patterns
        redundant_patterns = [
            r'^\s*(loading|error|404|not found|access denied|page not found)\s*$',
            r'^\s*(javascript|css|html|xml|json)\s*$',
            r'^\s*[^\w\s]*\s*$',  # Only special characters
            r'^\s*$',  # Only whitespace
        ]
        
        for pattern in redundant_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return ""
        
        # Remove excessive repetition (same word repeated many times)
        words = text.split()
        if len(words) > 3:
            word_counts = {}
            for word in words:
                word_counts[word.lower()] = word_counts.get(word.lower(), 0) + 1
            
            # If any word appears more than 50% of the time, it's likely noise
            max_repetition = max(word_counts.values()) if word_counts else 0
            if max_repetition > len(words) * 0.5:
                return ""
        
        # Remove content that's mostly empty or just repeated characters
        if len(text) < 5:
            return ""
        
        # Check if content is mostly repeated characters
        if len(set(text)) < 3 and len(text) > 10:
            return ""
        
        # More lenient length requirements
        if len(text) > 5000:
            return ""
        
        return text
    
    def extract_key_content(text, max_length=600):
        """Intelligent content extraction prioritizing relevance and coherence"""
        if not text:
            return ""
        
        # Clean the text
        cleaned = clean_and_enhance_text(text)
        if not cleaned:
            return ""
        
        # If text is short enough, use it all
        if len(cleaned) <= max_length:
            return cleaned
        
        # Split into sentences more intelligently
        sentences = re.split(r'[.!?]+', cleaned)
        scored_sentences = []
        
        # Define relevance scoring
        high_priority_terms = ['arlink', 'arweave', 'blockchain', 'web3', 'decentralized', 'permanent', 'storage']
        medium_priority_terms = ['network', 'protocol', 'data', 'content', 'service', 'platform', 'app']
        low_priority_terms = ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with']
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 8:
                continue
            
            # Calculate sentence score
            sentence_lower = sentence.lower()
            high_score = sum(2 for term in high_priority_terms if term in sentence_lower)
            medium_score = sum(1 for term in medium_priority_terms if term in sentence_lower)
            low_score = sum(0.1 for term in low_priority_terms if term in sentence_lower)
            
            # Length bonus (prefer medium-length sentences)
            length_bonus = 0
            if 20 <= len(sentence) <= 100:
                length_bonus = 1
            elif len(sentence) > 100:
                length_bonus = 0.5
            
            total_score = high_score + medium_score + low_score + length_bonus
            
            scored_sentences.append((sentence, total_score))
        
        # Sort by score and select top sentences
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        
        selected_sentences = []
        current_length = 0
        
        for sentence, score in scored_sentences:
            if current_length + len(sentence) <= max_length:
                selected_sentences.append(sentence)
                current_length += len(sentence)
            else:
                break
        
        # If we have very few sentences, add some lower-scored ones
        if len(selected_sentences) < 2 and len(scored_sentences) > 2:
            for sentence, score in scored_sentences[2:]:
                if current_length + len(sentence) <= max_length:
                    selected_sentences.append(sentence)
                    current_length += len(sentence)
                else:
                    break
        
        return '. '.join(selected_sentences) + '.' if selected_sentences else cleaned[:max_length]
    
    # Optimized chunking strategy - create only 2 high-quality chunks maximum
    
    # 1. Create a comprehensive title+description chunk (highest priority)
    title_chunk_text = ""
    if title and len(title.strip()) > 5:  # More lenient title validation
        enhanced_title = clean_and_enhance_text(title)
        if enhanced_title:
            title_chunk_text = f"Title: {enhanced_title}"
            if description and len(description.strip()) > 10:  # More lenient description validation
                enhanced_desc = clean_and_enhance_text(description[:200])
                title_chunk_text += f" - {enhanced_desc}"
    
    if title_chunk_text:
        chunks.append({
            'text': title_chunk_text,
            'weight': 5.0,  # Highest weight for title chunk
            'type': 'title',
            'section': 'Title',
            'content_quality': 'high',
            'web_loader_title': title,
            'web_loader_description': description,
            'web_loader_content': content,
            'chunk_length': len(title_chunk_text),
            **enhanced_metadata
        })
    
    # 2. Create a single, optimized content chunk (more lenient)
    if content and len(content.strip()) > 20:  # More lenient content validation
        key_content = extract_key_content(content)
        if key_content and len(key_content) > 15:  # More lenient content requirement
            # Create content chunk with context
            content_chunk_text = key_content
            if title:
                content_chunk_text = f"Content about {title}: {content_chunk_text}"
            
            chunks.append({
                'text': content_chunk_text,
                'weight': 4.0,  # High weight for content
                'type': 'content',
                'section': 'Content',
                'content_quality': 'high',
                'chunk_length': len(content_chunk_text),
                'web_loader_title': title,
                'web_loader_description': description,
                'web_loader_content': content,
                **enhanced_metadata
            })
    
    # Ensure we have at least one chunk (robust fallback)
    if not chunks:
        if title and len(title.strip()) > 3:
            # Fallback: create minimal title chunk
            chunks.append({
                'text': f"Title: {title}",
                'weight': 3.0,
                'type': 'title',
                'section': 'Title',
                'content_quality': 'medium',
                'web_loader_title': title,
                'web_loader_description': description,
                'web_loader_content': content,
                'chunk_length': len(title),
                **enhanced_metadata
            })
        elif content and len(content.strip()) > 10:
            # Fallback: create content chunk from raw content
            raw_content = content.strip()[:500]  # Limit to 500 chars
            chunks.append({
                'text': f"Content: {raw_content}",
                'weight': 2.0,
                'type': 'content',
                'section': 'Content',
                'content_quality': 'medium',
                'web_loader_title': title,
                'web_loader_description': description,
                'web_loader_content': content,
                'chunk_length': len(raw_content),
                **enhanced_metadata
            })
        else:
            # Last resort: create a basic chunk from URL
            url_parts = url.split('/')
            domain = url_parts[-1] if url_parts else url
            chunks.append({
                'text': f"Page: {domain}",
                'weight': 1.0,
                'type': 'title',
                'section': 'Title',
                'content_quality': 'low',
                'web_loader_title': title,
                'web_loader_description': description,
                'web_loader_content': content,
                'chunk_length': len(domain),
                **enhanced_metadata
            })
    
    return chunks

# Update ARNS search endpoint to use ARNS-exclusive index/meta
@app.get("/searchweb")
def search_web(query: str, top_k: int = TOP_K, arns_only: bool = False, filter_nsfw: bool = False):
    if arns_only:
        # Search ARNS-exclusive collection
        try:
            if not arns_collection:
                logger.warning("No ARNS collection available")
                return {"results": []}
            
            # Create query embedding
            query_embedding = embed_text(query)
            
            # Search in ARNS collection
            results = arns_collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=top_k * 3,
                include=["metadatas", "documents", "distances"]
            )
            
            if not results['ids'] or not results['ids'][0]:
                logger.warning("No ARNS results found")
                return {"results": []}
            
            # Process results
            raw_results = []
            for i, (id_val, metadata, document, distance) in enumerate(zip(
                results['ids'][0], 
                results['metadatas'][0], 
                results['documents'][0], 
                results['distances'][0]
            )):
                if metadata and document:
                    score = 1.0 - (distance / 2.0)
                    raw_results.append({
                        "score": score,
                        **metadata,
                        "chunk": document
                    })
            
            # Group results
            grouped = []
            used = [False] * len(raw_results)
            for i, res in enumerate(raw_results):
                if used[i]:
                    continue
                group = [res]
                used[i] = True
                for j in range(i + 1, len(raw_results)):
                    if used[j]:
                        continue
                    if abs(res['score'] - raw_results[j]['score']) < 0.01:
                        group.append(raw_results[j])
                        used[j] = True
                group.sort(key=lambda x: -x['score'])
                main = group[0]
                duplicates = group[1:]
                main['duplicates'] = duplicates
                main['has_duplicates'] = len(duplicates) > 0
                grouped.append(main)
            
            grouped.sort(key=lambda x: -x['score'])
            grouped = grouped[:top_k]
            logger.info(f"ARNS-only search returned {len(grouped)} grouped results (top_k={top_k}).")
            return {"results": grouped}
            
        except Exception as e:
            logger.error(f"ARNS search failed: {e}")
            return {"results": []}
    else:
        return enhanced_search_modality(query, top_k, "web", filter_nsfw)

@app.get("/searchimage")
def search_image(query: str, top_k: int = TOP_K, arns_only: bool = False, filter_nsfw: bool = False):
    return enhanced_search_modality(query, top_k, "image", filter_nsfw)

@app.get("/searchaudio")
def search_audio(query: str, top_k: int = TOP_K, arns_only: bool = False, filter_nsfw: bool = False):
    return enhanced_search_modality(query, top_k, "audio", filter_nsfw)

@app.get("/searchvideo")
def search_video(query: str, top_k: int = TOP_K, arns_only: bool = False, filter_nsfw: bool = False):
    return enhanced_search_modality(query, top_k, "video", filter_nsfw)

API_URL = "https://cu.ardrive.io/dry-run?process-id=qNvAoz0TgcH7DMg8BCVn8jF32QH5L6T29VjHxhHqqGE"
HEADERS = {
    'accept': '*/*',
    'content-type': 'application/json',
    'origin': 'https://www.ao.link',
    'referer': 'https://www.ao.link/',
}

def fetch_page(cursor=None, limit=1000, max_retries=5):
    tags = [
        {"name":"Action","value":"Paginated-Records"},
        {"name":"Limit","value":str(limit)},
        {"name":"Sort-By","value":"startTimestamp"},
        {"name":"Sort-Order","value":"desc"},
        {"name":"Data-Protocol","value":"ao"},
        {"name":"Type","value":"Message"},
        {"name":"Variant","value":"ao.TN.1"}
    ]
    if cursor:
        tags.append({"name":"Cursor","value":cursor})
    else:
        tags.append({"name":"Cursor","value":"homedepot"})
    payload = {
        "Id": "1234",
        "Target": "qNvAoz0TgcH7DMg8BCVn8jF32QH5L6T29VjHxhHqqGE",
        "Owner": "1234",
        "Anchor": "0",
        "Data": "1234",
        "Tags": tags
    }
    for attempt in range(max_retries):
        try:
            response = requests.post(API_URL, headers=HEADERS, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"[ARNS fetch_page] Attempt {attempt+1} failed: {e}")
            time.sleep(2 ** attempt)  # Exponential backoff
    raise Exception(f"[ARNS fetch_page] All {max_retries} attempts failed.")

def get_all_arns():
    all_items = []
    cursor = None
    while True:
        data = fetch_page(cursor)
        message = data.get("Messages", [{}])[0]
        data_str = message.get("Data")
        if not data_str:
            print("No Data field found in response")
            break
        page_data = json.loads(data_str)
        items = page_data.get("items", [])
        all_items.extend(items)
        has_more = page_data.get("hasMore", False)
        cursor = page_data.get("nextCursor")
        print(f"[ARNS] Fetched {len(items)} items, hasMore={has_more}, nextCursor={cursor}")
        if not has_more or not cursor:
            break
    return all_items

def arns_index_loop():
    while True:
        try:
            arns_list = get_all_arns()
            print(f"[ARNS] Total ARNS fetched: {len(arns_list)}")
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = []
                for arn in arns_list:
                    url = f"https://{arn['name']}.arweave.net"
                    unique_id = extract_txid_or_arns_name(url)
                    with indexed_txids_lock:
                        already_indexed = unique_id in indexed_txids
                    if not already_indexed:
                        futures.append(executor.submit(index_file, url, True))
                    else:
                        logger.info(f"Skipping already indexed ARNS: {url}")
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        print(f"[ARNS] Error indexing ARNS: {e}")
            time.sleep(600)  # Sleep 10 minutes before next ARNS fetch
        except Exception as e:
            print(f"[ARNS Indexer Error] {e}")
            time.sleep(30)

def index_modality_loop(modality, content_types):
    logger.info(f"Starting index_modality_loop for {modality}")
    cursor = None if modality == "video" else load_cursor(modality)
    while True:
        try:
            query = f'''
            query ($cursor: String) {{
              transactions(
                after: $cursor
                first: {BATCH_SIZE}
                tags: [{{ name: "Content-Type", values: {json.dumps(content_types)} }}]
              ) {{
                pageInfo {{ hasNextPage }}
                edges {{ cursor node {{ id }} }}
              }}
            }}'''
            variables = {"cursor": cursor} if cursor else {}
            data = fetch_graphql(query, variables)
            edges = data["data"]["transactions"]["edges"]
            txid_url_pairs = []
            for edge in edges:
                txid = edge["node"]["id"]
                cursor = edge["cursor"]
                url = f"https://arweave.net/{txid}"
                normalized_url = normalize_url(url)
                with indexed_txids_lock:
                    already_indexed = normalized_url in indexed_txids
                if not already_indexed:
                    detected = detect_file_type(url)
                    if detected == modality:
                        txid_url_pairs.append((normalized_url, url))
            with ThreadPoolExecutor(max_workers=16) as executor:
                futures = []
                for normalized_url, url in txid_url_pairs:
                    futures.append(executor.submit(index_file, url))
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"Indexing failed: {e}")
            with indexed_txids_lock:
                for normalized_url, _ in txid_url_pairs:
                    indexed_txids.add(normalized_url)
            if modality != "video":
                save_cursor(cursor, modality)
            time.sleep(POLL_INTERVAL)
        except Exception as e:
            logger.error(f"[{modality.capitalize()} Indexer Error] {e}")
            time.sleep(30)

def search_with_metadata_filters(query: str, top_k: int = TOP_K, modality: str = "web", 
                                filters: dict = None, where: dict = None):
    """
    Search with metadata filtering capabilities.
    
    Args:
        query: Search query
        top_k: Number of results to return
        modality: Content modality to search
        filters: Dictionary of metadata filters (e.g., {"author": "John", "language": "en"})
        where: ChromaDB where clause for filtering
    """
    logger.info(f"Metadata-filtered search called for modality '{modality}' with query '{query}' and filters: {filters}")
    
    try:
        # Get the appropriate collection
        collection = collections.get(modality)
        if not collection:
            logger.warning(f"No ChromaDB collection for modality '{modality}'")
            return {"results": []}
        
        # Create query embedding
        query_embedding = embed_text(query)
        
        # Prepare where clause for filtering
        where_clause = where or {}
        
        # Add filters to where clause
        if filters:
            for key, value in filters.items():
                if value:
                    where_clause[key] = value
        
        # Search in ChromaDB with filters
        results = collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k * 3,
            where=where_clause if where_clause else None,
            include=["metadatas", "documents", "distances"]
        )
        
        if not results['ids'] or not results['ids'][0]:
            logger.warning(f"No results found for modality '{modality}' with filters")
            return {"results": []}
        
        # Process results
        raw_results = []
        for i, (id_val, metadata, document, distance) in enumerate(zip(
            results['ids'][0], 
            results['metadatas'][0], 
            results['documents'][0], 
            results['distances'][0]
        )):
            if metadata and document:
                # Convert distance to similarity score
                score = 1.0 - (distance / 2.0)
                
                # Apply content type weighting for web results
                adjusted_score = score
                if modality == "web" and metadata.get("content_type") == "title":
                    adjusted_score *= 1.5
                elif modality == "web" and metadata.get("content_type") == "description":
                    adjusted_score *= 1.2
                
                raw_results.append({
                    "score": adjusted_score,
                    "original_score": score,
                    **metadata,
                    "chunk": document
                })
        
        # Group results
        SCORE_GROUP_THRESHOLD = 0.01
        grouped = []
        used = [False] * len(raw_results)
        
        for i, res in enumerate(raw_results):
            if used[i]:
                continue
            group = [res]
            used[i] = True
            
            for j in range(i + 1, len(raw_results)):
                if used[j]:
                    continue
                if abs(res['original_score'] - raw_results[j]['original_score']) < SCORE_GROUP_THRESHOLD:
                    group.append(raw_results[j])
                    used[j] = True
            
            group.sort(key=lambda x: -x['score'])
            main = group[0]
            duplicates = group[1:]
            main['duplicates'] = duplicates
            main['has_duplicates'] = len(duplicates) > 0
            grouped.append(main)
        
        grouped.sort(key=lambda x: -x['score'])
        grouped = grouped[:top_k]
        
        logger.info(f"Metadata-filtered search returned {len(grouped)} results")
        return {"results": grouped}
        
    except Exception as e:
        logger.error(f"Error in metadata-filtered search: {e}")
        return {"results": []}

# Add metadata search endpoint
@app.get("/searchweb/metadata")
def search_web_with_metadata(
    query: str, 
    top_k: int = TOP_K,
    author: str = None,
    language: str = None,
    content_type: str = None,
    domain: str = None,
    has_title: bool = None,
    has_description: bool = None
    ):
    """Search web content with metadata filtering."""
    filters = {}
    if author:
        filters["author"] = author
    if language:
        filters["language"] = language
    if content_type:
        filters["content_type"] = content_type
    if domain:
        filters["domain"] = domain
    if has_title is not None:
        filters["has_title"] = has_title
    if has_description is not None:
        filters["has_description"] = has_description
    
    return search_with_metadata_filters(query, top_k, "web", filters)



