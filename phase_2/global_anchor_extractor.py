import json
import logging
import math
from typing import List, Dict, Any

from utils.openai_client import openai_json, async_openai_json
from models.narrative_state import GlobalMetaAnchor

logger = logging.getLogger("phase_2.global_anchor")

def extract_global_anchor(full_text: str) -> GlobalMetaAnchor:
    """
    V3 Architecture: Map-Reduce Global Meta-Anchor Extraction.
    Extracts the definitive structural baseline prior to processing individual scenes.
    
    1. Map: Split script into chunks, summarize each chunk rapidly.
    2. Reduce: Pass all summaries to LLM to enforce global parameters.
    """
    logger.info("Starting Phase 2A: Global Meta-Anchor Pass (Map-Reduce)")
    
    # 1. Chunk the text (approx 2000 words per chunk for map-reduce)
    words = full_text.split()
    CHUNK_SIZE = 2500
    
    # If the text is short enough to fit in an 8k context window, skip map-reduce
    if len(words) < 5000:
        logger.info(f"Script length {len(words)} is small enough for single-pass analysis.")
        return _reduce_to_anchor([full_text])
        
    num_chunks = math.ceil(len(words) / CHUNK_SIZE)
    chunks = [" ".join(words[i * CHUNK_SIZE:(i + 1) * CHUNK_SIZE]) for i in range(num_chunks)]
    
    logger.info(f"Mapping {num_chunks} chunks...")
    summaries = []
    
    # Map step: generate rapid synopses
    map_prompt_template = """
    Summarize the narrative events, tone, and character dynamics in this section of a script.
    Focus strictly on:
    - What actually happens (action)
    - How it feels (comedic, tragic, tense)
    - The structural realism (is it grounded, or absurd?)
    Keep it under 150 words.
    
    Script Section:
    {chunk}
    """
    
    # Since we can't do purely parallel blocking here easily without async wrapper overhead in a sync function,
    # we'll execute sequentially for stability, or we can use the async client if preferred.
    for i, chunk in enumerate(chunks):
        logger.debug(f"Summarizing chunk {i+1}/{num_chunks}...")
        res = openai_json(
            prompt=map_prompt_template.format(chunk=chunk),
            system_prompt="You are a narrative intelligence summarizer. Always output JSON.",
            expected_keys=["summary"]
        )
        if res and "summary" in res:
            summaries.append(f"Part {i+1}: " + res["summary"])
            
    logger.info("Map phase complete. Proceeding to Reduction.")
    return _reduce_to_anchor(summaries)


def _reduce_to_anchor(synopses: List[str]) -> GlobalMetaAnchor:
    """
    Processes the sequence of narrative summaries or raw text into a definitive Anchor.
    """
    combined_synopsis = "\n\n".join(synopses)
    
    prompt = f"""
    You are a Senior Theatrical and Cinematic NLP Architect.
    Analyze the following narrative outline of an entire script.
    
    Define the Global Thematic Setup, Realism Level, and Meta-Genre of this narrative.
    You must classify the script across several continuous ranges to help an automated lighting 
    system safely light theatrical scenes.
    
    Narrative Outline:
    {combined_synopsis}
    
    Provide the output in valid JSON matching the exact schema requirements:
    - primary_genre (string): e.g., Comedy, Drama, Thriller
    - secondary_genres (list of strings): e.g., ["Action", "Romance"]
    - subgenre (string): e.g., "Dark Comedy Satire"
    - genre_confidence_score (float 0.0-1.0)
    - narrative_seriousness_score (float 0.0-1.0): 0.0 is slapstick triviality, 1.0 is permanent fatality and absolute realism.
    - overall_thematic_identity (string)
    - realism_baseline (string): e.g., "Cartoon Physics", "Grounded Historical", "Hyperbolic Noir"
    - narrative_universe_logic (string): e.g., "Mistakes are fatal" or "Mistakes are funny"
    - intended_audience_experience (string): e.g., "Catharsis through fear", "Joy through absurdity"
    """

    system_prompt = "You are the Global Meta-Anchor extractor for a decision-safe AI lighting engine. Output STRICT JSON."
    
    expected_keys = [
        "primary_genre", "secondary_genres", "subgenre", "genre_confidence_score",
        "narrative_seriousness_score", "overall_thematic_identity", "realism_baseline",
        "narrative_universe_logic", "intended_audience_experience"
    ]
    
    result = openai_json(
        prompt=prompt,
        system_prompt=system_prompt,
        expected_keys=expected_keys,
        model="gpt-4o-mini" # Using fast model for rapid anchoring
    )
    
    if result:
        return GlobalMetaAnchor(**result)
        
    # Safety Fallback if LLM fails
    logger.warning("Global Meta-Anchor extraction failed. Falling back to Sincere Drama.")
    return GlobalMetaAnchor()
