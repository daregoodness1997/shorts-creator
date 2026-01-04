from Components.YoutubeDownloader import download_youtube_video
from Components.Edit import extractAudio, crop_video
from Components.Transcription import transcribeAudio
from Components.LanguageTasks import GetHighlight, GetMultipleHighlights
from Components.FaceCrop import crop_to_vertical, combine_videos
from Components.Subtitles import add_subtitles_to_video
import sys
import os
import uuid
import re

# Generate unique session ID for this run (for concurrent execution support)
session_id = str(uuid.uuid4())[:8]
print(f"Session ID: {session_id}")

# Check for auto-approve flag (for batch processing)
auto_approve = "--auto-approve" in sys.argv
if auto_approve:
    sys.argv.remove("--auto-approve")

# Check for number of shorts flag
num_shorts = 1  # Default to 1 short
for i, arg in enumerate(sys.argv):
    if arg.startswith("--shorts="):
        try:
            num_shorts = int(arg.split("=")[1])
            sys.argv.pop(i)
            break
        except ValueError:
            print("Invalid --shorts value, using default (1)")

# Check if URL/file was provided as command-line argument
if len(sys.argv) > 1:
    url_or_file = sys.argv[1]
    print(f"Using input from command line: {url_or_file}")
else:
    # Show available videos in the videos folder
    videos_folder = "videos"
    available_videos = []

    if os.path.exists(videos_folder):
        # Get all video files (mp4, webm, avi, mov, mkv)
        video_extensions = (".mp4", ".webm", ".avi", ".mov", ".mkv")
        available_videos = [
            f
            for f in os.listdir(videos_folder)
            if f.lower().endswith(video_extensions) and not f.startswith("video_")
        ]
        available_videos.sort()

    # Interactive menu
    if available_videos:
        print(f"\n{'='*60}")
        print("AVAILABLE VIDEOS IN 'videos' FOLDER:")
        print(f"{'='*60}")
        for idx, video in enumerate(available_videos, 1):
            print(f"{idx}. {video}")
        print(f"{'='*60}\n")

        print("Options:")
        print(
            "  - Enter a number (1-{}) to select from the list above".format(
                len(available_videos)
            )
        )
        print("  - Enter a YouTube URL to download a new video")
        print("  - Enter a file path to use a video from another location")
        print()

        selection = input("Your choice: ").strip()

        # Check if user entered a number
        if selection.isdigit():
            idx = int(selection) - 1
            if 0 <= idx < len(available_videos):
                selected_video = available_videos[idx]
                print(f"\n{'='*60}")
                print(f"Selected: {selected_video}")
                print(f"{'='*60}\n")

                confirm = input("Process this video? (y/n): ").strip().lower()

                if confirm == "y" or confirm == "yes" or confirm == "":
                    url_or_file = os.path.join(videos_folder, selected_video)
                    print(f"✓ Processing: {selected_video}\n")
                    
                    # Ask how many shorts to generate
                    if not auto_approve:
                        shorts_input = input("How many shorts do you want to generate? (default: 1): ").strip()
                        if shorts_input.isdigit() and int(shorts_input) > 0:
                            num_shorts = int(shorts_input)
                        print(f"Will generate {num_shorts} short(s)\n")
                else:
                    print("Cancelled by user.")
                    sys.exit(0)
            else:
                print("Invalid selection number. Please try again.")
                sys.exit(1)
        else:
            # Treat as URL or file path
            url_or_file = selection
    else:
        print("No videos found in 'videos' folder.")
        url_or_file = input("Enter YouTube video URL or local video file path: ")

# Check if input is a local file
video_title = None
if os.path.isfile(url_or_file):
    print(f"Using local video file: {url_or_file}")
    Vid = url_or_file
    # Extract title from filename
    video_title = os.path.splitext(os.path.basename(url_or_file))[0]
else:
    # Assume it's a YouTube URL
    print(f"Downloading from YouTube: {url_or_file}")
    Vid = download_youtube_video(url_or_file)
    if Vid:
        Vid = Vid.replace(".webm", ".mp4")
        print(f"Downloaded video and audio files successfully! at {Vid}")
        # Extract title from downloaded file path
        video_title = os.path.splitext(os.path.basename(Vid))[0]


# Clean and slugify title for filename
def clean_filename(title):
    # Convert to lowercase
    cleaned = title.lower()
    # Remove or replace invalid filename characters
    cleaned = re.sub(r'[<>:"/\\|?*\[\]]', "", cleaned)
    # Replace spaces and underscores with hyphens
    cleaned = re.sub(r"[\s_]+", "-", cleaned)
    # Remove multiple consecutive hyphens
    cleaned = re.sub(r"-+", "-", cleaned)
    # Remove leading/trailing hyphens
    cleaned = cleaned.strip("-")
    # Limit length
    return cleaned[:80]


# Process video (works for both local files and downloaded videos)
if Vid:
    # Create unique temporary filenames
    audio_file = f"audio_{session_id}.wav"
    temp_clip = f"temp_clip_{session_id}.mp4"
    temp_cropped = f"temp_cropped_{session_id}.mp4"
    temp_subtitled = f"temp_subtitled_{session_id}.mp4"

    Audio = extractAudio(Vid, audio_file)
    if Audio:

        transcriptions = transcribeAudio(Audio)
        if len(transcriptions) > 0:
            print(f"\n{'='*60}")
            print(f"TRANSCRIPTION SUMMARY: {len(transcriptions)} segments")
            print(f"{'='*60}\n")
            TransText = ""

            for text, start, end in transcriptions:
                TransText += f"{start} - {end}: {text}\n"

            print(f"Analyzing transcription to find {num_shorts} highlight(s)...")
            
            # Get highlights based on number requested
            highlights = GetMultipleHighlights(TransText, num_shorts)

            # Check if GetMultipleHighlights failed
            if highlights is None or len(highlights) == 0:
                print(f"\n{'='*60}")
                print("ERROR: Failed to get highlights from LLM")
                print(f"{'='*60}")
                print("This could be due to:")
                print("  - API issues or rate limiting")
                print("  - Invalid API key")
                print("  - Network connectivity problems")
                print("  - Malformed transcription data")
                print(f"\nTranscription summary:")
                print(f"  Total segments: {len(transcriptions)}")
                print(f"  Total length: {len(TransText)} characters")
                print(f"{'='*60}\n")
                sys.exit(1)  # Exit gracefully
            
            print(f"\n{'='*60}")
            print(f"✓ Successfully extracted {len(highlights)} highlight(s)")
            print(f"{'='*60}\n")
            
            # Process each highlight to create shorts
            created_shorts = []
            for idx, (start, stop) in enumerate(highlights, 1):
                print(f"\n{'='*60}")
                print(f"PROCESSING SHORT {idx}/{len(highlights)}")
                print(f"Time: {start}s - {stop}s ({stop-start}s duration)")
                print(f"{'='*60}\n")

                # Validate times
                if start <= 0 or stop <= 0 or stop <= start:
                    print(f"⚠ Skipping highlight {idx} - invalid time range")
                    continue

                # Create unique temporary filenames for this short
                temp_clip = f"temp_clip_{session_id}_{idx}.mp4"
                temp_cropped = f"temp_cropped_{session_id}_{idx}.mp4"
                temp_subtitled = f"temp_subtitled_{session_id}_{idx}.mp4"

                try:
                    print(f"Step 1/4: Extracting clip from original video...")
                    crop_video(Vid, temp_clip, start, stop)

                    print(f"Step 2/4: Cropping to vertical format (9:16)...")
                    crop_to_vertical(temp_clip, temp_cropped)

                    print(f"Step 3/4: Adding subtitles to video...")
                    add_subtitles_to_video(
                        temp_cropped, temp_subtitled, transcriptions, video_start_time=start
                    )

                    # Generate final output filename
                    clean_title = clean_filename(video_title) if video_title else "output"
                    if len(highlights) > 1:
                        final_output = f"{clean_title}_{session_id}_short_{idx}.mp4"
                    else:
                        final_output = f"{clean_title}_{session_id}_short.mp4"

                    print(f"Step 4/4: Adding audio to final video...")
                    combine_videos(temp_clip, temp_subtitled, final_output)
                    
                    created_shorts.append(final_output)
                    
                    print(f"\n{'='*60}")
                    print(f"✓ SHORT {idx} COMPLETE: {final_output}")
                    print(f"{'='*60}\n")

                    # Clean up temporary files for this short
                    for temp_file in [temp_clip, temp_cropped, temp_subtitled]:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)

                except Exception as e:
                    print(f"\n⚠ ERROR creating short {idx}: {e}")
                    continue

            # Final summary
            print(f"\n{'='*60}")
            print(f"✓✓✓ ALL DONE! ✓✓✓")
            print(f"{'='*60}")
            print(f"Successfully created {len(created_shorts)} short(s):")
            for short in created_shorts:
                print(f"  • {short}")
            print(f"{'='*60}\n")

            # Clean up audio file
            try:
                if os.path.exists(audio_file):
                    os.remove(audio_file)
                print(f"Cleaned up session files for {session_id}")
            except Exception as e:
                print(f"Warning: Could not clean up some files: {e}")
        else:
            print("No transcriptions found")
    else:
        print("No audio file found")
else:
    print("Unable to process the video")
