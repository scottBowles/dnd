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


def cleanup_temporary_files(max_age_hours: int = 24) -> None:
    """
    Clean up temporary audio files and chunks older than specified age.
    
    Args:
        max_age_hours: Maximum age of files to keep (in hours)
    """
    import tempfile
    import time
    import os
    from datetime import datetime, timedelta
    
    temp_dir = Path(tempfile.gettempdir())
    cutoff_time = time.time() - (max_age_hours * 3600)
    
    # Patterns for temporary files created by transcription service
    patterns = [
        "session_audio_*",
        "chunk_*",
        "*.tmp",
        "transcription_*"
    ]
    
    cleaned_count = 0
    
    for pattern in patterns:
        for file_path in temp_dir.glob(pattern):
            try:
                # Check if file is older than cutoff time
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    cleaned_count += 1
                    print(f"🗑️ Cleaned up temporary file: {file_path.name}")
            except (OSError, FileNotFoundError):
                # File might have been deleted by another process
                pass
    
    print(f"🧹 Cleanup completed. Removed {cleaned_count} temporary files.")
