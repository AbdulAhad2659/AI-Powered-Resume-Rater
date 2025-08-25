import os
import logging
from pathlib import Path

from dotenv import load_dotenv

# Optional imports kept to preserve logic
try:
    from groq import Groq
except ImportError:
    Groq = None

try:
    import langextract as lx  # not used, but preserved
except ImportError:
    lx = None

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Env
load_dotenv()

AUDIO_SAVE_DIR = os.getenv("AUDIO_SAVE_DIR", "./tts_outputs")
Path(AUDIO_SAVE_DIR).mkdir(parents=True, exist_ok=True)

RECOMMENDED_FILE = os.getenv("RECOMMENDED_FILE", "./recommended.txt")
STATIC_DIR = os.getenv("STATIC_DIR", "./static")
Path(STATIC_DIR).mkdir(parents=True, exist_ok=True)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GOOGLE_API_KEY:
    logger.warning("GOOGLE_API_KEY not set. Gemini calls will fail unless provided.")
if not GROQ_API_KEY:
    logger.info("GROQ_API_KEY not set — Groq fallback will be unavailable.")

# Initialize Groq client if key provided
groq_client = None
if GROQ_API_KEY and Groq is not None:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        logger.info("Groq client initialized for fallback.")
    except Exception as e:
        logger.warning("Failed to initialize Groq client: %s", e)
        groq_client = None
        