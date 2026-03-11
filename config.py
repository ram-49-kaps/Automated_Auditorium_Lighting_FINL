"""
Configuration file for Automated Auditorium Lighting System
"""

# ============================================================================
# TIMING CONFIGURATION
# ============================================================================
WORDS_PER_MINUTE = 150
SCENE_TRANSITION_BUFFER = 2
DEFAULT_FADE_DURATION = 1.5

# ============================================================================
# SCENE SEGMENTATION
# ============================================================================
MAX_WORDS_PER_SCENE = 400   # Word budget per scene (was 120 — caused always-33-scenes bug)
MIN_WORDS_PER_SCENE = 50    # Don't create micro-scenes below this

# ============================================================================
# EMOTION DETECTION
# ============================================================================
EMOTION_MODEL = "j-hartmann/emotion-english-distilroberta-base"
EMOTION_THRESHOLD = 0.3
USE_ML_EMOTION = True
USE_ZERO_SHOT_EMOTION = False  # Set True only if bart-large-mnli is pre-downloaded (~1.6GB)

# Basic 7 emotions (ML model output)
EMOTION_CATEGORIES_BASIC = [
    "anger", "disgust", "fear", "joy", "neutral", "sadness", "surprise"
]

# Extended 19 emotions (keyword enrichment + zero-shot)
EMOTION_CATEGORIES = [
    "anger", "disgust", "fear", "joy", "neutral", "sadness", "surprise",
    "nostalgia", "mystery", "romantic", "anticipation", "hope", "triumph",
    "tension", "despair", "serenity", "confusion", "awe", "jealousy"
]

# ============================================================================
# SCENE DETECTION KEYWORDS
# ============================================================================
SCENE_MARKERS = [
    "INT.", "EXT.", "FADE IN", "FADE OUT", "CUT TO", 
    "SCENE", "ACT", "INTERIOR", "EXTERIOR", "INT", "EXT"
]

# ============================================================================
# FILE PATHS
# ============================================================================
DATA_DIR = "data"
RAW_SCRIPTS_DIR = f"{DATA_DIR}/raw_scripts"
CLEANED_SCRIPTS_DIR = f"{DATA_DIR}/cleaned_scripts"
SEGMENTED_SCRIPTS_DIR = f"{DATA_DIR}/segmented_scripts"
OUTPUT_DIR = f"{DATA_DIR}/standardized_output"

# 🆕 NEW PATHS
KNOWLEDGE_DIR = f"{DATA_DIR}/auditorium_knowledge"
LIGHTING_CUES_DIR = f"{DATA_DIR}/lighting_cues"

# ============================================================================
# OUTPUT FORMAT
# ============================================================================
JSON_INDENT = 2
INCLUDE_METADATA = True
TIMESTAMP_FORMAT = "seconds"

# ============================================================================
# 🆕 RAG CONFIGURATION
# ============================================================================
USE_VECTOR_DB = True  # Use FAISS for fixture retrieval
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Sentence transformer model

# ============================================================================
# 🆕 CUE GENERATION
# ============================================================================
USE_LLM_GENERATION = False  # Set to True if you have OpenAI API key
OPENAI_API_KEY = None  # Set your API key here or in environment variable
LLM_MODEL = "gpt-4"  # or "gpt-3.5-turbo"
FALLBACK_TO_RULES = True  # Use rule-based if LLM fails

# LangChain Configuration
LANGCHAIN_VERBOSE = False  # Enable LangChain debug logging
LLM_TEMPERATURE = 0.3      # Lower = more deterministic lighting choices
LLM_MAX_TOKENS = 1000      # Limit response size

# ============================================================================
# 🆕 DMX CONFIGURATION
# ============================================================================
DMX_UNIVERSE = 1
DMX_REFRESH_RATE = 44  # Hz (standard DMX refresh rate)
ARTNET_IP = "192.168.1.100"  # IP of Avolites Titan console
ARTNET_PORT = 6454  # Standard Art-Net port

# ============================================================================
# 🆕 VALIDATION
# ============================================================================
STRICT_VALIDATION = True  # Reject invalid cues
ALLOW_WARNINGS = True  # Generate cues even with warnings

# ============================================================================
# LOGGING
# ============================================================================
LOG_LEVEL = "INFO"
VERBOSE_OUTPUT = True

# ============================================================================
# 🆕 LIGHTKEY OSC CONFIGURATION
# ============================================================================
LIGHTKEY_ENABLED = True              # Enable/disable LightKey output
LIGHTKEY_OSC_IP = "127.0.0.1"       # Same machine
LIGHTKEY_OSC_PORT = 8000            # LightKey default OSC port (verify in LightKey settings!)
LIGHTKEY_FIXTURE_MAPPING = {
    # Map your fixture IDs to LightKey fixture numbers
    "PAR_1": 1,        # PAR_1 → LightKey Fixture #1
    "PAR_2": 2,        # PAR_2 → LightKey Fixture #2
    "MovingHead_1": 3, # etc.
}

# ============================================================================
# PHASE 1 — TEXT ACQUISITION & STRUCTURING
# ============================================================================
OCR_CONFIDENCE_THRESHOLD = 0.85
OCR_PROVIDER = "mistral"
OCR_AVG_LINE_LENGTH_MIN = 10
OCR_AVG_LINE_LENGTH_MAX = 500
OCR_NOISE_RATIO_MAX = 0.05
CHUNK_MAX_LINES = 150
CHUNK_OVERLAP_LINES = 10
PHASE1_LLM_MODEL = "Qwen/Qwen2.5-7B-Instruct"
PHASE1_LLM_TEMPERATURE = 0.0
PHASE1_LLM_MAX_RETRIES = 1
PHASE1_LLM_MAX_NEW_TOKENS = 2048
SCENE_GAP_TOLERANCE_LINES = 2
SCENE_COVERAGE_THRESHOLD = 0.80
TIMESTAMP_MAX_JUMP_SECONDS = 1800

# Set to False to skip LLM and use rule-based segmentation (saves API credits)
PHASE1_USE_LLM = False

# ============================================================================
# OLLAMA LOCAL LLM CONFIGURATION
# ============================================================================
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "phi3:latest"
OLLAMA_TIMEOUT = 60          # seconds per request (balance between giving time & avoiding hangs)
OLLAMA_TEMPERATURE = 0.1     # low for deterministic outputs
OLLAMA_ENABLED = True        # master switch — set False to skip all Ollama calls