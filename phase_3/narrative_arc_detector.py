import logging
import numpy as np
from typing import List, Dict
from models.narrative_state import Scene, Script, GlobalMetaAnchor

logger = logging.getLogger("phase_3.narrative_arc")

def detect_narrative_arc_phases(script: Script) -> Script:
    """
    Phase 3: Analyzes cross-scene momentum globally rather than locally.
    Reassigns Narrative Arc Phases accurately based on Energy and Contextual Tension peaks.
    """
    logger.info("Starting Phase 3: Global Narrative Arc Detection")
    
    # Flatten scenes
    all_scenes = []
    for act in script.acts:
        all_scenes.extend(act.scenes)
        
    if not all_scenes:
        return script
        
    # Gather tension sequence.
    # In V3, tension = (energy * 0.4) + (seriousness * 0.3) + (negative_emotion_weight * 0.3)
    # We approximate "negative emotion" by pulling confidence if the scene's dominant surface emotion is Fear or Anger.
    tension_sequence = []
    for scene in all_scenes:
        scene_tension = 0.0
        if not scene.beats:
            tension_sequence.append(0.0)
            continue
            
        avg_energy = sum(b.scene_energy_score for b in scene.beats) / len(scene.beats)
        
        # calculate negative emotion density
        neg_beats = [b for b in scene.beats if b.surface_emotion in ["fear", "anger", "disgust", "panic"]]
        neg_density = len(neg_beats) / len(scene.beats) 
        
        # seriousness context limit
        seriousness = script.meta_anchor.narrative_seriousness_score
        
        # Composite Volatility Vector (tension)
        scene_tension = (avg_energy * 0.4) + (seriousness * 0.3) + (neg_density * 0.3)
        tension_sequence.append(scene_tension)
        
    # 2. Find Peaks using scipy equivalent local mathematical logic
    if len(tension_sequence) < 3:
        # Too short for a real arc
        for s in all_scenes:
            s.narrative_arc_phase = "Setup"
        return script
        
    try:
        from scipy.signal import find_peaks
        peaks, _ = find_peaks(tension_sequence, distance=max(1, len(tension_sequence) // 5))
    except ImportError:
        # Fallback 1D peak finding
        peaks = []
        for i in range(1, len(tension_sequence) - 1):
            if tension_sequence[i-1] < tension_sequence[i] > tension_sequence[i+1]:
                peaks.append(i)

    # 3. Label phases
    if len(peaks) == 0:
        climax_idx = np.argmax(tension_sequence)
    else:
        # The true Climax usually resides in the final 30% of the narrative timeline.
        # Weight peaks by magnitude and their proximity to the 80% mark.
        weighted_peaks = [(p, tension_sequence[p] * (1.0 - abs((p/len(tension_sequence)) - 0.8))) for p in peaks]
        climax_idx = max(weighted_peaks, key=lambda x: x[1])[0] if weighted_peaks else np.argmax(tension_sequence)

    # Simple dividing lines based on the global climax point
    inciting_incident_idx = len(tension_sequence) // 8
    
    for i, scene in enumerate(all_scenes):
        if i < inciting_incident_idx:
            scene.narrative_arc_phase = "Setup"
        elif i == inciting_incident_idx:
            scene.narrative_arc_phase = "Inciting Incident"
        elif i < climax_idx:
            scene.narrative_arc_phase = "Rising Action"
        elif i == climax_idx:
            scene.narrative_arc_phase = "Climax"
        elif i < len(all_scenes) - 1:
            scene.narrative_arc_phase = "Falling Action"
        else:
            scene.narrative_arc_phase = "Resolution"
            
    logger.info(f"Arc mapped. Found Climax at Scene {climax_idx + 1}")
    return script
