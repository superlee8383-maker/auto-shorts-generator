import os
import json
import argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips
except ImportError:
    from moviepy import AudioFileClip, ImageClip, concatenate_videoclips

from generate_audio import generate_scene_audio

WIDTH = 1080
HEIGHT = 1920
FPS = 30

def get_korean_font(size: int):
    """
    Search for available Korean font on system (NanumGothic, AppleGothic, Noto Sans CJK, etc.)
    Falls back to default if none found.
    """
    font_paths = [
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "C:\\Windows\\Fonts\\malgun.ttf",
        "C:\\Windows\\Fonts\\gulim.ttc"
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def draw_gradient_background(width, height, top_color=(20, 24, 33), bottom_color=(10, 12, 16)):
    """Draw a smooth vertical dark gradient image."""
    base = Image.new("RGB", (width, height), top_color)
    top_r, top_g, top_b = top_color
    bot_r, bot_g, bot_b = bottom_color
    
    # Simple vertical gradient
    arr = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        ratio = y / float(height)
        r = int(top_r * (1 - ratio) + bot_r * ratio)
        g = int(top_g * (1 - ratio) + bot_g * ratio)
        b = int(top_b * (1 - ratio) + bot_b * ratio)
        arr[y, :, 0] = r
        arr[y, :, 1] = g
        arr[y, :, 2] = b
    return Image.fromarray(arr)

def wrap_text(text: str, font, max_width: int, draw: ImageDraw.Draw) -> list:
    """Wrap text to fit within max_width pixels."""
    words = text.split(" ")
    lines = []
    current_line = []
    
    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
    return lines

def create_scene_frame(title: str, text: str, keyword: str, progress_ratio: float) -> Image.Image:
    """
    Create a single 1080x1920 frame for a scene:
    - Gradient backdrop
    - Top tag: "💡 1분 상식"
    - Subject Title
    - Subtitle card in the center with highlighted text
    - Bottom keyword tag & progress bar
    """
    img = draw_gradient_background(WIDTH, HEIGHT, top_color=(24, 28, 42), bottom_color=(12, 14, 22))
    draw = ImageDraw.Draw(img)

    # 1. Top Category Badge: 💡 1분 상식
    badge_font = get_korean_font(40)
    badge_text = "💡 1분 상식"
    badge_bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    bw = badge_bbox[2] - badge_bbox[0] + 50
    bh = badge_bbox[3] - badge_bbox[1] + 30
    bx = (WIDTH - bw) // 2
    by = 300
    draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=25, fill=(255, 204, 0))
    draw.text((bx + 25, by + 12), badge_text, font=badge_font, fill=(0, 0, 0))

    # 2. Main Title
    title_font = get_korean_font(56)
    t_bbox = draw.textbbox((0, 0), title, font=title_font)
    tw = t_bbox[2] - t_bbox[0]
    draw.text(((WIDTH - tw) // 2, 400), title, font=title_font, fill=(240, 240, 245))

    # 3. Decorative divider
    draw.line([(WIDTH // 2 - 120, 490), (WIDTH // 2 + 120, 490)], fill=(255, 204, 0), width=4)

    # 4. Center Subtitle Box
    box_w = 920
    box_x = (WIDTH - box_w) // 2
    box_y = 750
    box_h = 500

    draw.rounded_rectangle([box_x, box_y, box_x + box_w, box_y + box_h], radius=32, fill=(35, 42, 60, 220), outline=(60, 72, 98), width=3)

    # Subtitle text inside box
    sub_font = get_korean_font(58)
    lines = wrap_text(text, sub_font, box_w - 100, draw)
    line_height = 85
    total_text_h = len(lines) * line_height
    start_y = box_y + (box_h - total_text_h) // 2

    for i, line in enumerate(lines):
        l_bbox = draw.textbbox((0, 0), line, font=sub_font)
        lw = l_bbox[2] - l_bbox[0]
        lx = box_x + (box_w - lw) // 2
        ly = start_y + i * line_height
        
        # Subtle drop shadow
        draw.text((lx + 2, ly + 2), line, font=sub_font, fill=(10, 10, 15))
        draw.text((lx, ly), line, font=sub_font, fill=(255, 255, 255))

    # 5. Bottom Keyword
    if keyword:
        kw_font = get_korean_font(42)
        kw_text = f"#{keyword}"
        kw_bbox = draw.textbbox((0, 0), kw_text, font=kw_font)
        kw_w = kw_bbox[2] - kw_bbox[0]
        draw.text(((WIDTH - kw_w) // 2, 1400), kw_text, font=kw_font, fill=(150, 170, 205))

    # 6. Progress bar at bottom
    bar_y = 1750
    bar_w = 880
    bar_x = (WIDTH - bar_w) // 2
    draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + 12], radius=6, fill=(50, 58, 76))
    fill_w = int(bar_w * max(0.02, min(1.0, progress_ratio)))
    draw.rounded_rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + 12], radius=6, fill=(255, 204, 0))

    return img

def build_trivia_video(trivia_item: dict, output_file: str):
    title = trivia_item["title"]
    voice = trivia_item.get("voice", "ko-KR-SunHiNeural")
    scenes = trivia_item["scenes"]
    
    os.makedirs("temp", exist_ok=True)
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)

    clips = []
    total_scenes = len(scenes)

    print(f"🎬 Starting video creation: '{title}' ({total_scenes} scenes)")

    for idx, scene in enumerate(scenes):
        text = scene["text"]
        keyword = scene.get("keyword", "")
        progress = (idx + 1) / float(total_scenes)

        audio_path = f"temp/audio_{idx}.mp3"
        img_path = f"temp/frame_{idx}.png"

        print(f"  [{idx+1}/{total_scenes}] Generating TTS: {text[:25]}...")
        generate_scene_audio(text, voice, audio_path)

        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration + 0.3  # Add slight natural breathing gap

        frame_img = create_scene_frame(title, text, keyword, progress)
        frame_img.save(img_path)

        img_clip = ImageClip(img_path).set_duration(duration)
        img_clip = img_clip.set_audio(audio_clip)

        clips.append(img_clip)

    print("🎞️ Concatenating scene clips...")
    final_video = concatenate_videoclips(clips, method="compose")

    print(f"🚀 Rendering final MP4 to {output_file}...")
    final_video.write_videofile(
        output_file,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile="temp/temp-audio.m4a",
        remove_temp=True
    )
    print("✅ Video rendering complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate 1-Minute Trivia Short Video")
    parser.add_argument("--item-id", type=str, default="octopus_hearts", help="ID from trivia_samples.json")
    parser.add_argument("--output", type=str, default="output/octopus_trivia_short.mp4", help="Output MP4 file path")
    args = parser.parse_args()

    data_path = os.path.join(os.path.dirname(__file__), "data", "trivia_samples.json")
    with open(data_path, "r", encoding="utf-8") as f:
        samples = json.load(f)

    selected = next((s for s in samples if s["id"] == args.item_id), samples[0])
    build_trivia_video(selected, args.output)
