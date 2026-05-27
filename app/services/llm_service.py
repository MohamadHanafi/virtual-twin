from functools import lru_cache
import os
from pathlib import Path
import re

from mlx_lm import generate, load
from mlx_lm.sample_utils import make_sampler
from dotenv import load_dotenv
from google import genai
from google.genai import types

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

BASE_MODEL_DIR = PROJECT_ROOT / "models" / "base" / "mlx-community__Qwen3-4B-4bit"
ADAPTER_DIR = PROJECT_ROOT / "adapters" / "virtual_twin_style"

LOCAL_PROVIDER = "local"
GEMINI_PROVIDER = "gemini"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


SYSTEM_MESSAGE = (
    "You are Mohamad's professional virtual assistant. "
    "Answer clearly, concisely, professionally, and only make claims supported by available context. "
    "When the user's request is vague or missing important context, ask one concise"
    "follow-up question before answering. Do not guess."
)


def clean_model_output(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = text.replace("<think>", "").replace("</think>", "")
    return text.strip()


def _llm_provider() -> str:
    return os.getenv("LLM_PROVIDER", LOCAL_PROVIDER).strip().lower()


def _gemini_model_name() -> str:
    return os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL


def _split_system_instruction(messages: list[dict[str, str]]) -> tuple[str | None, list[types.Content]]:
    system_parts = []
    contents = []

    for message in messages:
        role = message["role"]
        content = message["content"]

        if role == "system":
            system_parts.append(content)
            continue

        gemini_role = "model" if role == "assistant" else "user"
        contents.append(
            types.Content(
                role=gemini_role,
                parts=[types.Part.from_text(text=content)],
            )
        )

    system_instruction = "\n\n".join(system_parts) if system_parts else None
    return system_instruction, contents


@lru_cache(maxsize=1)
def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")

    return genai.Client(api_key=api_key)


@lru_cache(maxsize=1)
def get_local_llm():
    if not BASE_MODEL_DIR.exists():
        raise FileNotFoundError(f"Base model not found: {BASE_MODEL_DIR}")

    if not ADAPTER_DIR.exists():
        raise FileNotFoundError(f"LoRA adapter not found: {ADAPTER_DIR}")

    model, tokenizer = load(str(BASE_MODEL_DIR), adapter_path=str(ADAPTER_DIR))
    sampler = make_sampler(temp=0.5)
    return model, tokenizer, sampler


def _generate_local_response(messages: list[dict[str, str]], max_tokens: int) -> str:
    model, tokenizer, sampler = get_local_llm()
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    response = generate(
        model,
        tokenizer,
        prompt=prompt,
        sampler=sampler,
        max_tokens=max_tokens,
    )
    return clean_model_output(response)


def _generate_gemini_response(messages: list[dict[str, str]], max_tokens: int) -> str:
    system_instruction, contents = _split_system_instruction(messages)
    response = get_gemini_client().models.generate_content(
        model=_gemini_model_name(),
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.5,
            max_output_tokens=max_tokens,
        ),
    )
    print (response)
    return clean_model_output(response.text or "")


def generate_chat_response(messages: list[dict[str, str]], max_tokens: int = 256) -> str:
    if _llm_provider() == GEMINI_PROVIDER:
        return _generate_gemini_response(messages, max_tokens=max_tokens)

    return _generate_local_response(messages, max_tokens=max_tokens)


def generate_router_response(messages: list[dict[str, str]], max_tokens: int = 128) -> str:
    if _llm_provider() == GEMINI_PROVIDER:
        return _generate_gemini_response(messages, max_tokens=max_tokens)

    return _generate_local_response(messages, max_tokens=max_tokens)
