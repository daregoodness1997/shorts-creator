from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from moviepy.config import change_settings
import re
import os

# Configure ImageMagick path
IMAGEMAGICK_BINARY = "/usr/local/bin/convert"
if os.path.exists(IMAGEMAGICK_BINARY):
    change_settings({"IMAGEMAGICK_BINARY": IMAGEMAGICK_BINARY})


def add_subtitles_to_video(
    input_video, output_video, transcriptions, video_start_time=0
):
    """
    Add subtitles to video based on transcription segments.

    Args:
        input_video: Path to input video file
        output_video: Path to output video file
        transcriptions: List of [text, start, end] from transcribeAudio
        video_start_time: Start time offset if video was cropped
    """
    video = VideoFileClip(input_video)
    video_duration = video.duration

    # Filter transcriptions to only those within the video timeframe
    relevant_transcriptions = []
    for text, start, end in transcriptions:
        # Adjust times relative to video start
        adjusted_start = start - video_start_time
        adjusted_end = end - video_start_time

        # Only include if within video duration
        if adjusted_end > 0 and adjusted_start < video_duration:
            adjusted_start = max(0, adjusted_start)
            adjusted_end = min(video_duration, adjusted_end)
            relevant_transcriptions.append([text.strip(), adjusted_start, adjusted_end])

    if not relevant_transcriptions:
        print("No transcriptions found for this video segment")
        video.write_videofile(output_video, codec="libx264", audio_codec="aac")
        video.close()
        return

    # Create text clips for each transcription segment
    text_clips = []

    # Scale font size proportionally to video height for better readability
    # 1080p → 70px, 720p → 47px
    dynamic_fontsize = int(video.h * 0.065)

    for text, start, end in relevant_transcriptions:
        # Clean up text
        text = text.strip()
        if not text:
            continue

        # Modern subtitle styling with green background box
        # Black text on #52b788 green background with padding
        txt_clip = TextClip(
            text,
            fontsize=dynamic_fontsize,
            color="black",  # Black text for contrast on green
            font="Arial-Bold",  # Bold, clean, modern font
            method="caption",
            size=(video.w - 160, None),  # Leave 80px margin on each side for padding
            align="center",
            kerning=2,  # Better letter spacing
            bg_color="#52b788",  # Modern green background
        )

        # Add padding around the text by creating a margin box
        # Position at bottom center with breathing room
        bottom_margin = int(video.h * 0.12)  # 12% from bottom
        txt_clip = txt_clip.margin(
            left=40, right=40, top=20, bottom=20, color=(82, 183, 136), opacity=1.0
        )  # RGB for #52b788
        
        txt_clip = txt_clip.set_position(
            ("center", video.h - txt_clip.h - bottom_margin)
        )
        txt_clip = txt_clip.set_start(start)
        txt_clip = txt_clip.set_duration(end - start)

        text_clips.append(txt_clip)

    # Composite video with subtitles
    print(f"Adding {len(text_clips)} subtitle segments to video...")
    final_video = CompositeVideoClip([video] + text_clips)

    # Write output
    final_video.write_videofile(
        output_video,
        codec="libx264",
        audio_codec="aac",
        fps=video.fps,
        preset="medium",
        bitrate="3000k",
    )

    video.close()
    final_video.close()
    print(f"✓ Subtitles added successfully -> {output_video}")
