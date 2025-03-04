import argparse
import json
from video_transcription_pipeline import VideoTranscriptionPipeline

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Process videos and generate transcript PDF.')
    parser.add_argument('--input', '-i', type=str, required=True, 
                        help='Path to JSON file containing video URLs or comma-separated list of URLs')
    parser.add_argument('--output', '-o', type=str, default='transcripts.pdf', 
                        help='Output PDF file path')
    parser.add_argument('--model', '-m', type=str, default='base', 
                        choices=['tiny', 'base', 'small', 'medium', 'large'],
                        help='Whisper model size to use')
    parser.add_argument('--max-downloads', '-d', type=int, default=10, 
                        help='Maximum concurrent downloads')
    parser.add_argument('--max-transcriptions', '-t', type=int, default=4, 
                        help='Maximum concurrent transcription processes')
    
    args = parser.parse_args()
    
    # Parse input to get video URLs
    video_urls = []
    if args.input.endswith('.json'):
        # Load URLs from JSON file
        try:
            with open(args.input, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    video_urls = data
                elif isinstance(data, dict) and 'urls' in data:
                    video_urls = data['urls']
                else:
                    print("Error: JSON file must contain a list of URLs or a dict with 'urls' key")
                    return 1
        except Exception as e:
            print(f"Error loading JSON file: {str(e)}")
            return 1
    else:
        # Parse comma-separated URLs
        video_urls = [url.strip() for url in args.input.split(',') if url.strip()]
    
    # Validate we have URLs to process
    if not video_urls:
        print("Error: No video URLs provided")
        return 1
    
    print(f"Processing {len(video_urls)} videos...")
    
    # Initialize and run the pipeline
    pipeline = VideoTranscriptionPipeline(
        max_concurrent_downloads=args.max_downloads,
        max_concurrent_transcriptions=args.max_transcriptions
    )
    
    result = pipeline.process_videos(
        video_urls=video_urls,
        output_pdf=args.output,
        whisper_model_name=args.model
    )
    
    print(f"Pipeline completed in {result['elapsed_time']:.2f} seconds")
    print(f"Successfully processed: {result['success_count']} videos")
    print(f"Errors encountered: {result['error_count']} videos")
    print(f"Output saved to: {result['output_pdf']}")
    
    return 0

if __name__ == "__main__":
    exit(main())