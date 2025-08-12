def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """Count tokens for a given text using tiktoken."""
    import tiktoken

    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception as e:
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except:
            # Fallback: assume 1 token per 4 characters
            return len(text) // 4
