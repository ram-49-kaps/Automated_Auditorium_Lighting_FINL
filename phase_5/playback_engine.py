"""
Playback Engine
Orchestrates the timing and execution of LightingInstructions.
"""

import json
import time
import asyncio
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass

from .scene_renderer import SceneRenderer

class PlaybackEngine:
    """
    Engine to play lighting instructions with accurate timing.
    
    IMPORTANT:
    1. Phase 5 assumes all LightingInstruction inputs are schema-valid and does not perform validation.
    2. All transitions in Phase 5 use linear interpolation unless explicitly extended in future versions.
    """
    
    def __init__(self, renderer: SceneRenderer):
        """
        Initialize playback engine
        
        Args:
            renderer: Reference to the SceneRenderer instance
        """
        self.renderer = renderer
        self.instructions: List[Dict] = []
        self.sorted_instructions: List[Dict] = []
        
        self.is_playing = False
        self.is_paused = False
        self.start_time = 0.0
        self.pause_time = 0.0
        self.elapsed_time = 0.0
        self.total_duration = 0.0
        
        # Callbacks
        self.callbacks = []
        
        # Transition State
        # Stores the value of a group at the START of a transition
        # Key: (scene_id, group_id) -> { intensity: float, color: hex }
        self._transition_start_states: Dict[tuple, Dict] = {}

    def load_instructions(self, instructions: List[Dict]):
        """
        Load a list of LightingInstruction objects.
        """
        self.instructions = instructions
        # Sort by start time
        self.sorted_instructions = sorted(
            instructions, 
            key=lambda x: x.get("time_window", {}).get("start", 0)
        )
        
        # Calculate total duration
        if self.sorted_instructions:
            last_end = max(i.get("time_window", {}).get("end", 0) for i in self.sorted_instructions)
            self.total_duration = last_end
        else:
            self.total_duration = 0.0
            
    def play(self):
        """Start or resume playback"""
        if self.is_paused:
            # Resume
            self.start_time = time.time() - self.elapsed_time
            self.is_paused = False
        else:
            # Start
            self.start_time = time.time()
            if not self.is_playing:
                self.elapsed_time = 0
                self.renderer.reset()
                self._transition_start_states.clear()
        
        self.is_playing = True
        self._notify_callbacks("play", self.elapsed_time)

    def pause(self):
        """Pause playback"""
        if self.is_playing and not self.is_paused:
            self.is_paused = True
            self.pause_time = time.time()
            self.elapsed_time = self.pause_time - self.start_time
            self._notify_callbacks("pause", self.elapsed_time)

    def stop(self):
        """Stop and reset"""
        self.is_playing = False
        self.is_paused = False
        self.elapsed_time = 0
        self.renderer.reset()
        self._transition_start_states.clear()
        self._notify_callbacks("stop", 0)
        
    def seek(self, time_seconds: float):
        """Jump to specific time"""
        self.elapsed_time = max(0.0, min(time_seconds, self.total_duration))
        if self.is_playing and not self.is_paused:
            self.start_time = time.time() - self.elapsed_time
        
        # On seek, we clear transitions because we can't easily interpolate from valid history
        self._transition_start_states.clear()
        
        # Force an update to show the frame at this time
        self._apply_state_at_time(self.elapsed_time)
        self._notify_callbacks("seek", self.elapsed_time)

    def update(self) -> Dict:
        """
        Main loop tick. Calculates time and updates renderer.
        Returns status dict.
        """
        if self.is_playing and not self.is_paused:
            current_time = time.time()
            self.elapsed_time = current_time - self.start_time
            
            if self.elapsed_time >= self.total_duration:
                self._notify_callbacks("complete", self.total_duration)
                # Loop or stop? Let's stop.
                self.stop()
                return self.get_status()
                
            self._apply_state_at_time(self.elapsed_time)
            
        return self.get_status()

    def get_status(self) -> Dict:
        return {
            "is_playing": self.is_playing,
            "is_paused": self.is_paused,
            "elapsed_time": self.elapsed_time,
            "total_duration": self.total_duration,
            "progress": (self.elapsed_time / self.total_duration) if self.total_duration > 0 else 0
        }

    def _apply_state_at_time(self, t: float):
        """
        Determine active cues and push state to renderer.
        """
        active_instructions = [
            inst for inst in self.sorted_instructions
            if inst["time_window"]["start"] <= t < inst["time_window"]["end"]
        ]
        
        # Apply instructions
        # Note: If multiple instructions overlap for the same group, the last one in the list wins.
        # Ideally time windows shouldn't overlap for the same group, but we handle it gracefully.
        
        for inst in active_instructions:
            scene_id = inst.get("scene_id", "unknown")
            start = inst["time_window"]["start"]
            
            for group_data in inst.get("groups", []):
                group_id = group_data["group_id"]
                params = group_data["parameters"]
                transition = group_data.get("transition")
                
                target_intensity = params.get("intensity", 0.0)
                target_color_semantic = params.get("color")
                target_focus = params.get("focus_area")
                
                # Check transition
                is_fading = False
                fade_alpha = 1.0
                
                if transition and transition.get("type") in ["fade", "crossfade"]:
                    duration = transition.get("duration", 0)
                    time_into_scene = t - start
                    
                    if time_into_scene < duration and duration > 0:
                        is_fading = True
                        fade_alpha = time_into_scene / duration
                        
                        # Capture start state if not exists
                        # We use scene_id in key to ensure we capture fresh validation for new scenes
                        key = (scene_id, group_id)
                        if key not in self._transition_start_states:
                            current_state = self.renderer.get_state(group_id)
                            # If light wasn't in renderer, assume defaults
                            if current_state:
                                self._transition_start_states[key] = {
                                    "intensity": current_state.intensity,
                                    "color": current_state.color_hex
                                }
                            else:
                                self._transition_start_states[key] = {
                                    "intensity": 0.0,
                                    "color": "#000000"
                                }
                                
                if is_fading:
                    start_vals = self._transition_start_states[(scene_id, group_id)]
                    
                    # Interpolate intensity
                    curr_intensity = start_vals["intensity"] + (target_intensity - start_vals["intensity"]) * fade_alpha
                    
                    # Interpolate color? 
                    # Complex to interpolate hex. For now, snap color at 50% or keep start?
                    # Let's Cut color at start, simple. Or snap at 0.
                    # MVD: Cut color immediately or simple crossfade if we implemented RGB lerp.
                    # Let's just update intensity smoothly and snap color.
                    # Or better: if fade, maybe color changes? 
                    # Let's stick to updating intensity smoothly. Color validation is tricky without RGB helpers in this file.
                    # Just snap color for now.
                    
                    self.renderer.update_group(
                        group_id=group_id,
                        intensity=curr_intensity,
                        color_semantic=target_color_semantic, # Snap color
                        focus_area=target_focus
                    )
                else:
                    # No fade, set directly
                    self.renderer.update_group(
                        group_id=group_id,
                        intensity=target_intensity,
                        color_semantic=target_color_semantic,
                        focus_area=target_focus
                    )

    def register_callback(self, callback: Callable):
        self.callbacks.append(callback)
    
    def _notify_callbacks(self, event: str, data: Any):
        for cb in self.callbacks:
            try:
                cb(event, data)
            except Exception as e:
                print(f"Callback error: {e}")