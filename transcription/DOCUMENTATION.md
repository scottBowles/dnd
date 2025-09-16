# D&D Transcription App - Complete Documentation Index

This directory contains a comprehensive audio transcription system designed specifically for Dungeons & Dragons gaming sessions. Below is your complete guide to understanding and using the transcription app.

## 📚 Documentation Overview

### Documentation by User Type

| User Type         | Primary Documentation                  | Additional Resources                              |
| ----------------- | -------------------------------------- | ------------------------------------------------- |
| **New Users**     | [README.md](README.md) → Quick Start   | [CLI_REFERENCE.md](CLI_REFERENCE.md) for commands |
| **CLI Users**     | [CLI_REFERENCE.md](CLI_REFERENCE.md)   | [README.md](README.md) → Command Reference        |
| **Developers**    | [API_REFERENCE.md](API_REFERENCE.md)   | [services.py](services.py) for code examples      |
| **System Admins** | [README.md](README.md) → Configuration | [tests.py](tests.py) for validation               |

### Core Documentation

| Document                                 | Purpose                                  | Audience                 |
| ---------------------------------------- | ---------------------------------------- | ------------------------ |
| **[README.md](README.md)**               | Complete feature guide, setup, and usage | All users                |
| **[CLI_REFERENCE.md](CLI_REFERENCE.md)** | Quick command reference                  | CLI users                |
| **[API_REFERENCE.md](API_REFERENCE.md)** | Developer API documentation              | Developers               |
| **[DOCUMENTATION.md](DOCUMENTATION.md)** | This index file                          | Documentation navigators |

### Code Documentation

| File                                                                                   | Purpose                  | Key Classes/Functions                                                                             |
| -------------------------------------------------------------------------------------- | ------------------------ | ------------------------------------------------------------------------------------------------- |
| **[services.py](services.py)**                                                         | Core transcription logic | `TranscriptionConfig`, `TranscriptionService`, `AudioProcessingService`, `CampaignContextService` |
| **[utils.py](utils.py)**                                                               | Utility functions        | `safe_save_json()`, `ordinal()`                                                                   |
| **[responses.py](responses.py)**                                                       | API response handling    | `WhisperResponse` class for safe API response access                                              |
| **[models.py](models.py)**                                                             | Database models          | `TranscriptionSession`, `AudioTranscript`, `TranscriptChunk`                                      |
| **[tests.py](tests.py)**                                                               | Comprehensive test suite | 25+ tests for all components                                                                      |
| **[management/commands/transcribe_audio.py](management/commands/transcribe_audio.py)** | Django CLI command       | Main entry point for transcription                                                                |

## 🚀 Quick Start Guide

### 1. First Time Setup

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="your-key-here"

# Run database migrations for transcription models
python manage.py makemigrations transcription
python manage.py migrate

# Place audio files in recordings folder
mkdir -p recordings
cp your-audio-files.mp3 recordings/

# Run your first transcription
python manage.py transcribe_audio --session-notes "First session"
```

### 2. Essential Commands

```bash
# Basic transcription
python manage.py transcribe_audio

# With session context and GameLog
python manage.py transcribe_audio --log-url "session-5-url"

# Process specific file
python manage.py transcribe_audio --file "dm.flac"

# Preview without processing
python manage.py transcribe_audio --dry-run
```

### 3. Programmatic Usage

```python
from pathlib import Path
from transcription.services import TranscriptionConfig, TranscriptionService

# Create and use transcription service
config = TranscriptionConfig(input_folder=Path("my_audio"))
service = TranscriptionService(config)

# Process file with splitting support and session context
success = service.process_file_with_splitting(
    Path("session.mp3"),
    session_notes="Tonight we explore the dungeon...",
    log=gamelog  # Optional: link to GameLog for database storage
)

# Get campaign context for custom usage
formatted_context = service.context_service.get_formatted_context()
print(f"Campaign context: {formatted_context}")
```

> **💡 Tip**: See [API_REFERENCE.md](API_REFERENCE.md) for complete programmatic usage documentation.

## 🎯 Features at a Glance

### Core Capabilities

-   **Whisper API Integration**: High-quality AI transcription
-   **Campaign Context**: Automatic inclusion of character names, places, items
-   **Audio Splitting**: Handles large files automatically
-   **Batch Processing**: Process multiple files at once
-   **Flexible Configuration**: Customizable paths and settings

### Supported Audio Formats

-   `.flac` (recommended)
-   `.wav`
-   `.aac`
-   `.m4a`
-   `.mp3`

### Output Format

-   JSON files with full transcript text
-   Timestamped segments
-   Campaign context metadata
-   Processing information

## 🏗 System Architecture

### Instance-Based Design

The app uses instance-based configuration to avoid shared state issues:

```python
# Create custom configuration
config = TranscriptionConfig(
    input_folder=Path("session_recordings"),
    max_file_size_mb=15,
    chunk_duration_minutes=5
)

# Use with service
service = TranscriptionService(config)
```

### Service Components

1. **TranscriptionConfig**: Configuration and settings management with lazy directory creation
2. **CampaignContextService**: Fetches D&D campaign data from database and formats for prompts
3. **AudioProcessingService**: Handles file splitting and audio processing
4. **TranscriptionService**: Main orchestrator for transcription workflow
5. **WhisperResponse** (in `responses.py`): Safe wrapper for OpenAI API responses with validation
6. **Utility functions** (in `utils.py`): Common helpers like `safe_save_json()` and `ordinal()`

## 📁 Directory Structure

```
transcription/
├── README.md                    # Main documentation
├── CLI_REFERENCE.md            # Command reference
├── API_REFERENCE.md            # Developer API documentation
├── DOCUMENTATION.md            # This index file
├── services.py                 # Core business logic
├── utils.py                    # Utility functions (safe_save_json, ordinal)
├── responses.py                # API response handling (WhisperResponse)
├── models.py                   # Database models
├── tests.py                    # Test suite (25+ tests)
├── management/
│   └── commands/
│       └── transcribe_audio.py # Django management command
├── migrations/                 # Database migrations
└── __pycache__/               # Python cache files

# Project Directories (created automatically)
recordings/                     # Input audio files
transcripts/                   # Output JSON files
audio_chunks/                  # Temporary chunks for large files
```

## 🔧 Configuration Options

### Default Settings

-   **Max file size**: 20MB (under Whisper's 25MB limit)
-   **Chunk duration**: 10 minutes
-   **API delay**: 21 seconds between requests
-   **Recent threshold**: 180 days for campaign context
-   **Supported formats**: `.flac`, `.wav`, `.aac`, `.m4a`, `.mp3`

### Customization Examples

```python
# Minimal configuration
config = TranscriptionConfig()

# Custom configuration
config = TranscriptionConfig(
    input_folder=Path("my_recordings"),
    output_folder=Path("my_transcripts"),
    max_file_size_mb=15,
    chunk_duration_minutes=5
)
```

## 🧪 Testing & Development

### Running Tests

```bash
# Run all transcription tests
python manage.py test transcription

# Verbose output
python manage.py test transcription --verbosity=2

# Specific test class
python manage.py test transcription.tests.TranscriptionServiceTests
```

### Test Coverage

-   **25+ comprehensive tests** covering all components
-   **Instance-based testing** ensures no shared state issues
-   **Mock integration** for external services (OpenAI, file system)
-   **Error handling** validation for common failure scenarios

## 🔍 Common Use Cases

### 1. Weekly Session Processing

```bash
# Process session 8 with previous context
python manage.py transcribe_audio \
  --session-number 8 \
  --previous-transcript "transcripts/session_07_summary.txt"
```

### 2. Large File Handling

```bash
# System automatically splits large files
python manage.py transcribe_audio --file "3hour_marathon_session.flac"
```

### 3. Custom Organization

```bash
# Organize by campaign or session
python manage.py transcribe_audio \
  --input-folder "recordings/curse_of_strahd/session_12" \
  --output-folder "transcripts/curse_of_strahd/session_12"
```

### 4. Preview Processing

```bash
# See what would be processed without doing it
python manage.py transcribe_audio --dry-run
```

## 🚨 Troubleshooting Quick Reference

### Common Issues & Solutions

| Issue                      | Solution                                     |
| -------------------------- | -------------------------------------------- |
| "OpenAI API key not found" | `export OPENAI_API_KEY="your-key"`           |
| "No audio files found"     | Check file formats in recordings/ folder     |
| "File too large"           | App auto-splits; check disk space for chunks |
| Rate limiting              | Default 21s delay prevents this              |
| Poor transcription quality | Use previous transcript context              |

### Getting Help

1. **Run dry-run**: `python manage.py transcribe_audio --dry-run`
2. **Check logs**: Review console output for detailed errors
3. **Verify setup**: `python manage.py check`
4. **Test configuration**: `python manage.py shell -c "from transcription.services import TranscriptionConfig; print('OK')"`

## 📖 Further Reading

### External Resources

-   [OpenAI Whisper API Documentation](https://platform.openai.com/docs/guides/speech-to-text)
-   [Django Management Commands](https://docs.djangoproject.com/en/stable/howto/custom-management-commands/)
-   [Audio Processing with PyDub](https://github.com/jiaaro/pydub)

### Related Project Files

-   Django models for characters, places, items (used for campaign context)
-   Main Django settings configuration
-   Project-wide requirements and dependencies

---

**Last Updated**: June 2025  
**Version**: 2.0  
**Test Coverage**: 25+ comprehensive tests  
**Status**: Production ready ✅
