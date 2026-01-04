from moviepy.editor import *
from Transcription import transcribeAudio
import re
import math

class EnhancedTextOverlay:
    def __init__(self, video_path="Final.mp4", output_path="test.mp4"):
        self.video_path = video_path
        self.output_path = output_path
        self.video = VideoFileClip(video_path)
        
        # Styling configuration
        self.config = {
            'font': 'DejaVu-Sans-Bold',
            'fontsize': 15,
            'color': 'white',
            # 'bg_color': (0, 0, 0),  # RGB tuple for black
            'bg_opacity': 0.7,
            'stroke_color': 'black',
            'stroke_width': 1,
            'position': ('center', 'center'),
            # 'margin_bottom': 80,
            'max_width': int(self.video.w * 0.8),
            'line_height': 1.2,
            # 'fade_duration': 0.1,
            'animation_style': 'none'  # 'fade', 'slide', 'none'
        }
    

    
    def split_long_text(self, text, max_chars=35):
        """Split long text into multiple lines for better readability"""
        if len(text) <= max_chars:
            return [text]
        
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            if len(current_line + " " + word) <= max_chars:
                current_line += (" " + word) if current_line else word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def create_text_clip(self, text, start_time, end_time, style_override=None):
        """Create a styled text clip with background and animations"""
        # Apply style overrides
        config = self.config.copy()
        if style_override:
            config.update(style_override)
        
        
        text_lines = self.split_long_text(text)
        text_content = '\n'.join(text_lines)
        
        # Calculate duration
        duration = end_time - start_time
        
        try:
            # Create main text clip with simpler approach
            txt_clip = TextClip(
                txt=text_content,
                fontsize=config['fontsize'],
                font=config['font'],
                color=config['color'],
                method='caption',
                size=(config['max_width'],None),
                align='center'
            )
            
            # Set timing and position
            txt_clip = txt_clip.set_start(start_time).set_duration(duration)
            
            # Set position
            if config['position'] == ('center', 'bottom'):
                y_pos = self.video.h - config['margin_bottom'] - txt_clip.h
                txt_clip = txt_clip.set_position(('center', y_pos))
            else:
                txt_clip = txt_clip.set_position(config['position'])
            
            # Add fade animation
            if config['animation_style'] == 'fade' and config['fade_duration'] > 0:
                fade_dur = min(config['fade_duration'], duration / 2)
                txt_clip = txt_clip.fadein(fade_dur).fadeout(fade_dur)
            
            return txt_clip
            
        except Exception as e:
            print(f"Error creating text clip for '{text}': {e}")
            return None
    
    def process_transcriptions(self, transcriptions):
        """Process all transcription segments and create text clips"""
        text_clips = []
        
        for i, (text, start, end) in enumerate(transcriptions):
            # Skip very short segments
            if end - start < 0.5:
                continue
            
            # Create style variations for different segments
            style_override = {}
            
            # Alternate colors for better visual variety
            if i % 3 == 0:
                style_override['color'] = 'white'
            elif i % 3 == 1:
                style_override['color'] = 'yellow'
            else:
                style_override['color'] = 'yellow'
            
            # Create text clip
            clip = self.create_text_clip(text, start, end, style_override)
            if clip:
                text_clips.append(clip)
        
        return text_clips
    
    def create_enhanced_video(self, transcriptions=None, fps=30):
        """Create the final video with enhanced text overlays"""
        print("Creating enhanced video with dynamic text overlays...")
        
        # Require transcriptions to be provided (no automatic transcription)
        if transcriptions is None:
            print("❌ Error: No transcriptions provided. Transcriptions must be passed to avoid double processing.")
            print("Please call: overlay.create_enhanced_video(transcriptions=your_transcriptions)")
            return

        
        if not transcriptions:
            print("No transcriptions found. Creating video without text overlay.")
            self.video.write_videofile(self.output_path, fps=fps)
            return
        
        print(f"Processing {len(transcriptions)} transcript segments...")
        
        # Create all text clips
        text_clips = self.process_transcriptions(transcriptions)
        
        if not text_clips:
            print("No valid text clips created. Creating video without text overlay.")
            self.video.write_videofile(self.output_path, fps=fps)
            return
        
        print(f"Created {len(text_clips)} text overlay clips")
        
        # Composite all clips together
        all_clips = [self.video] + text_clips
        final_video = CompositeVideoClip(all_clips)
        
        # Write the final video
        print(f"Writing final video to {self.output_path}...")
        final_video.write_videofile(
            self.output_path,
            fps=fps,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True
        )
        
        print("Enhanced video creation completed!")
        
        # Clean up
        final_video.close()
        self.video.close()

def main():
    """Main function to run the enhanced text overlay"""
    # Sample transcription data (replace with actual data)
    sample_transcriptions = [
        [" I don't know well, I don't I don't I'm literally trying to check it all on Twitter, and it's all", 0.0, 5.5],
        [' Nobody deserves you deserve', 7.44, 9.44],
        ["This is a test of the enhanced text overlay system", 10.0, 13.0],
        ["Multiple segments with different colors and animations", 14.0, 17.5],
        ["Creating professional looking YouTube Shorts", 18.0, 21.0]
    ]
    
    # Create enhanced overlay instance
    overlay = EnhancedTextOverlay(
        video_path="Final.mp4",
        output_path="enhanced_output.mp4"
    )
    
    # Customize styling if needed
    overlay.config.update({
        'fontsize': 15,
        'margin_bottom': 100,
        'fade_duration': 0.1,
        'animation_style': 'fade'
    })
    
    # Create the enhanced video
    overlay.create_enhanced_video()

if __name__ == "__main__":
    main()
