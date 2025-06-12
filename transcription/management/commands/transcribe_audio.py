"""
Django management command for transcribing D&D audio files.
"""

from django.core.management.base import BaseCommand, CommandError
from pathlib import Path

from transcription.services import TranscriptionService, TranscriptionConfig


class Command(BaseCommand):
    help = "Transcribe D&D audio files using Whisper API with campaign context"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            help="Specific audio file to transcribe (relative to recordings folder)",
        )
        parser.add_argument(
            "--previous-transcript",
            type=str,
            help="Path to previous session transcript file for context",
        )
        parser.add_argument(
            "--input-folder",
            type=str,
            help="Custom input folder path (default: recordings/)",
        )
        parser.add_argument(
            "--output-folder",
            type=str,
            help="Custom output folder path (default: transcripts/)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be processed without actually transcribing",
        )

    def handle(self, *args, **options):
        try:
            # Create config with custom paths if provided
            config_kwargs = {}
            if options["input_folder"]:
                config_kwargs["input_folder"] = Path(options["input_folder"])
            if options["output_folder"]:
                config_kwargs["output_folder"] = Path(options["output_folder"])

            config = TranscriptionConfig(**config_kwargs)

            # Load previous transcript if provided
            previous_transcript = ""
            if options["previous_transcript"]:
                transcript_path = Path(options["previous_transcript"])
                if transcript_path.exists():
                    previous_transcript = transcript_path.read_text(encoding="utf-8")
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Loaded previous transcript: {transcript_path}"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Previous transcript file not found: {transcript_path}"
                        )
                    )

            # Initialize transcription service with config
            service = TranscriptionService(config)

            # Check if input folder exists
            if not config.input_folder.exists():
                raise CommandError(
                    f"Input folder does not exist: {config.input_folder}"
                )

            # Process specific file or all files
            if options["file"]:
                file_path = config.input_folder / options["file"]
                if not file_path.exists():
                    raise CommandError(f"File does not exist: {file_path}")

                if options["dry_run"]:
                    self.stdout.write(f"Would process file: {file_path}")
                    return

                self.stdout.write(f"Processing file: {file_path}")
                success = service.process_file_with_splitting(
                    file_path, previous_transcript
                )

                if success:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Successfully transcribed: {file_path.name}"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f"Failed to transcribe: {file_path.name}")
                    )
            else:
                # Process all files
                audio_files = [
                    f
                    for f in config.input_folder.iterdir()
                    if f.suffix.lower() in config.audio_extensions
                ]

                if not audio_files:
                    self.stdout.write(
                        self.style.WARNING(
                            f"No audio files found in {config.input_folder}"
                        )
                    )
                    return

                if options["dry_run"]:
                    self.stdout.write(f"Would process {len(audio_files)} files:")
                    for file in audio_files:
                        self.stdout.write(f"  - {file.name}")
                    return

                self.stdout.write(f"Processing {len(audio_files)} files...")
                processed_count = service.process_all_files(previous_transcript)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully processed {processed_count}/{len(audio_files)} files"
                    )
                )

        except Exception as e:
            raise CommandError(f"Transcription failed: {str(e)}")
