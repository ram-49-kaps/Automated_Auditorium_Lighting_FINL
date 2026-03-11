"""
Shared Ollama Client — Local LLM Interface

Provides a reusable wrapper for Ollama phi3:mini (or any local model).
All phases use this single client for LLM inference.

Key features:
  - Connection health check on first call
  - Circuit breaker: disables after 3 consecutive failures
  - Timeout + 1 automatic retry on transient errors
  - JSON-mode generation with auto-parse + validation
  - Graceful fallback: returns None on any failure (callers handle)
"""

import json
import logging
import requests
import asyncio
import aiohttp
import os
from typing import Optional, Dict, Any, List

logger = logging.getLogger("ollama_client")

# Attempt dynamic hook into new OpenAI Client
try:
    from utils.openai_client import (
        openai_json as _openai_json,
        async_openai_json as _async_openai_json,
        openai_json_array as _openai_json_array
    )
    _has_openai = bool(os.environ.get("OPENAI_API_KEY"))
except ImportError:
    _has_openai = False

# ---------------------------------------------------------------------------
# Lazy config import (avoids circular imports)
# ---------------------------------------------------------------------------
def _get_config():
    """Load Ollama config values."""
    try:
        from config import (
            OLLAMA_BASE_URL,
            OLLAMA_MODEL,
            OLLAMA_TIMEOUT,
            OLLAMA_TEMPERATURE,
            OLLAMA_ENABLED,
        )
        return {
            "base_url": OLLAMA_BASE_URL,
            "model": OLLAMA_MODEL,
            "timeout": OLLAMA_TIMEOUT,
            "temperature": OLLAMA_TEMPERATURE,
            "enabled": OLLAMA_ENABLED,
        }
    except ImportError:
        logger.warning("Ollama config not found in config.py — using defaults")
        return {
            "base_url": "http://localhost:11434",
            "model": "phi3:mini",
            "timeout": 30,
            "temperature": 0.1,
            "enabled": True,
        }


# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------
_ollama_available: Optional[bool] = None   # None = not checked yet
_consecutive_failures: int = 0
_CIRCUIT_BREAKER_THRESHOLD = 3


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
def _check_ollama_health() -> bool:
    """
    Ping Ollama server to verify it's running.
    Called once on first use. Sets _ollama_available flag.
    """
    global _ollama_available
    cfg = _get_config()

    if not cfg["enabled"]:
        logger.info("Ollama is disabled via config (OLLAMA_ENABLED=False)")
        _ollama_available = False
        return False

    try:
        resp = requests.get(
            f"{cfg['base_url']}/api/tags",
            timeout=5,
        )
        if resp.status_code == 200:
            models = [m.get("name", "") for m in resp.json().get("models", [])]
            logger.info(f"✅ Ollama is running. Available models: {models}")
            _ollama_available = True
            return True
        else:
            logger.warning(f"Ollama health check returned status {resp.status_code}")
            _ollama_available = False
            return False
    except requests.ConnectionError:
        logger.warning(
            f"⚠️ Ollama is not reachable at {cfg['base_url']}. "
            "All phases will use fallback logic."
        )
        _ollama_available = False
        return False
    except Exception as e:
        logger.warning(f"⚠️ Ollama health check failed: {e}")
        _ollama_available = False
        return False


def is_ollama_available() -> bool:
    """Check if Ollama (or substituted OpenAI key) is available (lazy health check on first call)."""
    global _ollama_available
    if _has_openai:
        return True
    
    if _ollama_available is None:
        _check_ollama_health()
    return bool(_ollama_available)


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------
def _record_failure():
    """Record a failure. Trips circuit breaker after threshold."""
    global _consecutive_failures, _ollama_available
    _consecutive_failures += 1
    if _consecutive_failures >= _CIRCUIT_BREAKER_THRESHOLD:
        logger.error(
            f"🔴 Circuit breaker tripped: {_consecutive_failures} consecutive Ollama failures. "
            "Disabling Ollama for the rest of this run."
        )
        _ollama_available = False


def _record_success():
    """Reset failure counter on success."""
    global _consecutive_failures
    _consecutive_failures = 0


# ---------------------------------------------------------------------------
# Core generation function
# ---------------------------------------------------------------------------
def ollama_generate(
    prompt: str,
    system_prompt: str = "",
    temperature: Optional[float] = None,
    max_tokens: int = 2048,
    timeout: Optional[int] = None,
    is_json: bool = False,
) -> Optional[str]:
    """
    Generate text using Ollama.

    Args:
        prompt: User prompt text.
        system_prompt: Optional system instruction.
        temperature: Override config temperature.
        max_tokens: Maximum tokens in response.
        timeout: Override global request timeout.
        is_json: If True, forces Ollama into strict JSON mode.

    Returns:
        Generated text string, or None on failure.
    """
    if not is_ollama_available():
        return None

    cfg = _get_config()
    temp = temperature if temperature is not None else cfg["temperature"]

    payload = {
        "model": cfg["model"],
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temp,
            "num_predict": max_tokens,
        },
    }
    if is_json:
        payload["format"] = "json"
    if system_prompt:
        payload["system"] = system_prompt

    # Try with 1 retry
    for attempt in range(2):
        try:
            req_timeout = timeout if timeout is not None else cfg["timeout"]
            resp = requests.post(
                f"{cfg['base_url']}/api/generate",
                json=payload,
                timeout=req_timeout,
            )

            if resp.status_code == 200:
                result = resp.json().get("response", "").strip()
                if result:
                    _record_success()
                    return result
                else:
                    logger.warning("Ollama returned empty response")
                    _record_failure()
                    return None
            else:
                logger.warning(
                    f"Ollama returned status {resp.status_code} (attempt {attempt + 1}/2)"
                )
                if attempt == 0:
                    continue  # retry
                _record_failure()
                return None

        except requests.Timeout:
            logger.warning(
                f"Ollama request timed out after {req_timeout}s (attempt {attempt + 1}/2)"
            )
            if attempt == 0:
                continue
            _record_failure()
            return None

        except requests.ConnectionError:
            logger.warning("Ollama connection lost")
            _record_failure()
            return None

        except Exception as e:
            logger.warning(f"Ollama request failed: {e} (attempt {attempt + 1}/2)")
            if attempt == 0:
                continue
            _record_failure()
            return None

    return None


# ---------------------------------------------------------------------------
# JSON generation with validation
# ---------------------------------------------------------------------------
def ollama_json(
    prompt: str,
    system_prompt: str = "",
    expected_keys: Optional[List[str]] = None,
    temperature: Optional[float] = None,
    timeout: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Generate JSON output from Ollama and auto-parse it.

    Args:
        prompt: User prompt (should ask for JSON output).
        system_prompt: System instruction.
        expected_keys: If provided, validate the parsed dict contains these keys.
        temperature: Override config temperature.

    Returns:
        Parsed JSON dict, or None on failure/invalid output.
    """
    if not is_ollama_available():
        return None

    # Enhance prompt to request JSON
    json_system = system_prompt
    if json_system:
        json_system += "\n\nIMPORTANT: You MUST respond with ONLY valid JSON. No markdown, no explanation, no extra text."
    else:
        json_system = "You MUST respond with ONLY valid JSON. No markdown, no explanation, no extra text."

    raw = ollama_generate(prompt, system_prompt=json_system, temperature=temperature, timeout=timeout, is_json=True)
    if raw is None:
        return None

    # Parse JSON — handle markdown code blocks
    text = raw.strip()

    # Strip markdown code fences if present
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object or array in the response
        import re
        obj_match = re.search(r'\{.*\}', text, re.DOTALL)
        arr_match = re.search(r'\[.*\]', text, re.DOTALL)

        match = obj_match or arr_match
        if match:
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                logger.warning(f"Ollama JSON parse failed even after extraction. Raw: {text[:200]}")
                _record_failure()
                return None
        else:
            logger.warning(f"Ollama did not return valid JSON. Raw: {text[:200]}")
            _record_failure()
            return None

    # Validate expected keys
    if expected_keys and isinstance(parsed, dict):
        missing = [k for k in expected_keys if k not in parsed]
        if missing:
            logger.warning(f"Ollama JSON missing expected keys: {missing}")
            _record_failure()
            return None

    _record_success()
    return parsed


# ---------------------------------------------------------------------------
# Convenience: JSON array generation
# ---------------------------------------------------------------------------
def ollama_json_array(
    prompt: str,
    system_prompt: str = "",
    temperature: Optional[float] = None,
    timeout: Optional[int] = None,
) -> Optional[List[Dict]]:
    """
    Generate a JSON array from Ollama.

    Returns:
        Parsed list of dicts, or None on failure.
    """
    result = ollama_json(prompt, system_prompt=system_prompt, temperature=temperature, timeout=timeout)
    if result is None:
        return None
    if isinstance(result, list):
        return result
    # If it returned a dict with a list inside, try common keys
    for key in ["results", "scenes", "rules", "items", "data"]:
        if key in result and isinstance(result[key], list):
            return result[key]
    logger.warning("Ollama returned JSON dict instead of array")
    return None


# ---------------------------------------------------------------------------
# Reset (for testing)
# ---------------------------------------------------------------------------
def reset_client():
    """Reset client state. Useful for testing."""
    global _ollama_available, _consecutive_failures
    _ollama_available = None
    _consecutive_failures = 0

# ---------------------------------------------------------------------------
# Asynchronous Support (aiohttp)
# ---------------------------------------------------------------------------

async def _async_record_failure():
    """Async wrapper for recording failures."""
    _record_failure()

async def async_ollama_generate(
    prompt: str,
    system_prompt: str = "",
    temperature: Optional[float] = None,
    max_tokens: int = 2048,
    timeout: Optional[int] = None,
    is_json: bool = False,
    session: Optional[aiohttp.ClientSession] = None,
) -> Optional[str]:
    """Non-blocking Ollama generation using aiohttp."""
    if not is_ollama_available():
        return None

    cfg = _get_config()
    temp = temperature if temperature is not None else cfg["temperature"]
    req_timeout = timeout if timeout is not None else cfg["timeout"]

    payload = {
        "model": cfg["model"],
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temp,
            "num_predict": max_tokens,
        },
    }
    if is_json:
        payload["format"] = "json"
    if system_prompt:
        payload["system"] = system_prompt

    client_timeout = aiohttp.ClientTimeout(total=req_timeout)
    
    # helper for the request
    async def make_request(current_session):
        for attempt in range(2):
            try:
                async with current_session.post(
                    f"{cfg['base_url']}/api/generate",
                    json=payload,
                    timeout=client_timeout,
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        result = data.get("response", "").strip()
                        if result:
                            _record_success()
                            return result
                        else:
                            await _async_record_failure()
                            return None
                    else:
                        logger.warning(f"Ollama returned status {resp.status} (attempt {attempt + 1}/2)")
                        if attempt == 0: continue
                        await _async_record_failure()
                        return None
            except asyncio.TimeoutError:
                logger.warning(f"Ollama request timed out after {req_timeout}s (attempt {attempt + 1}/2)")
                if attempt == 0: continue
                await _async_record_failure()
                return None
            except Exception as e:
                logger.warning(f"Ollama async request failed: {e} (attempt {attempt + 1}/2)")
                if attempt == 0: continue
                await _async_record_failure()
                return None
        return None

    if session is None:
        async with aiohttp.ClientSession() as s:
            return await make_request(s)
    else:
        return await make_request(session)


async def async_ollama_json(
    prompt: str,
    system_prompt: str = "",
    expected_keys: Optional[List[str]] = None,
    temperature: Optional[float] = None,
    timeout: Optional[int] = None,
    session: Optional[aiohttp.ClientSession] = None,
) -> Optional[Dict[str, Any]]:
    """Non-blocking JSON generation."""
    if _has_openai:
        cfg = _get_config()
        temp = temperature if temperature is not None else cfg.get("temperature", 0.1)
        return await _async_openai_json(
            prompt=prompt,
            system_prompt=system_prompt,
            expected_keys=expected_keys,
            temperature=temp
        )

    if not is_ollama_available():
        return None

    json_system = system_prompt
    if json_system:
        json_system += "\n\nIMPORTANT: You MUST respond with ONLY valid JSON. No markdown, no explanation, no extra text."
    else:
        json_system = "You MUST respond with ONLY valid JSON. No markdown, no explanation, no extra text."

    raw = await async_ollama_generate(
        prompt, 
        system_prompt=json_system, 
        temperature=temperature, 
        timeout=timeout, 
        is_json=True,
        session=session
    )
    if raw is None:
        return None

    text = raw.strip()
    if text.startswith("```json"): text = text[7:]
    elif text.startswith("```"): text = text[3:]
    if text.endswith("```"): text = text[:-3]
    text = text.strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        import re
        obj_match = re.search(r'\{.*\}', text, re.DOTALL)
        arr_match = re.search(r'\[.*\]', text, re.DOTALL)
        match = obj_match or arr_match
        if match:
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                await _async_record_failure()
                return None
        else:
            await _async_record_failure()
            return None

    if expected_keys and isinstance(parsed, dict):
        missing = [k for k in expected_keys if k not in parsed]
        if missing:
            await _async_record_failure()
            return None

    _record_success()
    return parsed
