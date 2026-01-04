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
manual_timeframes = None  # For manual time specification
subtitle_style = "green_box"  # Default subtitle style
zoom_mode = "auto"  # Default zoom mode

for i, arg in enumerate(sys.argv[:]):
    if arg.startswith("--shorts="):
        try:
            num_shorts = int(arg.split("=")[1])
            sys.argv.remove(arg)
        except ValueError:
            print("Invalid --shorts value, using default (1)")
    elif arg.startswith("--times="):
        # Parse manual timeframes like --times="10-130,200-320"
        try:
            manual_timeframes = arg.split("=")[1]
            sys.argv.remove(arg)
        except:
            print("Invalid --times value")
    elif arg.startswith("--subtitle-style="):
        try:
            subtitle_style = arg.split("=")[1]
            sys.argv.remove(arg)
        except:
            print("Invalid --subtitle-style value")
    elif arg.startswith("--zoom="):
        try:
            zoom_mode = arg.split("=")[1]
            if zoom_mode not in ["auto", "fit", "fill", "none"]:
                print(f"Invalid --zoom value '{zoom_mode}', using 'auto'")
                zoom_mode = "auto"
            else:
                sys.argv.remove(arg)
        except:
            print("Invalid --zoom value")

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

                    # Ask how to select timeframes
                    if not auto_approve and manual_timeframes is None:
                        print("\nHow would you like to select highlights?")
                        print("  [1] AI automatically selects best moments (default)")
                        print("  [2] Manually specify timeframes")
                        selection_mode = input("Your choice (1/2): ").strip()

                        if selection_mode == "2":
                            print("\nEnter timeframes in format: START-END,START-END")
                            print("Example: 10-130,200-320 (creates 2 shorts)")
                            manual_timeframes = input("Timeframes: ").strip()
                        else:
                            shorts_input = input(
                                "How many shorts do you want to generate? (default: 1): "
                            ).strip()
                            if shorts_input.isdigit() and int(shorts_input) > 0:
                                num_shorts = int(shorts_input)
                            print(
                                f"Will generate {num_shorts} short(s) using AI selection\n"
                            )
                        
                        # Ask for subtitle style
                        print("\nSelect subtitle style:")
                        print("  [1] Green Box (default) - Black text on green background")
                        print("  [2] Classic - White text with black outline")
                        print("  [3] Minimal - Subtle white text with thin outline")
                        print("  [4] Bold Yellow - Large yellow text with thick outline")
                        print("  [5] TikTok - Large white text, prominent outline")
                        style_choice = input("Your choice (1-5): ").strip()
                        
                        style_map = {
                            "1": "green_box",
                            "2": "classic",
                            "3": "minimal",
                            "4": "bold_yellow",
                            "5": "tiktok",
                        }
                        subtitle_style = style_map.get(style_choice, "green_box")
                        print(f"✓ Using '{subtitle_style}' subtitle style\n")
                        
                        # Ask for zoom mode
                        print("\nSelect zoom mode:")
                        print("  [1] Auto (default) - Intelligently adjusts zoom")
                        print("  [2] Fit - Zoom out to show full width")
                        print("  [3] Fill - Zoom in to fill frame (may clip content)")
                        print("  [4] None - No zoom adjustment")
                        zoom_choice = input("Your choice (1-4): ").strip()
                        
                        zoom_map = {
                            "1": "auto",
                            "2": "fit",
                            "3": "fill",
                            "4": "none",
                        }
                        zoom_mode = zoom_map.get(zoom_choice, "auto")
                        print(f"✓ Using '{zoom_mode}' zoom mode\n")
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


# Parse manual timeframes from string
def parse_timeframes(timeframes_str):
    """
    Parse timeframe string like "10-130,200-320" into list of tuples.
    Returns: [(10, 130), (200, 320)] or None if invalid
    """
    try:
        timeframes = []
        segments = timeframes_str.split(",")
        for segment in segments:
            segment = segment.strip()
            if "-" not in segment:
                continue
            start, end = segment.split("-")
            start = int(start.strip())
            end = int(end.strip())
            if start >= 0 and end > start:
                timeframes.append((start, end))
        return timeframes if len(timeframes) > 0 else None
    except Exception as e:
        print(f"Error parsing timeframes: {e}")
        return None


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
        # Check if transcription already exists
        clean_title = clean_filename(video_title) if video_title else "output"
        transcription_file = f"transcriptions/{clean_title}_transcription.txt"

        # Create transcriptions directory if it doesn't exist
        os.makedirs("transcriptions", exist_ok=True)

        # Try to load existing transcription
        transcriptions = None
        if os.path.exists(transcription_file):
            try:
                print(f"\nFound existing transcription: {transcription_file}")
                print("Loading cached transcription...")
                transcriptions = []
                with open(transcription_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and " - " in line and ": " in line:
                            # Parse format: "start - end: text"
                            time_part, text = line.split(": ", 1)
                            start_str, end_str = time_part.split(" - ")
                            start = float(start_str)
                            end = float(end_str)
                            transcriptions.append([text, start, end])
                print(f"✓ Loaded {len(transcriptions)} segments from cache\n")
            except Exception as e:
                print(f"Warning: Could not load cached transcription: {e}")
                transcriptions = None

        # If no cached transcription, create new one
        if transcriptions is None:
            print("Generating new transcription...")
            transcriptions = transcribeAudio(Audio)

            # Save transcription to file
            if len(transcriptions) > 0:
                try:
                    with open(transcription_file, "w", encoding="utf-8") as f:
                        for text, start, end in transcriptions:
                            f.write(f"{start} - {end}: {text}\n")
                    print(f"✓ Transcription saved to: {transcription_file}\n")
                except Exception as e:
                    print(f"Warning: Could not save transcription: {e}")

        if len(transcriptions) > 0:
            print(f"\n{'='*60}")
            print(f"TRANSCRIPTION SUMMARY: {len(transcriptions)} segments")
            print(f"{'='*60}\n")
            TransText = ""

            for text, start, end in transcriptions:
                TransText += f"{start} - {end}: {text}\n"

            # Determine highlights: manual or AI-selected
            if manual_timeframes:
                print(f"\nUsing manually specified timeframes...")
                highlights = parse_timeframes(manual_timeframes)
                if highlights is None:
                    print(f"\n{'='*60}")
                    print("ERROR: Invalid timeframe format")
                    print(f"{'='*60}")
                    print("Expected format: START-END,START-END")
                    print("Example: 10-130,200-320")
                    print(f"{'='*60}\n")
                    sys.exit(1)
                print(f"Parsed {len(highlights)} timeframe(s):")
                for i, (start, end) in enumerate(highlights, 1):
                    print(f"  {i}. {start}s - {end}s ({end-start}s duration)")
                print()
            else:
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
            
            # Create output folder for shorts
            output_folder = "output_shorts"
            os.makedirs(output_folder, exist_ok=True)

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
                    crop_to_vertical(temp_clip, temp_cropped, zoom_mode=zoom_mode)

                    print(f"Step 3/4: Adding subtitles to video...")
                    add_subtitles_to_video(
                        temp_cropped,
                        temp_subtitled,
                        transcriptions,
                        video_start_time=start,
                        style=subtitle_style,
                    )

                    # Generate final output filename
                    clean_title = (
                        clean_filename(video_title) if video_title else "output"
                    )
                    if len(highlights) > 1:
                        final_output = os.path.join(
                            output_folder, f"{clean_title}_{session_id}_short_{idx}.mp4"
                        )
                    else:
                        final_output = os.path.join(
                            output_folder, f"{clean_title}_{session_id}_short.mp4"
                        )

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
