"""
Utility functions for transcription services.
Contains generic helper functions that can be reused across the transcription module.
"""

import json
from pathlib import Path
from typing import Any


def safe_save_json(data: Any, output_path: Path, description: str = "file") -> bool:
    """Safely serialize data to JSON and save to file.

    Args:
        data: The data to serialize and save
        output_path: Path where the JSON file should be saved
        description: Description of the file for logging purposes

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        json_content = json.dumps(data, indent=2, ensure_ascii=False)
        output_path.write_text(json_content, encoding="utf-8")
        print(f"✅ Saved {description}: {output_path}")
        return True
    except (TypeError, ValueError) as e:
        print(f"❌ Failed to serialize {description} to JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ Failed to save {description}: {e}")
        return False


def ordinal(n: int) -> str:
    """Convert number to ordinal (1st, 2nd, 3rd, etc.).

    Args:
        n: The number to convert

    Returns:
        str: The ordinal representation (e.g., "1st", "2nd", "3rd")
    """
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"
