"""
Shared OpenAI Client — Cloud LLM Interface

Provides a reusable wrapper for OpenAI models (targeting gpt-4o-mini).
Replaces the Ollama fallback implementation to leverage fast, cheap, API-driven responses.

Key features:
  - Synchronous and asynchronous clients
  - Enforced JSON mode output parsing
  - Environment variable automatic loading
"""

import json
import logging
import os
from typing import Optional, Dict, Any, List

# Try importing the official openai client
try:
    from openai import AsyncOpenAI, OpenAI
except ImportError:
    raise RuntimeError("The 'openai>=1.0.0' Python package is required. Run 'pip install openai'")

logger = logging.getLogger("openai_client")

# ---------------------------------------------------------------------------
# Client Instantiation
# ---------------------------------------------------------------------------
_sync_client: Optional[OpenAI] = None
_async_client: Optional[AsyncOpenAI] = None

def _get_api_key() -> str:
    """Fetch OpenAI API Key from environment or config."""
    from dotenv import load_dotenv
    # Dynamically locate root based on current utils dir
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env_path = os.path.join(project_root, ".env")
    load_dotenv(env_path) # Load from exact .env into python os memory
    
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        try:
            from config import OPENAI_API_KEY as ConfigKey
            if ConfigKey: return ConfigKey
        except ImportError:
            pass
    if not api_key:
        logger.error("No OPENAI_API_KEY found in .env or config.py!")
    return api_key


def get_sync_client() -> OpenAI:
    global _sync_client
    if _sync_client is None:
        _sync_client = OpenAI(api_key=_get_api_key())
    return _sync_client


def get_async_client() -> AsyncOpenAI:
    global _async_client
    if _async_client is None:
        _async_client = AsyncOpenAI(api_key=_get_api_key())
    return _async_client


# ---------------------------------------------------------------------------
# Core Generation Functions
# ---------------------------------------------------------------------------
def openai_json(
    prompt: str,
    system_prompt: str = "",
    expected_keys: Optional[List[str]] = None,
    temperature: float = 0.1,
    model: str = "gpt-4o-mini",
) -> Optional[Dict[str, Any]]:
    """
    Generate JSON output from OpenAI and parse it.
    """
    client = get_sync_client()
    if not json_system_check(system_prompt):
        system_prompt += "\n\nYou must return output in strictly valid JSON format."

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=temperature,
        )
        content = response.choices[0].message.content
        if not content:
            return None
        
        parsed = json.loads(content)
        
        if expected_keys:
            missing = [k for k in expected_keys if k not in parsed]
            if missing:
                logger.warning(f"OpenAI JSON missing keys: {missing}")
                return None
        return parsed
    except Exception as e:
        logger.error(f"OpenAI Generate Error: {e}")
        return None

async def async_openai_json(
    prompt: str,
    system_prompt: str = "",
    expected_keys: Optional[List[str]] = None,
    temperature: float = 0.1,
    model: str = "gpt-4o-mini",
) -> Optional[Dict[str, Any]]:
    """
    Async generate JSON output from OpenAI and parse it.
    """
    aclient = get_async_client()
    if not json_system_check(system_prompt):
        system_prompt += "\n\nYou must return output in strictly valid JSON format."

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        response = await aclient.chat.completions.create(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=temperature,
        )
        content = response.choices[0].message.content
        if not content:
            return None
            
        parsed = json.loads(content)
        
        if expected_keys:
            missing = [k for k in expected_keys if k not in parsed]
            if missing:
                logger.warning(f"OpenAI Async JSON missing keys: {missing}")
                return None
        return parsed
    except Exception as e:
        logger.error(f"OpenAI Async Generate Error: {e}")
        return None

def json_system_check(sys_prompt: str) -> bool:
    return "json" in sys_prompt.lower()

# For json array, wrap request to respond in object containing list
def openai_json_array(
    prompt: str,
    system_prompt: str = "",
    temperature: float = 0.1,
    model: str = "gpt-4o-mini",
) -> Optional[List[Dict]]:
    system_prompt += "\n\nYou must return a JSON object containing a 'results' key with the array as its value."
    result = openai_json(prompt, system_prompt, temperature=temperature, model=model)
    if result and "results" in result:
        return result["results"]
    return None
