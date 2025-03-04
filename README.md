# Transcribinator
Upload social media links -> get a pdf with the transcriptions
# Video Transcription Pipeline

A cost-effective system for batch transcribing short-form videos from platforms like TikTok, Instagram Reels, and more. This pipeline:

1. Downloads videos from provided URLs
2. Extracts audio from each video
3. Transcribes speech to text using OpenAI's Whisper model (running locally)
4. Compiles all transcriptions into a structured PDF report

## Features

- **Parallel Processing**: Download and transcribe up to 25 videos concurrently
- **Efficiency**: Uses temporary storage to minimize disk usage
- **Cost-Effective**: Leverages free, open-source tools with no API costs
- **Robust Error Handling**: Continues processing even if some videos fail
- **Configurable**: Adjust concurrency levels and model size for your hardware

## Requirements

- Python 3.8+
- FFmpeg (for audio extraction)
- GPU recommended for faster transcription (but not required)

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/video-transcription-pipeline.git
   cd video-transcription-pipeline
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install FFmpeg:
   - **Ubuntu/Debian**: `sudo apt install ffmpeg`
   - **macOS**: `brew install ffmpeg`
   - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) or use Chocolatey: `choco install ffmpeg`

## Usage

### Command Line Interface

```bash
python run_transcription.py --input urls.json --output transcripts.pdf --model base
```

Options:
- `--input` or `-i`: Path to JSON file with video URLs or comma-separated list of URLs
- `--output` or `-o`: Output PDF filename (default: transcripts.pdf)
- `--model` or `-m`: Whisper model size (tiny, base, small, medium, large) (default: base)
- `--max-downloads` or `-d`: Maximum concurrent downloads (default: 10)
- `--max-transcriptions` or `-t`: Maximum concurrent transcription processes (default: 4)

### JSON Input Format

```json
[
  "https://www.tiktok.com/@username/video/1234567890",
  "https://www.instagram.com/reel/AbCdEfGhIjK/"
]
```

Or alternatively:

```json
{
  "urls": [
    "https://www.tiktok.com/@username/video/1234567890",
    "https://www.instagram.com/reel/AbCdEfGhIjK/"
  ]
}
```

### Using as a Python Module

```python
from video_transcription_pipeline import VideoTranscriptionPipeline

# Initialize pipeline
pipeline = VideoTranscriptionPipeline(
    max_concurrent_downloads=10,
    max_concurrent_transcriptions=4
)

# Process videos
result = pipeline.process_videos(
    video_urls=[
        "https://www.tiktok.com/@username/video/1234567890",
        "https://www.instagram.com/reel/AbCdEfGhIjK/"
    ],
    output_pdf="transcripts.pdf",
    whisper_model_name="base"  # Options: tiny, base, small, medium, large
)

print(f"Pipeline completed in {result['elapsed_time']:.2f} seconds")
```

## Performance Considerations

- **Whisper Model Size**: Larger models are more accurate but require more RAM and processing power:
  - `tiny`: ~150MB, fastest but least accurate
  - `base`: ~500MB, good balance for most short videos
  - `small`: ~1GB, better accuracy
  - `medium`: ~3GB, high accuracy
  - `large`: ~10GB, highest accuracy but very resource-intensive

- **Concurrency Settings**:
  - For downloads: Adjust based on your network bandwidth (10-25 is usually good)
  - For transcriptions: Set close to your CPU core count (or less if using larger models)

## Troubleshooting

- **yt-dlp Errors**: If downloads fail, try updating yt-dlp: `pip install -U yt-dlp`
- **Memory Issues**: Use a smaller Whisper model or reduce concurrency
- **Slow Transcription**: Consider using a GPU or reducing the model size

## Logging

The system logs all operations to `transcription.log` for debugging purposes.