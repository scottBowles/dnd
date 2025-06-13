# Transcription CLI Quick Reference

## Basic Commands

```bash
# Transcribe all files
python manage.py transcribe_audio

# Transcribe with GameLog link
python manage.py transcribe_audio --log-url "session-5-url"

# Transcribe specific file
python manage.py transcribe_audio --file "player1.mp3"

# Dry run (preview only)
python manage.py transcribe_audio --dry-run
```

## Advanced Usage

```bash
# Full session with context and GameLog
python manage.py transcribe_audio \
  --log-url "session-12-url" \
  --session-notes "Epic battle with the dragon" \
  --previous-transcript "transcripts/session11.txt" \
  --input-folder "recordings/session12" \
  --output-folder "transcripts/session12"

# Custom directories
python manage.py transcribe_audio \
  --input-folder "/path/to/audio" \
  --output-folder "/path/to/output"
```

## All Available Flags

| Flag                    | Type   | Description                 | Example                                |
| ----------------------- | ------ | --------------------------- | -------------------------------------- |
| `--log-url`             | `str`  | GameLog URL for correlation | `--log-url "session-5-url"`            |
| `--log-id`              | `str`  | GameLog Google Drive ID     | `--log-id "abc123"`                    |
| `--session-notes`       | `str`  | Notes about the session     | `--session-notes "Epic battle"`        |
| `--file`                | `str`  | Specific file to process    | `--file "dm.flac"`                     |
| `--previous-transcript` | `str`  | Previous session context    | `--previous-transcript "session4.txt"` |
| `--input-folder`        | `str`  | Custom input directory      | `--input-folder "audio/"`              |
| `--output-folder`       | `str`  | Custom output directory     | `--output-folder "results/"`           |
| `--dry-run`             | `flag` | Preview without processing  | `--dry-run`                            |

## Output Examples

### Successful Processing

```
Processing 3 files...
Transcribing player1.mp3...
Saved to /path/to/transcripts/player1.json
Transcribing dm.flac...
📂 Splitting dm.flac (45.2MB) into chunks...
  ✅ Created dm_DM_chunk_01.mp3 (20.0MB)
  ✅ Created dm_DM_chunk_02.mp3 (20.0MB)
✅ Split into 2 chunks
Saved to /path/to/transcripts/dm.json
Successfully processed 3/3 files
```

### Dry Run Output

```
Would process 2 files:
  - session5_part1.mp3
  - session5_part2.flac
```

## Quick Setup

1. **Set API Key**:

    ```bash
    export OPENAI_API_KEY="your-key-here"
    ```

2. **Place Audio Files**:

    ```bash
    cp *.mp3 recordings/
    ```

3. **Run Transcription**:

    ```bash
    python manage.py transcribe_audio --session-number 1
    ```

4. **Check Results**:
    ```bash
    ls transcripts/
    ```
