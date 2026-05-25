from functools import lru_cache
from pathlib import Path
import re

from mlx_lm import generate, load
from mlx_lm.sample_utils import make_sampler

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASE_MODEL_DIR = PROJECT_ROOT / "models" / "base" / "mlx-community__Qwen3-4B-4bit"
ADAPTER_DIR = PROJECT_ROOT / "adapters" / "virtual_twin_style"


SYSTEM_MESSAGE = (
    "You are Mohamad's professional virtual assistant. "
    "You do not pretend to be Mohamad. "
    "Answer clearly, concisely, and only make claims supported by available context. "
    "Never include hidden reasoning, chain-of-thought, or <think> tags in the response. "
    "When the user's request is vague or missing important context, ask one concise "
    "follow-up question before answering. Do not guess."
)


def clean_model_output(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = text.replace("<think>", "").replace("</think>", "")
    return text.strip()


@lru_cache(maxsize=1)
def get_llm():
    if not BASE_MODEL_DIR.exists():
        raise FileNotFoundError(f"Base model not found: {BASE_MODEL_DIR}")

    if not ADAPTER_DIR.exists():
        raise FileNotFoundError(f"LoRA adapter not found: {ADAPTER_DIR}")

    model, tokenizer = load(str(BASE_MODEL_DIR), adapter_path=str(ADAPTER_DIR))
    sampler = make_sampler(temp=0.5)
    return model, tokenizer, sampler


def generate_chat_response(messages: list[dict[str, str]], max_tokens: int = 256) -> str:
    model, tokenizer, sampler = get_llm()
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


def generate_router_response(messages: list[dict[str, str]], max_tokens: int = 128) -> str:
    model, tokenizer, sampler = get_llm()
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
