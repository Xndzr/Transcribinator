import os
import subprocess
import tempfile
import logging
import time
import concurrent.futures
from pathlib import Path
import whisper
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Setup logging
logging.basicConfig(
    filename="transcription.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class VideoTranscriptionPipeline:
    def __init__(
        self, max_concurrent_downloads=5, max_concurrent_transcriptions=2, audio_format="wav"
    ):
        """
        Initialize the video transcription pipeline.

        Args:
            max_concurrent_downloads: Maximum number of concurrent video downloads
            max_concurrent_transcriptions: Maximum number of concurrent transcription jobs
            audio_format: Output audio format (wav or mp3)
        """
        self.max_concurrent_downloads = max_concurrent_downloads
        self.max_concurrent_transcriptions = max_concurrent_transcriptions
        self.audio_format = audio_format
        self.temp_dir = None
        self.whisper_model = None
        self.results = []
        self.errors = []

    def initialize(self, model_name="base"):
        """Initialize resources including the Whisper model"""
        logger.info(f"Initializing pipeline with Whisper model: {model_name}")
        try:
            self.whisper_model = whisper.load_model(model_name)
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {str(e)}")
            raise

    def download_and_extract_audio(self, video_url):
        """
        Download video and extract audio using yt-dlp

        Args:
            video_url: URL of the video to download

        Returns:
            Path to the extracted audio file or None if failed
        """
        logger.info(f"Starting download and audio extraction for {video_url}")

        # Generate a filename-friendly ID
        video_id = video_url.split("/")[-1] if "/" in video_url else video_url
        audio_file = os.path.join(self.temp_dir, f"{video_id}.{self.audio_format}")

        try:
            # Use yt-dlp to download and extract audio
            cmd = [
                "yt-dlp",
                "--extract-audio",
                "--audio-format",
                self.audio_format,
                "--output",
                os.path.join(self.temp_dir, "%(id)s.%(ext)s"),
                video_url,
            ]

            # Run command and capture output
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )

            if os.path.exists(audio_file):
                logger.info(f"Successfully downloaded and extracted audio for {video_url}")
                return audio_file
            else:
                logger.error(f"Audio extraction completed but file not found for {video_url}")
                return None

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to download or extract audio from {video_url}: {str(e)}")
            logger.error(f"Error output: {getattr(e, 'stderr', 'No additional error details')}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error processing {video_url}: {str(e)}")
            return None

    def transcribe_audio(self, audio_file, video_url):
        """
        Transcribe audio file using Whisper

        Args:
            audio_file: Path to the audio file
            video_url: Original video URL (for reference)

        Returns:
            Dictionary with transcription results or error info
        """
        logger.info(f"Starting transcription for {audio_file} from {video_url}")

        try:
            # Perform transcription
            result = self.whisper_model.transcribe(audio_file)

            # Get the transcript text
            transcript = result.get("text", "").strip()

            if transcript:
                logger.info(f"Successfully transcribed audio from {video_url}")
                return {"url": video_url, "status": "success", "transcript": transcript}
            else:
                logger.warning(f"No speech detected for {video_url}")
                return {"url": video_url, "status": "empty", "transcript": "No speech detected."}

        except Exception as e:
            logger.error(f"Failed to transcribe {audio_file} from {video_url}: {str(e)}")
            return {"url": video_url, "status": "error", "error_message": str(e)}
        finally:
            # Clean up audio file
            try:
                if os.path.exists(audio_file):
                    os.remove(audio_file)
                    logger.info(f"Removed temporary audio file: {audio_file}")
            except Exception as e:
                logger.warning(f"Failed to delete temporary audio file {audio_file}: {str(e)}")

    def generate_pdf(self, output_path="transcripts.pdf"):
        """
        Generate PDF with all transcripts
        """
        logger.info(f"Generating PDF report at {output_path}")

        doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        content = []

        # Title
        content.append(Paragraph("Video Transcription Report", styles["Title"]))
        content.append(Spacer(1, 12))

        for idx, result in enumerate(self.results, 1):
            if idx > 1:
                content.append(PageBreak())

            # Video Header
            content.append(Paragraph(f"Video {idx}: {result['url']}", styles["Heading2"]))
            content.append(Spacer(1, 12))

            # Transcript or error
            if result["status"] == "success":
                content.append(Paragraph(result["transcript"], styles["Normal"]))
            else:
                content.append(Paragraph(f"Error: {result.get('error_message', 'Unknown error')}", styles["Normal"]))

        doc.build(content)
        logger.info(f"PDF report successfully generated at {output_path}")

    def process_videos(self, video_urls, output_pdf="transcripts.pdf", whisper_model_name="base"):
        """
        Process a list of videos through the full pipeline
        """
        start_time = time.time()
        logger.info(f"Processing {len(video_urls)} videos")

        self.results = []
        self.errors = []

        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dir = temp_dir
            logger.info(f"Temporary directory created: {temp_dir}")

            self.initialize(whisper_model_name)

            # Download and transcribe in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_concurrent_downloads) as download_executor:
                download_futures = {download_executor.submit(self.download_and_extract_audio, url): url for url in video_urls}

                with concurrent.futures.ProcessPoolExecutor(max_workers=self.max_concurrent_transcriptions) as transcribe_executor:
                    transcribe_futures = []

                    for future in concurrent.futures.as_completed(download_futures):
                        url = download_futures[future]
                        try:
                            audio_file = future.result()
                            if audio_file:
                                transcribe_futures.append(transcribe_executor.submit(self.transcribe_audio, audio_file, url))
                        except Exception as e:
                            logger.error(f"Download failed for {url}: {str(e)}")
                            self.errors.append({"url": url, "error_message": str(e)})

                    for future in concurrent.futures.as_completed(transcribe_futures):
                        self.results.append(future.result())

            self.generate_pdf(output_pdf)

        elapsed_time = time.time() - start_time
        logger.info(f"Pipeline completed in {elapsed_time:.2f} seconds")

        return {"success_count": len(self.results), "error_count": len(self.errors), "output_pdf": output_pdf, "elapsed_time": elapsed_time}


# Example usage
if __name__ == "__main__":
    pipeline = VideoTranscriptionPipeline(audio_format="wav")
    result = pipeline.process_videos(["https://www.tiktok.com/@example/video/123456789"], "video_transcripts.pdf")
    print(f"Processed: {result['success_count']} videos, Errors: {result['error_count']}")
