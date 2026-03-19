"""
Configuration for the Full-Context Experimental Pipeline.

Fully isolated — does NOT import from config.py or any existing module.
"""

# =============================================================================
# LLM CONFIGURATION
# =============================================================================
LLM_MODEL = "Qwen/Qwen2.5-7B-Instruct"
LLM_TEMPERATURE = 0.3          # Low temperature for near-deterministic output
LLM_MAX_OUTPUT_TOKENS = 4096   # Large enough for full-script JSON response

# Context window limits
MODEL_CONTEXT_WINDOW = 32768   # Qwen 2.5 7B context size
TOKEN_THRESHOLD_RATIO = 0.70   # Use at most 70% of context for input
MAX_INPUT_TOKENS = int(MODEL_CONTEXT_WINDOW * TOKEN_THRESHOLD_RATIO)  # ~22937

# =============================================================================
# EMOTIONAL SMOOTHING
# =============================================================================
EMOTIONAL_DELTA_CAP = 0.3          # Max energy delta between adjacent scenes
CONFIDENCE_PENALTY_ON_FLIP = 0.15  # Confidence reduction on emotion label flip
ENABLE_SMOOTHING = True            # Hard constraint flag

# =============================================================================
# DETERMINISTIC LIGHTING
# =============================================================================
LIGHTING_BLEND_FACTOR = 0.6    # Blend weight: 60% target + 40% previous
BASE_INTENSITY = 40.0          # Minimum lighting intensity (%)
ENERGY_INTENSITY_SCALE = 50.0  # Energy → intensity multiplier (0-1 → 0-50%)

# Palette split ratios (must sum to 1.0)
PRIMARY_COLOR_RATIO = 0.60
SECONDARY_COLOR_RATIO = 0.25
ANCHOR_COLOR_RATIO = 0.15

# =============================================================================
# VALIDATION & METRICS
# =============================================================================
ENABLE_DRIFT_METRICS = True    # Calculate and print emotional drift score

# =============================================================================
# OUTPUT
# =============================================================================
OUTPUT_DIR = "experimental_full_context_pipeline/output"
