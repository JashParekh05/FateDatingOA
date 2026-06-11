"""Provider-agnostic structured generation: Anthropic (default) or Groq (free).

Both providers take the same inputs (system prompt, user text, optional
base64 JPEG frames) and return a validated pydantic model.
"""

import json
from functools import lru_cache
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from . import config

T = TypeVar("T", bound=BaseModel)


def generate(system: str, prompt: str, schema: type[T],
             images_b64: list[str] | None = None) -> T:
    if config.LLM_PROVIDER == "openai":
        return _generate_openai(system, prompt, schema, images_b64)
    if config.LLM_PROVIDER == "groq":
        return _generate_groq(system, prompt, schema, images_b64)
    if config.LLM_PROVIDER == "anthropic":
        return _generate_anthropic(system, prompt, schema, images_b64)
    raise RuntimeError(
        f"Unknown LLM_PROVIDER {config.LLM_PROVIDER!r} — use 'openai', "
        "'anthropic', or 'groq'"
    )


# --------------------------------------------------------------------------
# OpenAI
# --------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _openai_client():
    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError("OpenAI support needs the openai package: pip install openai") from e
    import os
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set in your environment or .env")
    return OpenAI()


def _generate_openai(system: str, prompt: str, schema: type[T],
                     images_b64: list[str] | None) -> T:
    user_content: list | str
    if images_b64:
        user_content = []
        for i, data in enumerate(images_b64):
            user_content.append({"type": "text", "text": f"Frame {i + 1}:"})
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{data}"},
            })
        user_content.append({"type": "text", "text": prompt})
    else:
        user_content = prompt

    completion = _openai_client().chat.completions.parse(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        max_completion_tokens=4096,
        response_format=schema,
    )
    message = completion.choices[0].message
    if message.parsed is None:
        detail = message.refusal or "no parsed output"
        raise RuntimeError(f"OpenAI structured output failed: {detail}")
    return message.parsed


# --------------------------------------------------------------------------
# Anthropic
# --------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _anthropic_client():
    import anthropic
    try:
        return anthropic.Anthropic()
    except Exception as e:
        raise RuntimeError(
            "Could not create the Anthropic client — is ANTHROPIC_API_KEY set "
            f"in your environment or .env? ({e})"
        ) from e


def _generate_anthropic(system: str, prompt: str, schema: type[T],
                        images_b64: list[str] | None) -> T:
    content = []
    for i, data in enumerate(images_b64 or []):
        content.append({"type": "text", "text": f"Frame {i + 1}:"})
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": data},
        })
    content.append({"type": "text", "text": prompt})

    response = _anthropic_client().messages.parse(
        model=config.ANTHROPIC_MODEL,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": content}],
        output_format=schema,
    )
    if response.parsed_output is None:
        raise RuntimeError("Claude's structured output failed to parse")
    return response.parsed_output


# --------------------------------------------------------------------------
# Groq (OpenAI-compatible; free tier)
# --------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _groq_client():
    try:
        from groq import Groq
    except ImportError as e:
        raise RuntimeError("Groq support needs the groq package: pip install groq") from e
    if not config.GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set — get a free key at console.groq.com"
        )
    return Groq(api_key=config.GROQ_API_KEY)


def _generate_groq(system: str, prompt: str, schema: type[T],
                   images_b64: list[str] | None) -> T:
    # Groq's json_object mode guarantees JSON but not the shape, so we put the
    # schema in the prompt, validate with pydantic, and retry once on mismatch.
    schema_instruction = (
        f"{prompt}\n\nRespond with a single JSON object (no markdown fences) "
        f"matching exactly this JSON schema:\n{json.dumps(schema.model_json_schema())}"
    )

    user_content: list | str
    if images_b64:
        user_content = []
        for i, data in enumerate(images_b64):
            user_content.append({"type": "text", "text": f"Frame {i + 1}:"})
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{data}"},
            })
        user_content.append({"type": "text", "text": schema_instruction})
        model = config.GROQ_VISION_MODEL
    else:
        user_content = schema_instruction
        model = config.GROQ_MODEL

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]

    last_error = None
    for _ in range(2):
        response = _groq_client().chat.completions.create(
            model=model,
            messages=messages,
            max_completion_tokens=4096,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        try:
            return schema.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = e
            messages.append({"role": "assistant", "content": raw})
            messages.append({
                "role": "user",
                "content": f"That JSON didn't match the schema ({e}). "
                           "Respond again with a corrected JSON object only.",
            })
    raise RuntimeError(f"Groq output failed schema validation twice: {last_error}")
