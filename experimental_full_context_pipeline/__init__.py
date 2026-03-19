"""
Experimental Full-Context Pipeline

A clean-room experimental architecture that sends the entire script
to an LLM in a single pass (no chunking, no RAG, no sliding window).
Produces scene segmentation, emotion vectors, and deterministic lighting.

This module does NOT modify or depend on any existing pipeline code.
"""
