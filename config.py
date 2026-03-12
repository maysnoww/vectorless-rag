import json
import os


def _get_required(name):
    value = os.getenv(name)
    if value:
        return value
    raise RuntimeError(
        f"Missing required environment variable: {name}. "
        "Copy .env.example to .env and fill in your API settings."
    )


def _get_optional(name, default):
    value = os.getenv(name)
    return value if value not in (None, "") else default


def _get_int(name, default):
    value = os.getenv(name)
    if value in (None, ""):
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"Environment variable {name} must be an integer.") from exc


def _get_json(name, default):
    value = os.getenv(name)
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Environment variable {name} must be valid JSON."
        ) from exc


# Strong model (query rewrite + summarization)
MAIN_API_KEY = _get_required("MAIN_API_KEY")
MAIN_BASE_URL = _get_optional("MAIN_BASE_URL", "https://api.example.com")
MAIN_MODEL = _get_required("MAIN_MODEL")

# Lightweight model (retrieval — the cheapest model that can follow instructions)
RETRIEVAL_API_KEY = _get_required("RETRIEVAL_API_KEY")
RETRIEVAL_BASE_URL = _get_optional("RETRIEVAL_BASE_URL", "https://api.example.com")
RETRIEVAL_MODEL = _get_required("RETRIEVAL_MODEL")
RETRIEVAL_API_STYLE = _get_optional("RETRIEVAL_API_STYLE", "auto")

# Optional provider-specific retrieval parameters.
# Example JSON: {"thinking": {"type": "disabled"}}
RETRIEVAL_EXTRA_BODY = _get_json("RETRIEVAL_EXTRA_BODY", None)

# Splitting
MAX_TOKENS = _get_int("MAX_TOKENS", 1000)
OVERLAP_TOKENS = _get_int("OVERLAP_TOKENS", 100)

# Directories
DOCS_DIR = _get_optional("DOCS_DIR", "./docs")
LOG_DIR = _get_optional("LOG_DIR", "./logs")
