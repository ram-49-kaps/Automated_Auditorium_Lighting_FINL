"""
Phase 7 — Human-in-the-Loop Adaptive Learning
================================================
Provides:
  1. FeedbackLogger — logs human feedback entries to JSON
  2. AdaptivePresetManager — tracks corrections, generates versioned presets

DOES NOT modify original EMOTION_PRESETS.
Creates versioned copies (v2, v3) locally.
"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from copy import deepcopy

from .presets_versioned import EMOTION_PRESETS_v1


class FeedbackLogger:
    """
    Logs human feedback entries for lighting cue evaluation.

    Each entry records:
      - scene_id, emotion_distribution, generated_cue
      - human_modified_cue (if modified)
      - human_rating (1-5)
      - confidence_scores
      - timestamp
    """

    def __init__(self, log_dir: Optional[str] = None):
        """
        Initialize the feedback logger.

        Args:
            log_dir: Directory to store feedback log files.
                     Defaults to phase_7/data/feedback/
        """
        if log_dir:
            self._log_dir = Path(log_dir)
        else:
            self._log_dir = Path(__file__).parent / "data" / "feedback"
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._entries: List[Dict[str, Any]] = []

    def log(
        self,
        scene_id: str,
        emotion_distribution: Dict[str, Any],
        generated_cue: Dict[str, Any],
        human_modified_cue: Optional[Dict[str, Any]] = None,
        human_rating: int = 3,
        confidence_scores: Optional[Dict[str, float]] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Log a single human feedback entry.

        Args:
            scene_id: Scene identifier.
            emotion_distribution: Multi-emotion distribution for this scene.
            generated_cue: The system-generated lighting cue.
            human_modified_cue: The human's corrected cue (None if no change).
            human_rating: 1 (terrible) to 5 (perfect).
            confidence_scores: Dict of emotion → confidence score.
            notes: Optional human notes.

        Returns:
            The created feedback entry dict.
        """
        human_rating = max(1, min(5, human_rating))

        entry = {
            "scene_id": scene_id,
            "emotion_distribution": emotion_distribution,
            "generated_cue": generated_cue,
            "human_modified_cue": human_modified_cue,
            "human_rating": human_rating,
            "confidence_scores": confidence_scores or {},
            "timestamp": datetime.now().isoformat(),
            "notes": notes,
        }
        self._entries.append(entry)
        return entry

    def save(self, filename: Optional[str] = None) -> Path:
        """
        Save all feedback entries to a JSON file.

        Args:
            filename: Optional filename. Defaults to timestamped name.

        Returns:
            Path to saved file.
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"feedback_{timestamp}.json"

        filepath = self._log_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self._entries, f, indent=2, default=str)

        return filepath

    def load(self, filepath: str) -> List[Dict[str, Any]]:
        """
        Load feedback entries from a JSON file.

        Args:
            filepath: Path to feedback JSON file.

        Returns:
            List of feedback entry dicts.
        """
        with open(filepath, "r", encoding="utf-8") as f:
            entries = json.load(f)
        self._entries.extend(entries)
        return entries

    @property
    def entries(self) -> List[Dict[str, Any]]:
        """Get all logged entries."""
        return self._entries

    def clear(self) -> None:
        """Clear all logged entries."""
        self._entries = []


class AdaptivePresetManager:
    """
    Manages versioned emotion presets based on human feedback.

    Adaptive logic:
      1. Moving average adjustment of intensity corrections
      2. Generates EMOTION_PRESETS_v2, v3 from feedback
      3. Reduces accent probability if repeatedly removed
      4. Tracks alignment improvement trend

    NEVER modifies EMOTION_PRESETS_v1 (the original baseline).
    """

    def __init__(self, base_presets: Optional[Dict] = None):
        """
        Initialize with base presets.

        Args:
            base_presets: Starting presets. Defaults to EMOTION_PRESETS_v1.
        """
        self._base = base_presets or deepcopy(EMOTION_PRESETS_v1)
        self._v2 = deepcopy(self._base)
        self._corrections: Dict[str, List[float]] = {}  # emotion → [intensity_deltas]
        self._accent_removals: Dict[str, int] = {}  # emotion → removal_count
        self._accent_appearances: Dict[str, int] = {}  # emotion → appearance_count
        self._version = 2

    def process_feedback(self, entries: List[Dict[str, Any]]) -> None:
        """
        Process a batch of feedback entries to adapt presets.

        Args:
            entries: List of HumanFeedbackEntry dicts.
        """
        for entry in entries:
            self._process_single(entry)

        self._apply_corrections()

    def _process_single(self, entry: Dict[str, Any]) -> None:
        """Process a single feedback entry."""
        emotion_dist = entry.get("emotion_distribution", {})
        primary_emotion = emotion_dist.get("primary_emotion")
        if not primary_emotion:
            return

        generated = entry.get("generated_cue", {})
        modified = entry.get("human_modified_cue")

        # Track intensity corrections
        if modified is not None:
            gen_groups = generated.get("groups", [])
            mod_groups = modified.get("groups", [])

            if gen_groups and mod_groups:
                gen_intensity = gen_groups[0].get("parameters", {}).get("intensity", 0.5)
                mod_intensity = mod_groups[0].get("parameters", {}).get("intensity", 0.5)
                delta = mod_intensity - gen_intensity

                if primary_emotion not in self._corrections:
                    self._corrections[primary_emotion] = []
                self._corrections[primary_emotion].append(delta)

        # Track accent removals
        accent_emotion = emotion_dist.get("accent_emotion")
        if accent_emotion is not None:
            if accent_emotion not in self._accent_appearances:
                self._accent_appearances[accent_emotion] = 0
            self._accent_appearances[accent_emotion] += 1

            # If human removed accent (modified cue doesn't reflect it)
            if modified is not None:
                mod_metadata = modified.get("metadata", {})
                if mod_metadata.get("accent_emotion") is None:
                    if accent_emotion not in self._accent_removals:
                        self._accent_removals[accent_emotion] = 0
                    self._accent_removals[accent_emotion] += 1

    def _apply_corrections(self) -> None:
        """Apply moving average corrections to v2 presets."""
        for emotion, deltas in self._corrections.items():
            if not deltas or emotion not in self._v2:
                continue

            # Moving average (use last 10 corrections max)
            recent = deltas[-10:]
            avg_delta = sum(recent) / len(recent)

            # Apply correction (clamp to valid range)
            current = self._v2[emotion].get("intensity", 0.5)
            new_intensity = max(0.05, min(0.95, current + avg_delta))
            self._v2[emotion]["intensity"] = round(new_intensity, 3)

    def get_preset(self, version: int = 2) -> Dict:
        """
        Get presets for a specific version.

        Args:
            version: 1 = original, 2 = adapted.

        Returns:
            Emotion presets dict.
        """
        if version == 1:
            return deepcopy(self._base)
        else:
            return deepcopy(self._v2)

    def get_accent_probability(self, emotion: str) -> float:
        """
        Get the probability that an accent emotion should be kept.

        Decreases if humans frequently remove this accent.

        Args:
            emotion: Accent emotion label.

        Returns:
            Probability (0.0 to 1.0).
        """
        appearances = self._accent_appearances.get(emotion, 0)
        removals = self._accent_removals.get(emotion, 0)

        if appearances == 0:
            return 1.0  # No data → keep accent

        removal_rate = removals / appearances
        return max(0.0, 1.0 - removal_rate)

    def save_presets(self, output_dir: str) -> Path:
        """
        Save current adapted presets to file.

        Args:
            output_dir: Directory to save to.

        Returns:
            Path to saved file.
        """
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        data = {
            "version": self._version,
            "base_version": 1,
            "timestamp": datetime.now().isoformat(),
            "presets": self._v2,
            "corrections_applied": {
                k: round(sum(v[-10:]) / len(v[-10:]), 4) if v else 0
                for k, v in self._corrections.items()
            },
            "accent_probabilities": {
                emotion: self.get_accent_probability(emotion)
                for emotion in self._accent_appearances
            },
        }

        filepath = out / f"EMOTION_PRESETS_v{self._version}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return filepath
