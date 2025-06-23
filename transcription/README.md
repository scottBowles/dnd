# D&D Audio Transcription App

A Django-based audio transcription service designed specifically for Dungeons & Dragons gaming sessions. This app uses OpenAI's Whisper API to transcribe audio files with campaign-specific context for improved accuracy.

## Features

-   🎙️ **Automated Audio Transcription** - Uses OpenAI Whisper API for high-quality transcription
-   🐉 **D&D Campaign Context** - Integrates with your campaign database for character names, places, and lore
-   📁 **Batch Processing** - Process multiple audio files at once
-   ✂️ **Audio Splitting** - Automatically splits large files to meet API limits
-   🔧 **Flexible Configuration** - Customizable paths, settings, and processing options
-   🧪 **Comprehensive Testing** - 25+ tests ensure reliability
-   📊 **JSON Output** - Structured transcription results with metadata

## Quick Start

### Prerequisites

1. **OpenAI API Key** - Set up your API key in one of these ways:

    ```bash
    # Environment variable (recommended)
    export OPENAI_API_KEY="your-api-key-here"

    # Or add to Django settings.py
    OPENAI_API_KEY = "your-api-key-here"
    ```

2. **Audio Files** - Place your audio files in the `recordings/` directory
    - Supported formats: `.flac`, `.wav`, `.aac`, `.m4a`, `.mp3`

### Basic Usage

```bash
# Transcribe all audio files in recordings/ folder
python manage.py transcribe_audio

# Transcribe with session context
python manage.py transcribe_audio --session-number 5

# Process a specific file
python manage.py transcribe_audio --file "session5_part1.mp3"

# See what would be processed without actually transcribing
python manage.py transcribe_audio --dry-run
```

> **📖 Additional Documentation**:
>
> -   **CLI Reference**: See [CLI_REFERENCE.md](CLI_REFERENCE.md) for quick command examples
> -   **Developer API**: See [API_REFERENCE.md](API_REFERENCE.md) for programmatic usage
> -   **Complete Guide**: See [DOCUMENTATION.md](DOCUMENTATION.md) for documentation index

## Command Reference

### `python manage.py transcribe_audio`

The main Django management command for audio transcription.

#### Arguments

| Argument                | Type   | Default        | Description                                                  |
| ----------------------- | ------ | -------------- | ------------------------------------------------------------ |
| `--session-number`      | `int`  | `1`            | Session number for campaign context                          |
| `--file`                | `str`  | `None`         | Specific audio file to transcribe (relative to input folder) |
| `--previous-transcript` | `str`  | `None`         | Path to previous session transcript for context              |
| `--input-folder`        | `str`  | `recordings/`  | Custom input folder path                                     |
| `--output-folder`       | `str`  | `transcripts/` | Custom output folder path                                    |
| `--dry-run`             | `flag` | `False`        | Show what would be processed without transcribing            |

#### Examples

```bash
# Basic transcription of all files
python manage.py transcribe_audio

# Transcribe session 12 with previous context
python manage.py transcribe_audio \
  --session-number 12 \
  --previous-transcript "transcripts/session11.txt"

# Process files from custom directories
python manage.py transcribe_audio \
  --input-folder "/path/to/audio" \
  --output-folder "/path/to/output"

# Transcribe a specific player's recording
python manage.py transcribe_audio \
  --file "player_dorinda.flac" \
  --session-number 8

# Preview what would be processed
python manage.py transcribe_audio --dry-run
```

## Directory Structure

```
your-project/
├── recordings/           # Input audio files (default)
├── transcripts/         # Output JSON files (default)
├── audio_chunks/        # Temporary chunks for large files
└── transcription/
    ├── services.py      # Core transcription services
    ├── models.py        # Django models for data storage
    ├── tests.py         # Comprehensive test suite
    └── management/
        └── commands/
            └── transcribe_audio.py  # Main CLI command
```

## Configuration Options

### Default Settings

The app uses sensible defaults that work for most D&D sessions:

-   **Max file size**: 20MB (under Whisper's 25MB limit)
-   **Chunk duration**: 10 minutes
-   **API delay**: 21 seconds between requests
-   **Recent threshold**: 180 days for campaign context

### Custom Configuration

You can customize these settings by creating a `TranscriptionConfig` instance:

```python
from transcription.services import TranscriptionConfig, TranscriptionService

# Custom configuration
config = TranscriptionConfig(
    input_folder=Path("custom/input"),
    output_folder=Path("custom/output"),
    max_file_size_mb=15,
    chunk_duration_minutes=5,
    recent_threshold_days=90
)

service = TranscriptionService(config)
```

## Output Format

Transcriptions are saved as JSON files with the following structure:

```json
{
    "text": "Full transcription text...",
    "segments": [
        {
            "start": 0.0,
            "end": 5.2,
            "text": "Hello everyone, welcome to session 5..."
        }
    ],
    "metadata": {
        "character_name": "DM",
        "processing_date": "2025-06-07T10:30:00Z",
        "chunk_info": "chunk 1 of 3",
        "database_id": 42
    }
}
```

## Campaign Context Integration

The app automatically includes relevant campaign information in transcription prompts:

### What Gets Included

-   **Character Names**: Recently mentioned characters with races
-   **Places**: Important locations from your campaign
-   **Items & Artifacts**: Notable magical items and artifacts
-   **Organizations**: Guilds, factions, and associations
-   **Races**: Available player and NPC races

### Context Prioritization

The system prioritizes entities that have been:

1. Recently mentioned in game logs (within threshold days)
2. Most frequently referenced
3. Marked as important in your campaign database

## Advanced Usage

### Processing Large Files

Files larger than the configured limit are automatically split:

```bash
# Large file gets split into chunks automatically
python manage.py transcribe_audio --file "3hour_session.mp3"
```

Output:

```
📂 Splitting 3hour_session.mp3 (45.2MB) into chunks...
  ✅ Created 3hour_session_DM_chunk_01.mp3 (20.0MB)
  ✅ Created 3hour_session_DM_chunk_02.mp3 (20.0MB)
  ✅ Created 3hour_session_DM_chunk_03.mp3 (5.2MB)
✅ Split into 3 chunks
```

### Batch Processing with Context

```bash
# Process all files for session 10 with previous session context
python manage.py transcribe_audio \
  --session-number 10 \
  --previous-transcript "transcripts/session09_summary.txt"
```

### Custom Folder Organization

```bash
# Organize by session
python manage.py transcribe_audio \
  --input-folder "recordings/session_12" \
  --output-folder "transcripts/session_12" \
  --session-number 12
```

## Error Handling

The app gracefully handles common issues:

-   **Missing API key**: Clear error message with setup instructions
-   **Invalid audio files**: Skips unsupported formats with warnings
-   **Network issues**: Retries with exponential backoff
-   **Large files**: Automatic splitting and reassembly
-   **Missing directories**: Creates required folders automatically

## Testing

Run the comprehensive test suite:

```bash
# Run all transcription tests
python manage.py test transcription

# Run with verbose output
python manage.py test transcription --verbosity=2

# Run specific test classes
python manage.py test transcription.tests.TranscriptionServiceTests
```

## Performance Tips

1. **File Organization**: Group related audio files in session-specific folders
2. **Previous Context**: Always provide previous session transcripts for better accuracy
3. **Chunk Size**: Smaller chunks (5-8 minutes) often work better for D&D sessions
4. **API Limits**: The default 21-second delay prevents rate limiting

## Troubleshooting

### Common Issues

**"OpenAI API key not found"**

```bash
# Check if your API key is set
echo $OPENAI_API_KEY

# Set it for current session
export OPENAI_API_KEY="your-key-here"
```

**"No audio files found"**

```bash
# Check supported formats in your recordings folder
ls -la recordings/ | grep -E '\.(flac|wav|aac|m4a|mp3)$'
```

**"File too large"**

-   The app automatically splits large files
-   If you see this error, check available disk space for chunks

### Getting Help

1. **Run with dry-run** to see what would be processed:

    ```bash
    python manage.py transcribe_audio --dry-run
    ```

2. **Check the logs** for detailed error information

3. **Verify your setup**:

    ```bash
    # Test Django setup
    python manage.py check

    # Test database connection
    python manage.py shell -c "from transcription.services import TranscriptionConfig; print('Setup OK')"
    ```

## Contributing

The transcription app uses instance-based configuration to avoid shared state issues. When contributing:

1. **Always use instance-based patterns** - Pass config objects rather than modifying class attributes
2. **Write tests** - The app has comprehensive test coverage
3. **Follow Django conventions** - Use management commands for CLI interfaces

## License

This D&D transcription app is part of the larger D&D API project. See the main project LICENSE file for details.
