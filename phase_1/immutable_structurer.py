"""
Phase 1B — Immutable Structuring

Applied to acquired text only.
Produces a frozen, auditable coordinate system.

Operations (in order):
  1. UTF-8 normalization (NFC)
  2. Newline normalization (\\r\\n → \\n only, NO blank-line collapsing)
  3. Invisible character cleanup (zero-width, BOM, soft hyphens)
  4. SHA-256 hash generation
  5. 1-based line indexing
  6. Structural metadata extraction

After this step, the text is FROZEN. No downstream module may modify it.
"""

import hashlib
import re
import unicodedata
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Set

logger = logging.getLogger("phase_1.structurer")

# Characters to strip (zero-width and invisible)
INVISIBLE_CHARS = {
    "\u200b",  # Zero-width space
    "\u200c",  # Zero-width non-joiner
    "\u200d",  # Zero-width joiner
    "\u200e",  # Left-to-right mark
    "\u200f",  # Right-to-left mark
    "\u202a",  # Left-to-right embedding
    "\u202b",  # Right-to-left embedding
    "\u202c",  # Pop directional formatting
    "\u202d",  # Left-to-right override
    "\u202e",  # Right-to-left override
    "\u2060",  # Word joiner
    "\u2061",  # Function application
    "\u2062",  # Invisible times
    "\u2063",  # Invisible separator
    "\u2064",  # Invisible plus
    "\ufeff",  # BOM / Zero-width no-break space
    "\u00ad",  # Soft hyphen
    "\ufffe",  # Non-character
    "\uffff",  # Non-character
}


@dataclass
class StructuralMetadata:
    """Structural signals extracted from the text, used for chunking."""
    blank_line_indices: List[int] = field(default_factory=list)
    uppercase_line_indices: List[int] = field(default_factory=list)
    separator_line_indices: List[int] = field(default_factory=list)
    total_non_blank_lines: int = 0


@dataclass
class ImmutableText:
    """Frozen text with auditable coordinate system."""
    lines: Dict[int, str]                     # 1-based indexed
    sha256_hash: str                          # Fingerprint of final text
    total_lines: int
    structural_metadata: StructuralMetadata
    raw_text: str                             # Frozen full text
    source_method: str                        # "direct" or "ocr"


# Regex for separator lines
_SEPARATOR_PATTERN = re.compile(
    r"^("
    r"INT\.|EXT\.|INTERIOR|EXTERIOR"
    r"|ACT\s+[IVX\d]+"
    r"|SCENE\s+[IVX\d]+"
    r"|[-=]{3,}"
    r"|[*]{3,}"
    r").*$",
    re.IGNORECASE,
)


def structure_text(text: str, source_method: str) -> ImmutableText:
    """
    Apply immutable structuring to acquired text.

    Args:
        text: Raw acquired text from Phase 1A.
        source_method: "direct" or "ocr".

    Returns:
        ImmutableText with frozen lines, hash, and structural metadata.
    """
    logger.info("Phase 1B: Starting immutable structuring")

    # Step 1 — UTF-8 NFC normalization
    text = unicodedata.normalize("NFC", text)

    # Step 2 — Newline normalization (platform consistency only)
    # \r\n → \n, bare \r → \n
    # NO blank-line collapsing — all blanks preserved as structural signal
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Step 3 — Invisible character cleanup
    invisible_removed = 0
    cleaned_chars = []
    for ch in text:
        if ch in INVISIBLE_CHARS:
            invisible_removed += 1
        else:
            cleaned_chars.append(ch)
    text = "".join(cleaned_chars)

    if invisible_removed > 0:
        logger.info(f"Phase 1B: Removed {invisible_removed} invisible characters")

    # Step 4 — SHA-256 hash generation (fingerprint of final text)
    sha256_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    logger.info(f"Phase 1B: SHA-256 = {sha256_hash[:16]}...")

    # Step 5 — 1-based line indexing
    raw_lines = text.split("\n")
    lines: Dict[int, str] = {}
    for i, line in enumerate(raw_lines, start=1):
        lines[i] = line

    total_lines = len(lines)

    # Step 6 — Structural metadata extraction
    metadata = _extract_structural_metadata(lines)

    logger.info(
        f"Phase 1B: Structured {total_lines} lines "
        f"({metadata.total_non_blank_lines} non-blank, "
        f"{len(metadata.blank_line_indices)} blank, "
        f"{len(metadata.uppercase_line_indices)} uppercase headers, "
        f"{len(metadata.separator_line_indices)} separators)"
    )

    return ImmutableText(
        lines=lines,
        sha256_hash=sha256_hash,
        total_lines=total_lines,
        structural_metadata=metadata,
        raw_text=text,
        source_method=source_method,
    )


def _extract_structural_metadata(lines: Dict[int, str]) -> StructuralMetadata:
    """
    Extract structural signals from indexed lines.

    Identifies:
      - Blank lines (empty or whitespace-only)
      - Uppercase lines (≥3 non-space characters, all uppercase)
      - Separator lines (INT., EXT., ACT, SCENE, ---, ===)
    """
    blank_indices: List[int] = []
    uppercase_indices: List[int] = []
    separator_indices: List[int] = []
    non_blank_count = 0

    for line_num, content in lines.items():
        stripped = content.strip()

        if not stripped:
            blank_indices.append(line_num)
            continue

        non_blank_count += 1

        # Uppercase check: at least 3 letter chars, all uppercase
        letters = [c for c in stripped if c.isalpha()]
        if len(letters) >= 3 and stripped == stripped.upper():
            uppercase_indices.append(line_num)

        # Separator check
        if _SEPARATOR_PATTERN.match(stripped):
            separator_indices.append(line_num)

    return StructuralMetadata(
        blank_line_indices=blank_indices,
        uppercase_line_indices=uppercase_indices,
        separator_line_indices=separator_indices,
        total_non_blank_lines=non_blank_count,
    )
