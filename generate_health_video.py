import os, sys, json, asyncio, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import edge_tts, imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FONT_PATH = "/usr/share/fonts/pickle-hwp/NotoSansCJKkr-Regular.otf"
WIDTH, HEIGHT = 1080, 1920

def get_font(size):
    return ImageFont.truetype(FONT_PATH, size)

def wrap_text(text, font, max_w, draw):
    words = text.split(" ")
    lines, curr = [], []
    for w in words:
        test = " ".join(curr + [w])
        bbox = draw.textbbox((0, 0), test, font=font)
        if (bbox[2] - bbox[0]) <= max_w:
            curr.append(w)
        else:
            if curr: lines.append(" ".join(curr))
            curr = [w]
    if curr: lines.append(" ".join(curr))
    return lines

def process_background(bg_path):
    """Load, resize and crop to 1080x1920, and add subtle dark overlay for contrast."""
    im = Image.open(bg_path).convert("RGB")
    # Resize keeping aspect ratio to cover 1080x1920
    im_ratio = im.width / im.height
    target_ratio = WIDTH / HEIGHT
    if im_ratio > target_ratio:
        new_height = HEIGHT
        new_width = int(HEIGHT * im_ratio)
    else:
        new_width = WIDTH
        new_height = int(WIDTH / im_ratio)
    im = im.resize((new_width, new_height), Image.Resampling.LANCZOS)
    left = (new_width - WIDTH) // 2
    top = (new_height - HEIGHT) // 2
    im = im.crop((left, top, left + WIDTH, top + HEIGHT))

    # Apply slight dark gradient at top and bottom for text readability
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    d_over = ImageDraw.Draw(overlay)
    
    # Top header shadow
    for y in range(450):
        alpha = int(180 * (1.0 - y / 450.0))
        d_over.line([(0, y), (WIDTH, y)], fill=(10, 14, 22, alpha))
        
    # Subtitle area shadow (around y: 1100-1550)
    for y in range(1050, 1600):
        mid = 1300
        dist = abs(y - mid) / 250.0
        alpha = int(150 * max(0, 1.0 - dist))
        d_over.line([(0, y), (WIDTH, y)], fill=(10, 14, 22, alpha))

    # Bottom shadow
    for y in range(HEIGHT - 200, HEIGHT):
        alpha = int(180 * (y - (HEIGHT - 200)) / 200.0)
        d_over.line([(0, y), (WIDTH, y)], fill=(10, 14, 22, alpha))

    im = im.convert("RGBA")
    im = Image.alpha_composite(im, overlay).convert("RGB")
    return im

def create_scene_frame(bg_path, header_title, header_sub, text, keyword, progress):
    img = process_background(bg_path)
    draw = ImageDraw.Draw(img)

    # 1. Top Header Title (Reels style: Big bold white headline)
    head_font = get_font(68)
    h_bbox = draw.textbbox((0, 0), header_title, font=head_font)
    hw = h_bbox[2] - h_bbox[0]
    hx = (WIDTH - hw) // 2
    hy = 180
    # Text stroke / shadow for header
    draw.text((hx, hy), header_title, font=head_font, fill=(255, 255, 255), stroke_width=4, stroke_fill=(15, 20, 30))

    # Top Subtitle line
    sub_head_font = get_font(38)
    sh_bbox = draw.textbbox((0, 0), header_sub, font=sub_head_font)
    shw = sh_bbox[2] - sh_bbox[0]
    shx = (WIDTH - shw) // 2
    shy = 270
    draw.text((shx, shy), header_sub, font=sub_head_font, fill=(255, 215, 0), stroke_width=2, stroke_fill=(20, 20, 20))

    # 2. Lower-Center Subtitle (Reels style: Large white text with black outline)
    sub_font = get_font(52)
    max_w = WIDTH - 160
    lines = wrap_text(text, sub_font, max_w, draw)
    line_h = 82
    total_h = len(lines) * line_h
    start_y = 1250 - total_h // 2

    # Draw semi-transparent pill backdrop behind subtitle for ultimate readability
    pad_x, pad_y = 40, 25
    box_w = min(WIDTH - 100, max(draw.textbbox((0,0), l, font=sub_font)[2] - draw.textbbox((0,0), l, font=sub_font)[0] for l in lines) + pad_x*2)
    box_x = (WIDTH - box_w) // 2
    box_rect = [box_x, start_y - pad_y, box_x + box_w, start_y + total_h + pad_y]
    
    sub_bg = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    d_sub = ImageDraw.Draw(sub_bg)
    d_sub.rounded_rectangle(box_rect, radius=24, fill=(15, 20, 30, 210), outline=(255, 255, 255, 40), width=2)
    img = Image.alpha_composite(img.convert("RGBA"), sub_bg).convert("RGB")
    draw = ImageDraw.Draw(img)

    for i, line in enumerate(lines):
        l_bbox = draw.textbbox((0, 0), line, font=sub_font)
        lw = l_bbox[2] - l_bbox[0]
        lx = (WIDTH - lw) // 2
        ly = start_y + i * line_h
        draw.text((lx, ly), line, font=sub_font, fill=(255, 255, 255), stroke_width=3, stroke_fill=(10, 10, 15))

    # 3. Bottom Keyword tag
    if keyword:
        kw_font = get_font(38)
        kw_text = f"#{keyword}"
        kw_bbox = draw.textbbox((0, 0), kw_text, font=kw_font)
        kw_w = kw_bbox[2] - kw_bbox[0]
        kw_x = (WIDTH - kw_w) // 2
        draw.text((kw_x, 1720), kw_text, font=kw_font, fill=(240, 240, 240), stroke_width=2, stroke_fill=(10, 10, 10))

    # 4. Progress bar at bottom
    bar_w, bar_y = 960, 1830
    bar_x = (WIDTH - bar_w) // 2
    draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + 10], radius=5, fill=(60, 70, 90))
    fill_w = int(bar_w * max(0.05, min(1.0, progress)))
    draw.rounded_rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + 10], radius=5, fill=(255, 204, 0))

    return img

async def tts(text, voice, out_path):
    c = edge_tts.Communicate(text, voice)
    await c.save(out_path)

def get_audio_duration(path):
    cmd = [FFMPEG, "-i", path]
    p = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    for line in p.stderr.split("\n"):
        if "Duration:" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t.split(":")
            return float(h)*3600 + float(m)*60 + float(s)
    return 3.0

async def main():
    os.makedirs("temp_health", exist_ok=True)
    os.makedirs("downloads", exist_ok=True)

    voice = "ko-KR-SunHiNeural"
    scenes = [
        {
            "bg": "downloads/bg_morning.png",
            "header_title": "공복에 독이 되는 음식",
            "header_sub": "건강 상식 · 아침 식사 주의사항",
            "text": "바쁜 아침 건강을 위해 공복에 챙겨 먹었다가, 오히려 위장을 망치는 음식들이 있습니다.",
            "keyword": "공복 건강 주의"
        },
        {
            "bg": "downloads/bg_banana.png",
            "header_title": "1. 바나나",
            "header_sub": "마그네슘 불균형 · 심혈관 부담",
            "text": "첫 번째는 바나나입니다. 공복에 먹으면 마그네슘 수치가 급상승해 혈액 내 칼륨 균형이 깨질 수 있습니다.",
            "keyword": "바나나 공복 주의"
        },
        {
            "bg": "downloads/bg_tomato.png",
            "header_title": "2. 토마토",
            "header_sub": "타닌산 성분 · 위벽 자극과 속쓰림",
            "text": "두 번째는 토마토입니다. 토마토의 타닌산이 위산과 결합하면 위 내부 압력을 높여 심한 속쓰림을 유발합니다.",
            "keyword": "토마토 공복 주의"
        },
        {
            "bg": "downloads/bg_sweet_potato.png",
            "header_title": "3. 고구마",
            "header_sub": "아교질 · 타닌산 위산 과다 분비",
            "text": "세 번째는 고구마입니다. 고구마 속 아교질이 위벽을 자극해 위산이 쏟아져 나오게 만듭니다.",
            "keyword": "고구마 공복 주의"
        },
        {
            "bg": "downloads/bg_water.png",
            "header_title": "공복 추천 음식",
            "header_sub": "미온수 · 삶은 계란 · 양배추",
            "text": "아침 공복에는 따뜻한 물 한 잔과 함께 삶은 계란이나 양배추를 챙겨 드시는 것이 가장 안전합니다.",
            "keyword": "건강한 아침 식단"
        }
    ]

    concat_list = []
    print(f"🎬 Processing {len(scenes)} scenes for Health Shorts...")

    for idx, sc in enumerate(scenes):
        a_path = f"temp_health/a_{idx}.mp3"
        f_path = f"temp_health/f_{idx}.png"
        v_path = f"temp_health/v_{idx}.mp4"
        prog = (idx + 1) / len(scenes)

        print(f"  [{idx+1}/{len(scenes)}] Synthesizing audio & frame...")
        await tts(sc["text"], voice, a_path)
        dur = get_audio_duration(a_path) + 0.3

        frame = create_scene_frame(sc["bg"], sc["header_title"], sc["header_sub"], sc["text"], sc["keyword"], prog)
        frame.save(f_path)

        cmd = [
            FFMPEG, "-y",
            "-loop", "1", "-t", str(dur), "-i", f_path,
            "-i", a_path,
            "-c:v", "libx264", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
            "-shortest", v_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        concat_list.append(f"file '{os.path.abspath(v_path)}'")
        print(f"    Scene {idx+1} rendered ({dur:.1f}s)")

    concat_txt = "temp_health/concat.txt"
    with open(concat_txt, "w") as f:
        f.write("\n".join(concat_list))

    out_mp4 = "downloads/health_empty_stomach_short.mp4"
    cmd = [
        FFMPEG, "-y",
        "-f", "concat", "-safe", "0", "-i", concat_txt,
        "-c", "copy", out_mp4
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # Extract thumbnail
    thumb = "downloads/health_thumbnail.jpg"
    subprocess.run([FFMPEG, "-y", "-ss", "00:00:08", "-i", out_mp4, "-vframes", "1", thumb], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"✅ Finished: {out_mp4} & {thumb}")

asyncio.run(main())
