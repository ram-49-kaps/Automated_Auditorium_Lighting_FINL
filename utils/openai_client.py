"""
Unified LLM Client — Provider-Agnostic Interface

Uses the OpenAI Python library's `base_url` flexibility to route requests
to different LLM providers (OpenAI, HuggingFace) based on the selected model.

Architecture:
  1. Provider Registry maps model prefixes → (api_key_env_var, base_url)
  2. get_client(model) returns a configured OpenAI client for that provider
  3. llm_json() is the single entry point for all JSON-mode LLM calls
  4. set_active_model() sets the pipeline-wide default model

Usage:
  from utils.openai_client import set_active_model, llm_json

  set_active_model("Qwen/Qwen2.5-7B-Instruct")  # Called once at pipeline start
  result = llm_json(prompt, system_prompt)         # Uses active model
  result = llm_json(prompt, system_prompt, model="gpt-4o-mini")  # Override
"""

import json
import logging
import os
import re
from typing import Optional, Dict, Any, List

try:
    from openai import AsyncOpenAI, OpenAI
except ImportError:
    raise RuntimeError("The 'openai>=1.0.0' Python package is required. Run 'pip install openai'")

logger = logging.getLogger("llm_client")

# ---------------------------------------------------------------------------
# Provider Registry
# ---------------------------------------------------------------------------
# Maps model prefix → (env_var_for_api_key, base_url)
# The OpenAI library is flexible: by changing base_url, we route to any
# OpenAI-compatible API (HuggingFace, Groq, Anthropic, etc.)

PROVIDER_REGISTRY = {
    "gpt-": {
        "name": "openai",
        "api_key_env": "OPENAI_API_KEY",
        "base_url": None,  # Default OpenAI endpoint
        "supports_json_mode": True,
    },
    "Qwen/": {
        "name": "huggingface",
        "api_key_env": "HF_API_TOKEN",
        "base_url": "https://router.huggingface.co/v1/",
        "supports_json_mode": False,
    },
    "meta-llama/": {
        "name": "huggingface",
        "api_key_env": "HF_API_TOKEN",
        "base_url": "https://router.huggingface.co/v1/",
        "supports_json_mode": False,
    },
}

# ---------------------------------------------------------------------------
# Active Model (set once at pipeline start, used as default for all calls)
# ---------------------------------------------------------------------------
_active_model: Optional[str] = None


def set_active_model(model_id: str):
    """Set the pipeline-wide active model. Called once when pipeline starts."""
    global _active_model
    _active_model = model_id
    provider = _resolve_provider(model_id)
    logger.info(
        f"LLM Client configured: model={model_id}, "
        f"provider={provider['name']}"
    )


def get_active_model() -> Optional[str]:
    """Get the currently active model."""
    return _active_model


# ---------------------------------------------------------------------------
# Provider Resolution
# ---------------------------------------------------------------------------
def _resolve_provider(model: str) -> Dict[str, Any]:
    """Resolve which provider config to use based on model name prefix."""
    for prefix, config in PROVIDER_REGISTRY.items():
        if model.startswith(prefix):
            return config

    # Default fallback: treat as HuggingFace
    logger.warning(f"Unknown model prefix for '{model}', defaulting to HuggingFace")
    return PROVIDER_REGISTRY["Qwen/"]


def _load_api_key(env_var: str) -> str:
    """Load API key from environment, with .env fallback."""
    from dotenv import load_dotenv

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env_path = os.path.join(project_root, ".env")
    load_dotenv(env_path)

    api_key = os.environ.get(env_var, "")
    if not api_key:
        logger.error(f"No {env_var} found in environment or .env file!")
    return api_key


# ---------------------------------------------------------------------------
# Client Factory
# ---------------------------------------------------------------------------
_client_cache: Dict[str, OpenAI] = {}
_async_client_cache: Dict[str, AsyncOpenAI] = {}


def get_client(model: Optional[str] = None) -> OpenAI:
    """
    Get a configured OpenAI client for the given model's provider.
    Uses cached clients to avoid re-creating them.
    """
    model = model or _active_model or "gpt-4o-mini"
    provider = _resolve_provider(model)
    cache_key = provider["name"]

    if cache_key not in _client_cache:
        api_key = _load_api_key(provider["api_key_env"])
        kwargs = {"api_key": api_key}
        if provider["base_url"]:
            kwargs["base_url"] = provider["base_url"]
        _client_cache[cache_key] = OpenAI(**kwargs)
        logger.info(f"Created sync client for provider: {provider['name']}")

    return _client_cache[cache_key]


def get_async_client(model: Optional[str] = None) -> AsyncOpenAI:
    """
    Get a configured AsyncOpenAI client for the given model's provider.
    """
    model = model or _active_model or "gpt-4o-mini"
    provider = _resolve_provider(model)
    cache_key = provider["name"]

    if cache_key not in _async_client_cache:
        api_key = _load_api_key(provider["api_key_env"])
        kwargs = {"api_key": api_key}
        if provider["base_url"]:
            kwargs["base_url"] = provider["base_url"]
        _async_client_cache[cache_key] = AsyncOpenAI(**kwargs)
        logger.info(f"Created async client for provider: {provider['name']}")

    return _async_client_cache[cache_key]


# ---------------------------------------------------------------------------
# Core: JSON Generation
# ---------------------------------------------------------------------------
def llm_json(
    prompt: str,
    system_prompt: str = "",
    expected_keys: Optional[List[str]] = None,
    temperature: float = 0.1,
    model: Optional[str] = None,
    max_tokens: int = 2048,
) -> Optional[Dict[str, Any]]:
    """
    Generate structured JSON from any supported LLM provider.

    Uses the active model if no model is specified.
    Automatically handles provider differences:
      - OpenAI: uses response_format={"type": "json_object"}
      - HuggingFace: parses JSON from free-text response
    """
    model = model or _active_model or "gpt-4o-mini"
    provider = _resolve_provider(model)
    client = get_client(model)

    # Ensure system prompt asks for JSON
    if not _mentions_json(system_prompt):
        system_prompt += "\n\nYou must return output in strictly valid JSON format."

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        # Build request kwargs
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": max(temperature, 0.01),  # Avoid exact 0 for some providers
            "max_tokens": max_tokens,
        }

        # Only use json_object mode for providers that support it
        if provider["supports_json_mode"]:
            kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content

        if not content:
            return None

        # Parse JSON (may need extraction for non-json-mode providers)
        parsed = _extract_json(content.strip())

        if parsed is None:
            logger.warning(f"Could not parse JSON from LLM response (model={model})")
            return None

        if expected_keys:
            missing = [k for k in expected_keys if k not in parsed]
            if missing:
                logger.warning(f"LLM JSON missing keys: {missing} (model={model})")
                return None

        return parsed

    except Exception as e:
        logger.error(f"LLM call failed (model={model}, provider={provider['name']}): {e}")
        return None


async def async_llm_json(
    prompt: str,
    system_prompt: str = "",
    expected_keys: Optional[List[str]] = None,
    temperature: float = 0.1,
    model: Optional[str] = None,
    max_tokens: int = 2048,
) -> Optional[Dict[str, Any]]:
    """
    Async version of llm_json().
    """
    model = model or _active_model or "gpt-4o-mini"
    provider = _resolve_provider(model)
    aclient = get_async_client(model)

    if not _mentions_json(system_prompt):
        system_prompt += "\n\nYou must return output in strictly valid JSON format."

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": max(temperature, 0.01),
            "max_tokens": max_tokens,
        }

        if provider["supports_json_mode"]:
            kwargs["response_format"] = {"type": "json_object"}

        response = await aclient.chat.completions.create(**kwargs)
        content = response.choices[0].message.content

        if not content:
            return None

        parsed = _extract_json(content.strip())

        if parsed is None:
            logger.warning(f"Could not parse async JSON from LLM (model={model})")
            return None

        if expected_keys:
            missing = [k for k in expected_keys if k not in parsed]
            if missing:
                logger.warning(f"Async LLM JSON missing keys: {missing}")
                return None

        return parsed

    except Exception as e:
        logger.error(f"Async LLM call failed (model={model}, provider={provider['name']}): {e}")
        return None


def llm_json_array(
    prompt: str,
    system_prompt: str = "",
    temperature: float = 0.1,
    model: Optional[str] = None,
) -> Optional[List[Dict]]:
    """Generate a JSON array from the LLM."""
    system_prompt += "\n\nYou must return a JSON object containing a 'results' key with the array as its value."
    result = llm_json(prompt, system_prompt, temperature=temperature, model=model)
    if result and "results" in result:
        return result["results"]
    return None


def llm_chat(
    prompt: str,
    system_prompt: str = "",
    temperature: float = 0.1,
    model: Optional[str] = None,
    max_tokens: int = 2048,
) -> Optional[str]:
    """
    Raw text (non-JSON) LLM call. Returns the response as a plain string.
    Useful for phase_1 scene segmentation where the caller does its own parsing.
    """
    model = model or _active_model or "gpt-4o-mini"
    provider = _resolve_provider(model)
    client = get_client(model)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=max(temperature, 0.01),
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"LLM chat call failed (model={model}, provider={provider['name']}): {e}")
        return None


# ---------------------------------------------------------------------------
# JSON Extraction Helpers
# ---------------------------------------------------------------------------
def _extract_json(text: str) -> Optional[Dict]:
    """
    Extract JSON from LLM response text.

    Handles:
      - Clean JSON
      - JSON inside markdown code fences (```json ... ```)
      - Leading/trailing text around the JSON object
    """
    # 1. Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Try stripping markdown code fences
    fenced = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass

    # 3. Try finding the outermost { ... }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(text[first_brace : last_brace + 1])
        except json.JSONDecodeError:
            pass

    return None


def _mentions_json(sys_prompt: str) -> bool:
    """Check if the system prompt already mentions JSON."""
    return "json" in sys_prompt.lower()


# ---------------------------------------------------------------------------
# Backward Compatibility Aliases
# ---------------------------------------------------------------------------
# These allow existing code to work during migration
openai_json = llm_json
async_openai_json = async_llm_json
openai_json_array = llm_json_array

# Legacy client getters (for code that imports these directly)
def get_sync_client(model: str = "gpt-4o-mini") -> OpenAI:
    return get_client(model)
