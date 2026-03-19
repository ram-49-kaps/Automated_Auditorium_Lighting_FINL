"""
Phase 1F — Narrative Context Synthesizer

Takes chunk summaries from Phase 1C and produces a single "narrative_context"
string that captures the full emotional arc of the script.

This narrative context is injected into Phase 2 (Emotion Analysis) and
Phase 4 (Lighting Design) to prevent emotional drift and ensure temporal
coherence across the pipeline.

Key properties:
  - Single LLM call per script (not per scene)
  - Focuses on emotional texture, dramatic arc, and mood trajectory
  - Graceful fallback: concatenates summaries if LLM fails
"""

import os
import logging
from typing import List, Optional

from config import (
    PHASE1_LLM_MODEL,
    PHASE1_LLM_TEMPERATURE,
    PHASE1_LLM_MAX_NEW_TOKENS,
)

logger = logging.getLogger("phase_1.narrative")


# ---------------------------------------------------------------------------
# System prompt for narrative synthesis
# ---------------------------------------------------------------------------
NARRATIVE_SYSTEM_PROMPT = """You are a dramaturge and lighting design consultant. 

Your task is to synthesize sequential chunk summaries of a script into a single cohesive NARRATIVE CONTEXT document.

This document will be used by downstream AI systems to:
1. Predict emotions for individual scenes WITH awareness of the full arc
2. Design lighting that flows smoothly across the entire performance

YOUR OUTPUT MUST COVER:
- The overall emotional arc (e.g., "opens with tension, builds to confrontation, resolves in melancholy")
- Key emotional pivot points (where does the mood shift dramatically?)
- Character dynamics that drive emotional changes
- The mood trajectory — a scene-by-scene emotional "map" (e.g., "Scene 1: cautious hope → Scene 2: rising anxiety → Scene 3: explosive anger → Scene 4: quiet aftermath")
- Any recurring motifs, atmosphere, or tonal patterns

CONSTRAINTS:
- Write 200-400 words
- Be specific about emotions (not "the mood changes" but "the mood shifts from restrained grief to sudden fury")
- Focus on information useful for LIGHTING DESIGN (atmosphere, color mood, intensity shifts)
- Do NOT summarize plot details unless they directly drive emotional shifts
- Output ONLY the narrative context text — no headers, no JSON, no formatting markers"""


# ---------------------------------------------------------------------------
# HF Inference API client (reuse Phase 1C's lazy singleton)
# ---------------------------------------------------------------------------
def _get_client():
    """Get or create HuggingFace InferenceClient (lazy, lightweight)."""
    # Reuse Phase 1C's client to avoid duplicate initialization
    from phase_1.llm_scene_segmenter import _get_client as get_segmenter_client
    return get_segmenter_client()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def synthesize_narrative_context(chunk_summaries: List[str]) -> str:
    """
    Synthesize chunk summaries into a single narrative context.

    Args:
        chunk_summaries: List of dramatic summaries from Phase 1C
                         (one per chunk, 2-4 sentences each).

    Returns:
        A 200-400 word narrative context string describing the full
        emotional arc of the script.

    If LLM fails, returns a concatenated fallback.
    """
    if not chunk_summaries:
        logger.warning("Phase 1F: No chunk summaries provided — returning empty context")
        return ""

    # If only one summary, it IS the narrative context (no need for synthesis)
    if len(chunk_summaries) == 1:
        logger.info("Phase 1F: Single chunk — using chunk summary as narrative context")
        return chunk_summaries[0]

    logger.info(
        f"Phase 1F: Synthesizing narrative context from "
        f"{len(chunk_summaries)} chunk summaries"
    )

    # Try LLM synthesis
    try:
        return _synthesize_with_llm(chunk_summaries)
    except Exception as e:
        logger.warning(f"Phase 1F: LLM synthesis failed ({e}) — using fallback")
        return _fallback_concatenation(chunk_summaries)


def _synthesize_with_llm(chunk_summaries: List[str]) -> str:
    """Call LLM to synthesize chunk summaries into narrative context."""
    client = _get_client()

    # Build the user prompt with numbered summaries
    summaries_text = "\n\n".join(
        f"--- CHUNK {i+1} OF {len(chunk_summaries)} ---\n{summary}"
        for i, summary in enumerate(chunk_summaries)
    )

    user_prompt = (
        f"Here are {len(chunk_summaries)} sequential summaries from different "
        f"parts of a script. Synthesize them into a single narrative context "
        f"document (200-400 words) that captures the full emotional arc.\n\n"
        f"{summaries_text}"
    )

    messages = [
        {"role": "system", "content": NARRATIVE_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    response = client.chat_completion(
        messages=messages,
        max_tokens=PHASE1_LLM_MAX_NEW_TOKENS,
        temperature=PHASE1_LLM_TEMPERATURE if PHASE1_LLM_TEMPERATURE > 0 else 0.01,
        top_p=0.95,
    )

    narrative = response.choices[0].message.content.strip()

    # Basic validation — should be non-trivial text
    if len(narrative.split()) < 30:
        logger.warning(
            f"Phase 1F: LLM narrative too short ({len(narrative.split())} words) "
            f"— using fallback"
        )
        return _fallback_concatenation(chunk_summaries)

    logger.info(
        f"Phase 1F: Narrative context synthesized — "
        f"{len(narrative.split())} words"
    )
    return narrative


def _fallback_concatenation(chunk_summaries: List[str]) -> str:
    """Fallback: concatenate summaries with separators."""
    logger.info("Phase 1F: Using fallback concatenation for narrative context")
    parts = []
    for i, summary in enumerate(chunk_summaries):
        parts.append(f"[Part {i+1}] {summary}")
    return "\n\n".join(parts)
