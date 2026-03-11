"""
Advanced Hybrid Timestamp Estimation Module
Implements narrative-aware duration pacing based on:
1. Emotion analysis (energy multipliers)
2. Dialogue density vs Action density
3. Lexical triggers within stage directions
4. Proportional scaling between explicit anchors
"""

import re
import logging
from typing import List, Dict, Tuple, Any

logger = logging.getLogger("phase_1.timestamp_estimator")

# =========================================================================
# CONSTANTS & CONFIGURATION
# =========================================================================

# Base speaking rates
WORDS_PER_MINUTE_DIALOGUE = 180.0
WORDS_PER_MINUTE_ACTION = 120.0

# Emotion Energy Multipliers (Duration Modifiers)
# Lower multiplier = faster scene (less time)
# Higher multiplier = slower scene (more time)
EMOTION_ENERGY_MULTIPLIERS = {
    # High Energy / Fast
    "joy": 0.85,
    "hilarity": 0.80,
    "humorous": 0.85,
    "humor": 0.85,
    "anger": 0.85,
    "panic": 0.75,
    "suspense": 0.90,
    "urgency": 0.75,
    "fear": 0.85,
    
    # Low Energy / Slow
    "sadness": 1.30,
    "grief": 1.40,
    "romance": 1.20,
    "reflection": 1.30,
    "awe": 1.25,
    "melancholy": 1.35,
    "neutral": 1.00
}

# Lexical Triggers in Stage Directions
# These add or subtract absolute seconds
STATIC_TIME_MODIFIERS = {
    r"\b(pause|pauses)\b": 3.0,
    r"\b(silence)\b": 5.0,
    r"\b(long beat|long pause|beat)\b": 4.0,
    r"\b(hesitates|stops)\b": 2.0,
    r"\b(slowly|takes their time|glares)\b": 3.0,
}

# Transition Modifiers
TRANSITION_TIMINGS = {
    r"\bCUT TO:\b": 0.5,
    r"\b(FADE TO|FADE OUT|DISSOLVE TO)\b": 4.0,
}


# =========================================================================
# CORE TIMING LOGIC
# =========================================================================

def estimate_raw_duration(scene: Dict[str, Any], emotion_data: Dict[str, Any] = None) -> float:
    """
    Calculates the 'raw' estimated duration of a scene using narrative signals.
    """
    content = scene.get("content", "") or scene.get("text", "")
    if not content:
        return 2.0  # Minimum fallback 2 seconds

    # 1. Base estimation using Dialogue vs Action split
    lines = content.split('\n')
    dialogue_words = 0
    action_words = 0
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        
        # Simple heuristic: If line is indented or in quotes, it's likely dialogue.
        # Alternatively, if it starts with an uppercase name followed by text.
        # For a robust pass, we check if it doesn't look like a standard slugline or transition
        is_dialogue = False
        if line.startswith(' ' * 10) or stripped.startswith('"') or (':' in stripped and len(stripped.split(':')[0]) < 20):
             is_dialogue = True
             
        word_count = len(stripped.split())
        if is_dialogue:
            dialogue_words += word_count
        else:
            action_words += word_count

    base_duration = (dialogue_words / WORDS_PER_MINUTE_DIALOGUE) * 60 + \
                    (action_words / WORDS_PER_MINUTE_ACTION) * 60

    # 2. Emotion Energy Modifier
    multiplier = 1.0
    if emotion_data:
        primary_emotion = emotion_data.get("primary_emotion", "neutral").lower()
        multiplier = EMOTION_ENERGY_MULTIPLIERS.get(primary_emotion, 1.0)
    
    modified_duration = base_duration * multiplier

    # 3. Lexical Triggers (Stage Directions)
    static_bonus = 0.0
    for pattern, seconds in STATIC_TIME_MODIFIERS.items():
        matches = len(re.findall(pattern, content, flags=re.IGNORECASE))
        static_bonus += (matches * seconds)
        
    for pattern, seconds in TRANSITION_TIMINGS.items():
        if re.search(pattern, content, flags=re.IGNORECASE):
            static_bonus += seconds

    final_duration = modified_duration + static_bonus
    
    # Hard clamp to ensure a scene isn't impossibly short or long
    # e.g., minimum 5 seconds, max 20 minutes
    return round(max(5.0, min(final_duration, 1200.0)), 2)


# =========================================================================
# INTERPOLATION ENGINE
# =========================================================================

def interpolate_missing_timestamps(timestamps: List[Dict[str, Any]], scenes: List[Dict[str, Any]], emotions_map: Dict[str, Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Takes a timeline with some explicit anchors (start_time not None) 
    and missing gaps (start_time is None).
    Proportionally scales the estimated raw duration of the missing scenes 
    to seamlessly fill the chronological gaps between anchors.
    """
    if not timestamps:
        return []

    # Map emotions for easy lookup
    emotions_map = emotions_map or {}

    # Step 1: Ensure boundaries exist
    if timestamps[0]["start"] is None:
        timestamps[0]["start"] = 0.0
        timestamps[0]["source"] = "inferred_start"

    # Step 2: Identify chunks (sequences bounded by explicit anchors)
    chunks = []
    current_chunk = []
    
    for i, ts in enumerate(timestamps):
        if ts["start"] is not None:
            # Anchor hit! Close the previous chunk if it has missing items.
            if current_chunk:
                chunks.append({
                    "start_anchor_idx": current_chunk[0] - 1, # The anchor before the gap
                    "end_anchor_idx": i,                      # The anchor after the gap
                    "missing_indices": current_chunk.copy()
                })
                current_chunk = []
        else:
            current_chunk.append(i)
            
    # Handle an open-ended tail (no end anchor)
    if current_chunk:
        chunks.append({
            "start_anchor_idx": current_chunk[0] - 1,
            "end_anchor_idx": None, # Will just play out at 1.0 scale
            "missing_indices": current_chunk.copy()
        })

    # Step 3: Interpolate each chunk
    for chunk in chunks:
        missing_indices = chunk["missing_indices"]
        start_anchor_ts = timestamps[chunk["start_anchor_idx"]]["end"] or timestamps[chunk["start_anchor_idx"]]["start"]
        
        # Calculate raw durations for all missing scenes in this chunk
        raw_durations = []
        for idx in missing_indices:
            scene = scenes[idx]
            scene_id = scene.get("scene_id", "")
            emotion_data = emotions_map.get(scene_id)
            raw_dur = estimate_raw_duration(scene, emotion_data)
            raw_durations.append(raw_dur)
            
        total_raw_duration = sum(raw_durations)
        
        # If bounded, scale. If open-ended, standard 1.0 scale.
        scale_factor = 1.0
        if chunk["end_anchor_idx"] is not None:
            end_anchor_ts = timestamps[chunk["end_anchor_idx"]]["start"]
            available_time = max(0.0, end_anchor_ts - start_anchor_ts)
            
            if total_raw_duration > 0:
                scale_factor = available_time / total_raw_duration
            
            # Apply slight smoothing limit to scale factor (don't scale higher than 3x or lower than 0.3x)
            scale_factor = max(0.3, min(scale_factor, 3.0))

        # Apply scaled durations
        current_time = start_anchor_ts
        for idx, raw_dur in zip(missing_indices, raw_durations):
            scaled_dur = raw_dur * scale_factor
            timestamps[idx]["start"] = round(current_time, 1)
            timestamps[idx]["end"] = round(current_time + scaled_dur, 1)
            timestamps[idx]["duration"] = round(scaled_dur, 1)
            if scale_factor != 1.0 and chunk["end_anchor_idx"] is not None:
                timestamps[idx]["source"] = "interpolated"
            else:
                timestamps[idx]["source"] = "estimated_unbounded"
            current_time += scaled_dur
            
    # Clean up any missing "end" or "duration" for explicit anchors
    for i, ts in enumerate(timestamps):
        if ts.get("end") is None:
            if i + 1 < len(timestamps) and timestamps[i+1].get("start") is not None:
                ts["end"] = timestamps[i+1]["start"]
            else:
                scene = scenes[i]
                emotion_data = emotions_map.get(scene.get("scene_id", ""))
                ts["end"] = ts["start"] + estimate_raw_duration(scene, emotion_data)
                
            ts["duration"] = round(ts["end"] - ts["start"], 1)

    return timestamps
