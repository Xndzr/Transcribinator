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
    filename='transcription.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VideoTranscriptionPipeline:
    def __init__(self, max_concurrent_downloads=10, max_concurrent_transcriptions=4):
        """
        Initialize the video transcription pipeline.
        
        Args:
            max_concurrent_downloads: Maximum number of concurrent video downloads
            max_concurrent_transcriptions: Maximum number of concurrent transcription jobs
        """
        self.max_concurrent_downloads = max_concurrent_downloads
        self.max_concurrent_transcriptions = max_concurrent_transcriptions
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
        
        # Create a unique filename based on the video URL
        video_id = video_url.split('/')[-1] if '/' in video_url else video_url
        audio_file = os.path.join(self.temp_dir, f"{video_id}.wav")
        
        try:
            # Use yt-dlp to download and extract audio in one step
            cmd = [
                "yt-dlp",
                "--extract-audio",
                "--audio-format", "wav",
                "--output", audio_file,
                video_url
            ]
            
            # Run the command and capture output
            process = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            
            if os.path.exists(audio_file):
                logger.info(f"Successfully downloaded and extracted audio for {video_url}")
                return audio_file
            else:
                logger.error(f"Audio extraction completed but file not found for {video_url}")
                return None
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to download or extract audio from {video_url}: {str(e)}")
            logger.error(f"Error output: {e.stderr}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error processing {video_url}: {str(e)}")
            return None
    
    def transcribe_audio(self, audio_file, video_url):
        """
        Transcribe audio file using Whisper
        
        Args:
            audio_file: Path to the WAV audio file
            video_url: Original video URL (for reference)
            
        Returns:
            Dictionary with transcription results or error info
        """
        logger.info(f"Starting transcription for {audio_file} from {video_url}")
        
        try:
            # Perform transcription using Whisper
            result = self.whisper_model.transcribe(audio_file)
            
            # Get the transcript text
            transcript = result.get("text", "").strip()
            
            if transcript:
                logger.info(f"Successfully transcribed audio from {video_url}")
                return {
                    "url": video_url,
                    "status": "success",
                    "transcript": transcript
                }
            else:
                logger.warning(f"Transcription completed but empty result for {video_url}")
                return {
                    "url": video_url,
                    "status": "empty",
                    "transcript": "No speech detected in video."
                }
                
        except Exception as e:
            logger.error(f"Failed to transcribe {audio_file} from {video_url}: {str(e)}")
            return {
                "url": video_url,
                "status": "error",
                "error_message": str(e)
            }
        finally:
            # Clean up the audio file
            try:
                if os.path.exists(audio_file):
                    os.remove(audio_file)
                    logger.info(f"Removed temporary audio file: {audio_file}")
            except Exception as e:
                logger.warning(f"Failed to delete temporary audio file {audio_file}: {str(e)}")
    
    def generate_pdf(self, output_path="transcripts.pdf"):
        """
        Generate PDF with all transcripts
        
        Args:
            output_path: Path to save the PDF file
        """
        logger.info(f"Generating PDF report at {output_path}")
        
        # PDF setup
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        
        # Create custom styles
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=12
        )
        
        url_style = ParagraphStyle(
            'URLStyle',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.blue,
            spaceAfter=6
        )
        
        transcript_style = ParagraphStyle(
            'TranscriptStyle',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=12
        )
        
        error_style = ParagraphStyle(
            'ErrorStyle',
            parent=styles['Normal'],
            textColor=colors.red,
            fontSize=10
        )
        
        # Content for the PDF
        content = []
        
        # Add title
        content.append(Paragraph("Video Transcription Report", title_style))
        content.append(Paragraph(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        content.append(Spacer(1, 24))
        
        # Add transcripts
        for idx, result in enumerate(self.results, 1):
            # Add page break after first page for better readability
            if idx > 1:
                content.append(PageBreak())
            
            # Video header
            content.append(Paragraph(f"Video {idx}", title_style))
            content.append(Paragraph(f"Source: {result['url']}", url_style))
            content.append(Spacer(1, 12))
            
            # Transcript or error message
            if result['status'] == 'success':
                content.append(Paragraph(result['transcript'], transcript_style))
            elif result['status'] == 'empty':
                content.append(Paragraph("No speech detected in this video.", error_style))
            else:
                content.append(Paragraph(f"Error: Failed to transcribe this video.", error_style))
                content.append(Paragraph(f"Details: {result.get('error_message', 'Unknown error')}", error_style))
        
        # Add error summary if any
        if self.errors:
            content.append(PageBreak())
            content.append(Paragraph("Error Summary", title_style))
            content.append(Spacer(1, 12))
            
            for error in self.errors:
                content.append(Paragraph(f"• {error['url']}: {error['error_message']}", error_style))
        
        # Build the PDF
        try:
            doc.build(content)
            logger.info(f"PDF report successfully generated at {output_path}")
        except Exception as e:
            logger.error(f"Failed to generate PDF report: {str(e)}")
            raise
    
    def process_videos(self, video_urls, output_pdf="transcripts.pdf", whisper_model_name="base"):
        """
        Process a list of videos through the full pipeline
        
        Args:
            video_urls: List of video URLs to process
            output_pdf: Path to save the output PDF
            whisper_model_name: Name of the Whisper model to use
        """
        start_time = time.time()
        logger.info(f"Starting pipeline for {len(video_urls)} videos")
        
        # Clear previous results
        self.results = []
        self.errors = []
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            self.temp_dir = temp_dir
            logger.info(f"Created temporary directory: {temp_dir}")
            
            # Initialize Whisper model
            self.initialize(model_name=whisper_model_name)
            
            # Download and extract audio in parallel
            download_futures = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_concurrent_downloads) as download_executor:
                # Submit download jobs
                for url in video_urls:
                    future = download_executor.submit(self.download_and_extract_audio, url)
                    download_futures.append((future, url))
                
                # Process transcriptions as downloads complete
                with concurrent.futures.ProcessPoolExecutor(max_workers=self.max_concurrent_transcriptions) as transcribe_executor:
                    transcribe_futures = []
                    
                    # As each download completes, submit it for transcription
                    for future, url in download_futures:
                        try:
                            audio_file = future.result()
                            if audio_file:
                                # Submit for transcription
                                transcribe_future = transcribe_executor.submit(self.transcribe_audio, audio_file, url)
                                transcribe_futures.append(transcribe_future)
                            else:
                                # Log download failure
                                self.errors.append({
                                    "url": url,
                                    "error_message": "Failed to download or extract audio"
                                })
                        except Exception as e:
                            logger.error(f"Error processing download result for {url}: {str(e)}")
                            self.errors.append({
                                "url": url,
                                "error_message": f"Download processing error: {str(e)}"
                            })
                    
                    # Collect transcription results
                    for future in concurrent.futures.as_completed(transcribe_futures):
                        try:
                            result = future.result()
                            if result:
                                if result['status'] == 'error':
                                    self.errors.append({
                                        "url": result['url'],
                                        "error_message": result.get('error_message', 'Unknown transcription error')
                                    })
                                self.results.append(result)
                        except Exception as e:
                            logger.error(f"Error processing transcription result: {str(e)}")
            
            # Generate the PDF report
            self.generate_pdf(output_pdf)
        
        # Pipeline completion
        elapsed_time = time.time() - start_time
        logger.info(f"Pipeline completed in {elapsed_time:.2f} seconds")
        logger.info(f"Successfully processed: {len(self.results)} videos")
        logger.info(f"Errors encountered: {len(self.errors)} videos")
        
        return {
            "success_count": len(self.results),
            "error_count": len(self.errors),
            "output_pdf": output_pdf,
            "elapsed_time": elapsed_time
        }


# Example usage
if __name__ == "__main__":
    # List of video URLs to process
    video_urls = [
        "https://www.tiktok.com/@example/video/123456789",
        "https://www.instagram.com/reel/AbCdEfGhIjK/",
        # Add more URLs as needed
    ]
    
    # Initialize and run the pipeline
    pipeline = VideoTranscriptionPipeline(
        max_concurrent_downloads=10,  # Adjust based on network bandwidth
        max_concurrent_transcriptions=4  # Adjust based on CPU cores
    )
    
    result = pipeline.process_videos(
        video_urls=video_urls,
        output_pdf="video_transcripts.pdf",
        whisper_model_name="base"  # Options: tiny, base, small, medium, large
    )
    
    print(f"Pipeline completed in {result['elapsed_time']:.2f} seconds")
    print(f"Successfully processed: {result['success_count']} videos")
    print(f"Errors encountered: {result['error_count']} videos")
    print(f"Output saved to: {result['output_pdf']}")