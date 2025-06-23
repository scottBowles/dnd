# Developer API Reference

This document provides detailed API documentation for developers who want to use the transcription services programmatically or extend the functionality.

## Core API Classes

### TranscriptionConfig

The configuration class that manages all settings for transcription services.

#### Constructor

```python
TranscriptionConfig(
    input_folder: Optional[Path] = None,           # Default: Path("recordings")
    output_folder: Optional[Path] = None,          # Default: Path("transcripts")
    chunks_folder: Optional[Path] = None,          # Default: Path("audio_chunks")
    max_file_size_mb: int = 20,                    # Max file size before splitting
    chunk_duration_minutes: int = 10,              # Duration of each chunk
    delay_between_requests: int = 21,              # Seconds between API calls
    recent_threshold_days: int = 180,              # Days for campaign context
    openai_api_key: Optional[str] = None           # API key (auto-detected)
)
```

#### Properties

```python
# File processing settings
config.max_file_size_mb          # int: File size threshold for splitting
config.chunk_duration_minutes    # int: Minutes per audio chunk
config.audio_extensions          # List[str]: Supported file extensions

# Directory paths
config.input_folder              # Path: Where to find audio files
config.output_folder             # Path: Where to save transcripts
config.chunks_folder             # Path: Temporary chunk storage

# API settings
config.openai_api_key            # str: OpenAI API key
config.delay_between_requests    # int: Seconds between API calls
config.recent_threshold_days     # int: Days for campaign context relevance
```

#### Methods

```python
# Note: Directories are created automatically on first access via properties
```

### TranscriptionService

Main service for orchestrating the transcription process.

#### Constructor

```python
TranscriptionService(config: Optional[TranscriptionConfig] = None)
```

#### Key Methods

##### File Processing

```python
# Process file with automatic splitting if needed
def process_file_with_splitting(
    self,
    file_path: Path,
    previous_transcript: str = "",
    session_notes: str = "",
    log: Optional[GameLog] = None
) -> bool

# Process all files in input folder
def process_all_files(
    self,
    previous_transcript: str = "",
    session_notes: str = "",
    log: Optional[GameLog] = None
) -> int  # Returns count of successfully processed files
```

##### Internal Methods (Advanced Usage)

```python
# Private method: Create Whisper prompt with campaign context
def _create_whisper_prompt(
    self,
    character_name: str,
    chunk_info: str = "",
    previous_chunks_text: str = "",
    previous_transcript: str = "",
    session_notes: str = ""
) -> str

# Private method: Make API call to Whisper
def _call_whisper_api(
    self,
    file_path: Path,
    character_name: str,
    chunk_info: str = "",
    previous_chunks_text: str = "",
    previous_transcript: str = "",
    session_notes: str = ""
) -> Optional[WhisperResponse]  # Returns WhisperResponse or None
```

## Database Models

The transcription system includes Django models for persistent storage of transcription data alongside JSON file backups.

### TranscriptionSession

Represents a transcription session, optionally linked to a GameLog.

```python
from transcription.models import TranscriptionSession
from nucleus.models import GameLog

# Create session without GameLog
session = TranscriptionSession.objects.create(
    notes="Session notes"
)

# Create session linked to GameLog
game_log = GameLog.objects.get(id=1)
session = TranscriptionSession.objects.create(
    log=game_log,
    notes="Session notes"
)
```

#### Fields

```python
session.log                    # ForeignKey(GameLog): Optional link to game session
session.notes                  # TextField: Session notes
session.created                # DateTimeField: Creation timestamp
session.updated                # DateTimeField: Last update timestamp
```

### AudioTranscript

Stores transcript data for individual audio files.

```python
from transcription.models import AudioTranscript

# Query transcripts
transcript = AudioTranscript.objects.get(id=1)
transcripts = AudioTranscript.objects.filter(session=session)
```

#### Fields

```python
transcript.session                    # ForeignKey(TranscriptionSession)
transcript.original_filename          # CharField: Original audio filename
transcript.character_name             # CharField: Character/player name
transcript.file_size_mb              # FloatField: File size in MB
transcript.duration_minutes          # FloatField: Audio duration (nullable)
transcript.transcript_text           # TextField: Full transcript text
transcript.whisper_response          # JSONField: Full Whisper API response
transcript.was_split                 # BooleanField: Whether file was split
transcript.num_chunks                # PositiveIntegerField: Number of chunks
transcript.processing_time_seconds   # FloatField: Processing time (nullable)
transcript.campaign_context          # JSONField: Campaign context used
transcript.created                   # DateTimeField: Creation timestamp
transcript.updated                   # DateTimeField: Last update timestamp
```

### TranscriptChunk

Stores data for individual chunks of split audio files.

```python
from transcription.models import TranscriptChunk

# Query chunks for a transcript
chunks = TranscriptChunk.objects.filter(transcript=transcript).order_by('chunk_number')
```

#### Fields

```python
chunk.transcript              # ForeignKey(AudioTranscript)
chunk.chunk_number           # PositiveIntegerField: Chunk sequence number
chunk.filename               # CharField: Chunk filename
chunk.start_time_offset      # FloatField: Seconds from start of original file
chunk.duration_seconds       # FloatField: Chunk duration
chunk.chunk_text             # TextField: Chunk transcript text
chunk.whisper_response       # JSONField: Chunk-specific Whisper response
chunk.created                # DateTimeField: Creation timestamp
chunk.updated                # DateTimeField: Last update timestamp
```

## Utility Modules

### transcription.utils

General utility functions used throughout the transcription system.

```python
from transcription.utils import ordinal, safe_save_json

# Convert number to ordinal (1st, 2nd, 3rd, etc.)
def ordinal(n: int) -> str

# Save data to JSON file with error handling
def safe_save_json(data: Any, file_path: Path) -> bool
```

### transcription.responses

Response handling classes for external API responses.

```python
from transcription.responses import WhisperResponse

# See WhisperResponse class documentation below
```

### AudioProcessingService

Service for handling audio file operations and splitting.

#### Constructor

```python
AudioProcessingService(config: TranscriptionConfig)
```

#### Methods

```python
# Split large audio file into smaller chunks
def split_audio_file(
    self,
    file_path: Path,
    character_name: str = "Unknown"
) -> List[Path]  # Returns list of chunk file paths

# Get file size in megabytes
@staticmethod
def get_file_size_mb(file_path: Path) -> float
```

### CampaignContextService

Service for fetching and formatting campaign context from the database.

#### Constructor

```python
CampaignContextService(config: TranscriptionConfig)
```

#### Methods

```python
# Get campaign context from database
def get_campaign_context(self, limit: int = 50) -> Dict[str, List[Dict[str, Any]]]

# Get campaign context formatted for Whisper prompt (RECOMMENDED)
def get_formatted_context(self, max_length: int = 800) -> str
```

### WhisperResponse

Response wrapper class for OpenAI Whisper API responses with validation and safe access.

#### Constructor

```python
from transcription.responses import WhisperResponse

response = WhisperResponse(raw_response: Dict[str, Any])
```

#### Properties

```python
response.is_valid          # bool: True if response has valid structure
response.text              # str: Transcribed text (empty string if invalid)
response.segments          # List[Dict]: Timestamped segments (empty list if invalid)
response.raw_response      # Dict: Original API response
```

#### Usage Example

```python
# Typical usage within the transcription service
whisper_response = WhisperResponse(api_response)
if whisper_response.is_valid:
    print(f"Transcription: {whisper_response.text}")
    for segment in whisper_response.segments:
        print(f"{segment['start']}-{segment['end']}: {segment['text']}")
else:
    print("Invalid response from Whisper API")
```

## Usage Examples

### Basic Programmatic Usage

```python
from pathlib import Path
from transcription.services import TranscriptionConfig, TranscriptionService

# Create custom configuration
config = TranscriptionConfig(
    input_folder=Path("my_recordings"),
    output_folder=Path("my_transcripts"),
    max_file_size_mb=15,
    chunk_duration_minutes=5
)

# Initialize service
service = TranscriptionService(config)

# Process a single file with splitting support
audio_file = Path("my_recordings/session_1.mp3")
success = service.process_file_with_splitting(
    audio_file,
    previous_transcript="Previous session context...",
    session_notes="Important events this session...",
    log=game_log  # Optional: link to GameLog
)

if success:
    print("Transcription successful! Check output folder.")
else:
    print("Transcription failed")
```

### Batch Processing

```python
# Process all files in a directory
processed_count = service.process_all_files(
    previous_transcript="Last session context...",
    session_notes="Tonight we explore the dungeon...",
    log=game_log  # Optional: link to GameLog
)

print(f"Successfully processed {processed_count} files")
```

### Campaign Context Integration

```python
# Access campaign context service directly
context_service = service.context_service

# Get formatted context for custom usage
formatted_context = context_service.get_formatted_context(max_length=600)
print(f"Campaign context: {formatted_context}")

# Get raw context data for analysis
raw_context = context_service.get_campaign_context(limit=30)
character_names = [char['name'] for char in raw_context['characters']]
print(f"Characters in campaign: {character_names}")
```

### Custom Audio Processing

```python
from transcription.services import AudioProcessingService

# Initialize audio service
audio_service = AudioProcessingService(config)

# Check if file needs splitting
file_size = AudioProcessingService.get_file_size_mb(audio_file)
if file_size > config.max_file_size_mb:
    # Split the file
    chunks = audio_service.split_audio_file(audio_file, "PlayerName")
    print(f"Split into {len(chunks)} chunks")
else:
    print("File is small enough to process directly")
```

### Working with WhisperResponse

```python
from transcription.responses import WhisperResponse

# Simulate API response handling
raw_api_response = {
    "text": "The party enters the dungeon...",
    "segments": [
        {"start": 0.0, "end": 3.5, "text": "The party enters"},
        {"start": 3.5, "end": 7.2, "text": " the dungeon..."}
    ]
}

# Wrap in WhisperResponse for safe access
response = WhisperResponse(raw_api_response)

# Check validity before using
if response.is_valid:
    print(f"Full text: {response.text}")
    print(f"Number of segments: {len(response.segments)}")
else:
    print("Invalid API response received")

# Safe access - returns empty string/list if invalid
transcription = response.text  # Always safe to access
segments = response.segments   # Always safe to access
```

### Using Utility Functions

```python
from transcription.utils import ordinal, safe_save_json
from pathlib import Path

# Convert numbers to ordinals
print(ordinal(1))   # "1st"
print(ordinal(22))  # "22nd"
print(ordinal(103)) # "103rd"

# Safe JSON saving with error handling
data = {"session": 5, "transcript": "Game session text..."}
output_file = Path("transcripts/session_5.json")

if safe_save_json(data, output_file):
    print("Transcript saved successfully")
else:
    print("Failed to save transcript")
```

## Response Formats

### Transcription Response

```python
{
    "text": "Full transcription text...",
    "segments": [
        {
            "start": 0.0,
            "end": 5.2,
            "text": "Segment text...",
            "avg_logprob": -0.15,
            "no_speech_prob": 0.01
        }
    ],
    "language": "en"
}
```

### Campaign Context Response

```python
{
    "characters": [
        {
            "name": "Darnit",
            "race": "Human",
            "recent_mentions": 5
        }
    ],
    "places": [
        {
            "name": "Waterdeep",
            "type": "City",
            "recent_mentions": 3
        }
    ],
    "items": [
        {
            "name": "Sword of Flames",
            "type": "Weapon",
            "rarity": "Rare"
        }
    ],
    "races": ["Human", "Elf", "Dwarf"],
    "associations": ["Harpers", "Lords' Alliance"]
}
```

## Error Handling

### Common Exceptions

```python
# Configuration errors
ValueError("OpenAI API key not found")
ValueError("Invalid file format")

# File processing errors
FileNotFoundError("Audio file not found")
PermissionError("Cannot write to output directory")

# API errors
openai.error.RateLimitError("API rate limit exceeded")
openai.error.APIError("OpenAI API error")
```

### Error Handling Patterns

```python
try:
    # Using the current API methods
    success = service.process_file_with_splitting(
        audio_file,
        session_notes="Game session notes...",
        log=game_log  # Optional: link to GameLog
    )
    if success:
        print("Transcription completed successfully")
    else:
        print("Transcription failed or returned no result")

except ValueError as e:
    print(f"Configuration error: {e}")
except FileNotFoundError as e:
    print(f"File error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")

# For direct WhisperResponse handling
try:
    response = service._call_whisper_api(audio_file, "PlayerName", 1)
    if response and response.is_valid:
        print("Success:", response.text)
    else:
        print("API call failed or returned invalid response")
except Exception as e:
    print(f"API error: {e}")
```

## Extension Points

### Custom Configuration

```python
class CustomTranscriptionConfig(TranscriptionConfig):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Add custom settings
        self.custom_setting = kwargs.get('custom_setting', 'default_value')
```

### Custom Context Service

```python
class CustomContextService(CampaignContextService):
    def get_campaign_context(self):
        # Override to add custom context sources
        context = super().get_campaign_context()
        context['custom_data'] = self.get_custom_data()
        return context

    def get_custom_data(self):
        # Your custom context logic
        return {"custom": "data"}
```

### Custom Processing

```python
class CustomTranscriptionService(TranscriptionService):
    def _create_whisper_prompt(self, character_name, **kwargs):
        # Override private method to customize prompt generation
        base_prompt = super()._create_whisper_prompt(
            character_name, **kwargs
        )
        return f"{base_prompt}\n\nCustom instructions: Focus on combat descriptions."

class CustomContextService(CampaignContextService):
    def get_formatted_context(self, max_length: int = 800) -> str:
        # Override to add custom context formatting
        base_context = super().get_formatted_context(max_length)
        return f"HOMEBREW SETTING: {base_context}"

# Use custom services
config = TranscriptionConfig()
service = CustomTranscriptionService(config)
service.context_service = CustomContextService(config)
```

## Testing API

### Mock Objects for Testing

```python
from unittest.mock import Mock, patch
from pathlib import Path
from transcription.services import TranscriptionConfig, TranscriptionService
from transcription.responses import WhisperResponse

# Mock configuration for testing
mock_config = TranscriptionConfig(
    input_folder=Path("/tmp/test_input"),
    output_folder=Path("/tmp/test_output"),
    openai_api_key="test_key"
)

# Mock service with WhisperResponse
@patch('transcription.services.openai')
def test_transcription_service(mock_openai):
    # Mock the OpenAI API response
    mock_openai.Audio.transcribe.return_value = {
        "text": "Test transcription from D&D session",
        "segments": [
            {"start": 0.0, "end": 3.0, "text": "Test transcription"},
            {"start": 3.0, "end": 6.0, "text": " from D&D session"}
        ]
    }

    service = TranscriptionService(mock_config)
    success = service.process_file_with_splitting(
        Path("test.mp3"),
        session_notes="Test session"
    )

    assert success is True
    mock_openai.Audio.transcribe.assert_called_once()

# Test WhisperResponse directly
def test_whisper_response():
    # Test valid response
    valid_response = {"text": "Hello world", "segments": []}
    wrapper = WhisperResponse(valid_response)
    assert wrapper.is_valid
    assert wrapper.text == "Hello world"

    # Test invalid response
    invalid_response = {"error": "API failed"}
    wrapper = WhisperResponse(invalid_response)
    assert not wrapper.is_valid
    assert wrapper.text == ""
    assert wrapper.segments == []
```

## Performance Considerations

### Memory Usage

-   Large audio files are processed in chunks to manage memory
-   Temporary chunk files are cleaned up automatically
-   Consider chunk duration for memory vs. context trade-offs

### API Rate Limits

-   Default 21-second delay between requests prevents rate limiting
-   Adjust `delay_between_requests` based on your API tier
-   Monitor API usage through OpenAI dashboard

### Disk Space

-   Temporary chunks require disk space (cleaned up after processing)
-   Output JSON files are relatively small
-   Consider cleanup of old transcripts for long-running projects

## Version Compatibility

### Python Requirements

-   Python 3.8+
-   Django 3.2+
-   openai package
-   pydub package

### API Compatibility

-   OpenAI Whisper API v1
-   Designed for Whisper-1 model
-   Response format: verbose_json

---

**API Version**: 2.0  
**Last Updated**: June 2025  
**Python Requirements**: Python 3.8+, Django 3.2+  
**API Compatibility**: OpenAI Whisper API v1
