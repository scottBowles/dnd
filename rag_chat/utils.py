import tiktoken

_encoding_cache: dict[str, tiktoken.Encoding] = {}


def _get_encoding(model: str) -> tiktoken.Encoding:
    """Return a cached tiktoken encoding for the given model."""
    if model not in _encoding_cache:
        try:
            _encoding_cache[model] = tiktoken.encoding_for_model(model)
        except Exception:
            _encoding_cache[model] = tiktoken.get_encoding("cl100k_base")
    return _encoding_cache[model]


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """Count tokens for a given text using tiktoken."""
    try:
        return len(_get_encoding(model).encode(text))
    except Exception:
        # Fallback: assume 1 token per 4 characters
        return len(text) // 4
