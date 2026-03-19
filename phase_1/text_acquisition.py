"""
Phase 1A — Text Acquisition (With OCR Governance)

Flow:
  File → Direct Extract Attempt
         → If success → continue
         → Else → Mistral OCR
               → If confidence ≥ threshold AND quality checks pass → continue
               → Else → HARD STOP (User prompt)

No silent corruption.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional
from statistics import mean

from config import (
    OCR_CONFIDENCE_THRESHOLD,
    OCR_PROVIDER,
    OCR_AVG_LINE_LENGTH_MIN,
    OCR_AVG_LINE_LENGTH_MAX,
    OCR_NOISE_RATIO_MAX,
)

logger = logging.getLogger("phase_1.acquisition")


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------
@dataclass
class AcquisitionResult:
    """Output of Phase 1A — acquired text with provenance metadata."""
    text: str
    source_method: str            # "direct" or "ocr"
    confidence: float             # 1.0 for direct, OCR-reported for OCR
    ocr_used: bool
    file_extension: str
    quality_checks_passed: bool = True
    quality_issues: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class AcquisitionHardStop(Exception):
    """Raised when text acquisition cannot proceed safely."""
    pass


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def acquire_text(filepath: str) -> AcquisitionResult:
    """
    Acquire text from a script file.

    1. Detect file type
    2. Attempt direct extraction
    3. If direct extraction fails or returns empty → OCR fallback
    4. Validate quality
    5. Return AcquisitionResult or raise AcquisitionHardStop

    Args:
        filepath: Absolute or relative path to the script file.

    Returns:
        AcquisitionResult with text and metadata.

    Raises:
        FileNotFoundError: If file does not exist.
        AcquisitionHardStop: If no extraction method produces acceptable text.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Script file not found: {filepath}")

    _, ext = os.path.splitext(filepath)
    ext = ext.lower()

    logger.info(f"Phase 1A: Acquiring text from {os.path.basename(filepath)} ({ext})")

    # ------------------------------------------------------------------
    # Step 1 — Direct extraction
    # ------------------------------------------------------------------
    direct_text = _try_direct_extraction(filepath, ext)

    if direct_text and direct_text.strip():
        # For PDFs, check if direct extraction is truly sufficient.
        # Image-heavy PDFs (posters, designed docs) can return a thin
        # text layer that is technically non-empty but missing most content.
        if ext == ".pdf" and not _pdf_extraction_is_sufficient(direct_text, filepath):
            logger.warning(
                "Phase 1A: PDF direct extraction looks insufficient — "
                "falling through to OCR"
            )
        else:
            logger.info(
                f"Phase 1A: Direct extraction succeeded "
                f"({len(direct_text)} chars, {len(direct_text.splitlines())} lines)"
            )
            result = AcquisitionResult(
                text=direct_text,
                source_method="direct",
                confidence=1.0,
                ocr_used=False,
                file_extension=ext,
            )
            # Run quality checks even on direct extraction
            _validate_quality(result)
            return result

    # ------------------------------------------------------------------
    # Step 2 — OCR fallback (only for PDF / image-based files)
    # ------------------------------------------------------------------
    if ext in (".pdf",):
        logger.warning("Phase 1A: Direct extraction failed or empty — attempting OCR")
        return _try_ocr_fallback(filepath, ext)

    # ------------------------------------------------------------------
    # Step 3 — Hard stop for formats that should have direct text
    # ------------------------------------------------------------------
    raise AcquisitionHardStop(
        f"Direct text extraction returned empty for {ext} file. "
        f"This format does not support OCR fallback. "
        f"Please provide a valid {ext} file with readable text."
    )


# ---------------------------------------------------------------------------
# Direct extraction  (reuses utils/file_io.py readers)
# ---------------------------------------------------------------------------
def _try_direct_extraction(filepath: str, ext: str) -> Optional[str]:
    """Attempt direct text extraction using existing file readers."""
    try:
        from utils.file_io import read_script
        return read_script(filepath)
    except Exception as e:
        logger.warning(f"Phase 1A: Direct extraction error: {e}")
        return None


# ---------------------------------------------------------------------------
# PDF-specific quality gate for direct extraction
# ---------------------------------------------------------------------------
def _pdf_extraction_is_sufficient(text: str, filepath: str) -> bool:
    """
    Multi-signal quality gate for PDF direct extraction.

    Image-heavy PDFs (posters, designed agendas) often have a thin embedded
    text layer that is technically non-empty but missing most of the real
    content. This function checks 3 independent signals:

      1. Content-to-filesize ratio — is the text proportional to the PDF size?
      2. Structural coherence — does the text have sentence-like structure?
      3. Text density — absolute minimum word/line count

    Returns True if the extraction looks sufficient, False if OCR should run.
    """
    words = text.split()
    word_count = len(words)
    lines = [l for l in text.splitlines() if l.strip()]
    line_count = len(lines)

    # ------------------------------------------------------------------
    # Signal 1: Text density (absolute minimums)
    # ------------------------------------------------------------------
    if word_count < 20:
        logger.debug(
            f"PDF quality gate: FAIL — only {word_count} words (min 20)"
        )
        return False

    if line_count < 3:
        logger.debug(
            f"PDF quality gate: FAIL — only {line_count} lines (min 3)"
        )
        return False

    # ------------------------------------------------------------------
    # Signal 2: Content-to-filesize ratio
    # ------------------------------------------------------------------
    # A text-heavy PDF typically yields ~5-20% of its filesize as chars.
    # An image-heavy poster yields < 1%.
    try:
        file_size = os.path.getsize(filepath)
        if file_size > 0:
            text_ratio = len(text) / file_size
            if text_ratio < 0.01:
                logger.debug(
                    f"PDF quality gate: FAIL — text/filesize ratio "
                    f"{text_ratio:.4f} (< 0.01). "
                    f"File is {file_size} bytes but only {len(text)} chars extracted."
                )
                return False
    except OSError:
        pass  # Can't stat file — skip this signal

    # ------------------------------------------------------------------
    # Signal 3: Structural coherence
    # ------------------------------------------------------------------
    # Real text has multi-word lines (sentences, dialogue, descriptions).
    # Garbled extraction produces many single-word or very short lines.
    if line_count > 0:
        avg_words_per_line = word_count / line_count
        if avg_words_per_line < 3.0:
            logger.debug(
                f"PDF quality gate: FAIL — avg {avg_words_per_line:.1f} "
                f"words/line (min 3.0). Text looks fragmented."
            )
            return False

    logger.debug(
        f"PDF quality gate: PASS — {word_count} words, {line_count} lines, "
        f"coherence OK"
    )
    return True


# ---------------------------------------------------------------------------
# OCR fallback via Mistral + PyMuPDF
# ---------------------------------------------------------------------------
def _try_ocr_fallback(filepath: str, ext: str) -> AcquisitionResult:
    """
    Extract text from a PDF using OCR.

    Strategy (in order):
      1. Mistral OCR (via mistralai SDK) — best quality for image-heavy PDFs
      2. PyMuPDF native text extraction — fallback if Mistral fails
      3. AcquisitionHardStop — if everything fails

    Raises AcquisitionHardStop if:
      - All extraction methods fail
      - OCR confidence is below threshold
      - Quality checks fail
    """
    ocr_text = None
    confidence = 0.0
    method_used = None

    # --- Try Mistral OCR first ---
    try:
        ocr_text, confidence = _run_mistral_ocr(filepath)
        method_used = "mistral_ocr"
    except Exception as e:
        logger.warning(f"Phase 1A: Mistral OCR failed ({e}) — trying PyMuPDF")

    # --- Fallback: PyMuPDF native text extraction ---
    if not ocr_text or not ocr_text.strip():
        try:
            ocr_text, confidence = _run_pymupdf_text(filepath)
            method_used = "pymupdf"
        except Exception as e2:
            raise AcquisitionHardStop(
                f"All OCR methods failed. Mistral OCR and PyMuPDF text "
                f"extraction both returned no usable text. "
                f"Check MISTRAL_API_KEY in .env and network connectivity."
            )

    # -- Confidence gate --
    if confidence < OCR_CONFIDENCE_THRESHOLD:
        raise AcquisitionHardStop(
            f"OCR confidence ({confidence:.2f}) is below threshold "
            f"({OCR_CONFIDENCE_THRESHOLD}). Cannot proceed safely. "
            f"Please provide a cleaner version of the file or manually "
            f"convert the PDF to text."
        )

    result = AcquisitionResult(
        text=ocr_text,
        source_method="ocr",
        confidence=confidence,
        ocr_used=True,
        file_extension=ext,
    )

    # -- Structural quality gate --
    _validate_quality(result)

    if not result.quality_checks_passed:
        raise AcquisitionHardStop(
            f"OCR text passed confidence threshold ({confidence:.2f}) but "
            f"failed structural quality checks: {result.quality_issues}. "
            f"The text may have merged lines, missing line breaks, or "
            f"excessive noise. Please review the source file."
        )

    logger.info(
        f"Phase 1A: OCR extraction succeeded via {method_used} "
        f"(confidence={confidence:.2f}, {len(ocr_text)} chars)"
    )
    return result


def _run_mistral_ocr(filepath: str) -> tuple:
    """
    Call Mistral OCR API (via mistralai SDK).

    Returns:
        (extracted_text, confidence_score) tuple.
    """
    import os as _os
    from dotenv import load_dotenv
    load_dotenv()

    api_key = _os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError(
            "MISTRAL_API_KEY not found in environment. "
            "Add it to .env file."
        )

    from mistralai import Mistral

    client = Mistral(api_key=api_key)

    # Upload file and run OCR
    with open(filepath, "rb") as f:
        uploaded = client.files.upload(
            file={
                "file_name": os.path.basename(filepath),
                "content": f,
            },
            purpose="ocr",
        )

    signed_url = client.files.get_signed_url(file_id=uploaded.id)

    ocr_response = client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "document_url",
            "document_url": signed_url.url,
        },
    )

    # Extract text from all pages
    pages_text = []

    for page in ocr_response.pages:
        if page.markdown:
            pages_text.append(page.markdown)

    full_text = "\n\n".join(pages_text)

    # Estimate confidence from text quality indicators
    confidence = _estimate_ocr_confidence(full_text)

    return full_text, confidence


def _run_pymupdf_text(filepath: str) -> tuple:
    """
    Fallback: use PyMuPDF's built-in text extraction.

    Better than PyPDF2 for many PDFs. Handles embedded text layers
    that basic readers might miss.

    Returns:
        (extracted_text, confidence_score) tuple.
    """
    import fitz  # PyMuPDF

    doc = fitz.open(filepath)
    pages_text = []

    for page in doc:
        text = page.get_text("text")
        if text and text.strip():
            pages_text.append(text.strip())

    doc.close()

    if not pages_text:
        raise RuntimeError("PyMuPDF extracted no text from PDF")

    full_text = "\n\n".join(pages_text)
    confidence = _estimate_ocr_confidence(full_text)

    return full_text, confidence


def _estimate_ocr_confidence(text: str) -> float:
    """
    Estimate OCR confidence from text quality indicators.

    Heuristic scoring:
      - Ratio of printable characters
      - Average word length reasonableness
      - Presence of structural markers
    """
    if not text or not text.strip():
        return 0.0

    total_chars = len(text)
    printable_chars = sum(1 for c in text if c.isprintable() or c in "\n\r\t")
    printable_ratio = printable_chars / total_chars if total_chars > 0 else 0

    words = text.split()
    if words:
        avg_word_len = mean(len(w) for w in words)
        # Reasonable word length is 3-10 chars
        word_score = 1.0 if 3 <= avg_word_len <= 10 else 0.7
    else:
        word_score = 0.0

    # Combine scores
    confidence = (printable_ratio * 0.6) + (word_score * 0.4)
    return round(min(confidence, 1.0), 3)


# ---------------------------------------------------------------------------
# Quality validation
# ---------------------------------------------------------------------------
def _validate_quality(result: AcquisitionResult) -> None:
    """
    Run structural quality checks on acquired text.
    Mutates result.quality_checks_passed and result.quality_issues.
    """
    text = result.text
    issues = []

    lines = [l for l in text.splitlines() if l.strip()]

    if not lines:
        issues.append("No non-empty lines found")
        result.quality_checks_passed = False
        result.quality_issues = issues
        return

    # Check 1 — Average line length
    avg_line_len = mean(len(l) for l in lines)

    if avg_line_len < OCR_AVG_LINE_LENGTH_MIN:
        issues.append(
            f"Average line length too short ({avg_line_len:.1f} < "
            f"{OCR_AVG_LINE_LENGTH_MIN}) — possible line splitting corruption"
        )

    if avg_line_len > OCR_AVG_LINE_LENGTH_MAX:
        issues.append(
            f"Average line length too long ({avg_line_len:.1f} > "
            f"{OCR_AVG_LINE_LENGTH_MAX}) — possible missing line breaks"
        )

    # Check 2 — Character noise ratio
    non_printable = sum(
        1 for c in text if not c.isprintable() and c not in "\n\r\t"
    )
    noise_ratio = non_printable / len(text) if len(text) > 0 else 0

    if noise_ratio > OCR_NOISE_RATIO_MAX:
        issues.append(
            f"Excessive character noise ({noise_ratio:.3f} > "
            f"{OCR_NOISE_RATIO_MAX}) — possible encoding corruption"
        )

    # Set result
    if issues:
        # For direct extraction, log warnings but don't fail
        if result.source_method == "direct":
            for issue in issues:
                logger.warning(f"Phase 1A quality warning: {issue}")
            result.quality_checks_passed = True  # Don't block direct extraction
        else:
            result.quality_checks_passed = False

    result.quality_issues = issues
