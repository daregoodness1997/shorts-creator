from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from moviepy.config import change_settings
import re
import os

# Configure ImageMagick path
IMAGEMAGICK_BINARY = "/usr/local/bin/convert"
if os.path.exists(IMAGEMAGICK_BINARY):
    change_settings({"IMAGEMAGICK_BINARY": IMAGEMAGICK_BINARY})


def add_subtitles_to_video(
    input_video, output_video, transcriptions, video_start_time=0, style="green_box"
):
    """
    Add subtitles to video based on transcription segments.

    Args:
        input_video: Path to input video file
        output_video: Path to output video file
        transcriptions: List of [text, start, end] from transcribeAudio
        video_start_time: Start time offset if video was cropped
        style: Subtitle style - "green_box", "classic", "minimal", "bold_yellow", "tiktok"
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

    # Define subtitle styles
    styles = {
        "green_box": {
            "fontsize_factor": 0.043,
            "color": "black",
            "bg_color": "#52b788",
            "stroke_color": None,
            "stroke_width": 0,
            "margin": {"left": 40, "right": 40, "top": 20, "bottom": 20, "color": (82, 183, 136)},
            "bottom_margin_factor": 0.12,
        },
        "classic": {
            "fontsize_factor": 0.043,
            "color": "white",
            "bg_color": None,
            "stroke_color": "black",
            "stroke_width": 3,
            "margin": None,
            "bottom_margin_factor": 0.15,
        },
        "minimal": {
            "fontsize_factor": 0.038,
            "color": "white",
            "bg_color": None,
            "stroke_color": "black",
            "stroke_width": 2,
            "margin": None,
            "bottom_margin_factor": 0.10,
        },
        "bold_yellow": {
            "fontsize_factor": 0.050,
            "color": "yellow",
            "bg_color": None,
            "stroke_color": "black",
            "stroke_width": 4,
            "margin": None,
            "bottom_margin_factor": 0.15,
        },
        "tiktok": {
            "fontsize_factor": 0.055,
            "color": "white",
            "bg_color": None,
            "stroke_color": "black",
            "stroke_width": 5,
            "margin": None,
            "bottom_margin_factor": 0.20,
        },
    }

    # Get selected style or default to green_box
    style_config = styles.get(style, styles["green_box"])
    dynamic_fontsize = int(video.h * style_config["fontsize_factor"])

    for text, start, end in relevant_transcriptions:
        # Clean up text
        text = text.strip()
        if not text:
            continue

        # Create text clip with selected style
        txt_clip_params = {
            "txt": text,
            "fontsize": dynamic_fontsize,
            "color": style_config["color"],
            "font": "Arial-Bold",
            "method": "caption",
            "size": (video.w - 160, None),
            "align": "center",
            "kerning": 2,
        }
        
        # Add background color if specified
        if style_config["bg_color"]:
            txt_clip_params["bg_color"] = style_config["bg_color"]
        
        # Add stroke if specified
        if style_config["stroke_color"]:
            txt_clip_params["stroke_color"] = style_config["stroke_color"]
            txt_clip_params["stroke_width"] = style_config["stroke_width"]
        
        txt_clip = TextClip(**txt_clip_params)

        # Add margin/padding if specified
        if style_config["margin"]:
            margin_config = style_config["margin"]
            txt_clip = txt_clip.margin(
                left=margin_config["left"],
                right=margin_config["right"],
                top=margin_config["top"],
                bottom=margin_config["bottom"],
                color=margin_config["color"],
                opacity=1.0,
            )

        # Position at bottom center with breathing room
        bottom_margin = int(video.h * style_config["bottom_margin_factor"])
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
