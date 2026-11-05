import os, sys, json, asyncio, subprocess, urllib.request
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import edge_tts, imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FONT_PATH = "/usr/share/fonts/pickle-hwp/NotoSansCJKkr-Regular.otf"
WIDTH, HEIGHT = 1080, 1920
FPS = 30

# ElevenLabs Korean Voices (Top Creator Picks)
ELEVEN_VOICES = {
    "chris": "PDoCXqBQFGsvfO0hNkEs",      # Chris (캐주얼 대화·쇼츠 1위 남성)
    "yohan": "4JJwo477JUAx3HV0T7n7",      # Yohan Koo (건강·지식 정보 신뢰감 남성)
    "kkc": "1W00IGEmNmwmsDeYy7ag",        # KKC/Mike (빠른 텐션 숏폼 전용 남성)
    "anna": "uyVNoMrnUku1dZyVEXwD"        # Anna Kim (깔끔하고 세련된 정통 여성)
}

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

def create_ui_overlay(header_title, header_sub, text, keyword, progress):
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    for y in range(400):
        alpha = int(160 * (1.0 - y / 400.0))
        draw.line([(0, y), (WIDTH, y)], fill=(10, 14, 22, alpha))

    head_font = get_font(68)
    h_bbox = draw.textbbox((0, 0), header_title, font=head_font)
    draw.text(((WIDTH - (h_bbox[2] - h_bbox[0])) // 2, 180), header_title, font=head_font, fill=(255, 255, 255), stroke_width=4, stroke_fill=(15, 20, 30))

    sub_head_font = get_font(38)
    sh_bbox = draw.textbbox((0, 0), header_sub, font=sub_head_font)
    draw.text(((WIDTH - (sh_bbox[2] - sh_bbox[0])) // 2, 270), header_sub, font=sub_head_font, fill=(255, 215, 0), stroke_width=2, stroke_fill=(20, 20, 20))

    sub_font = get_font(52)
    lines = wrap_text(text, sub_font, WIDTH - 160, draw)
    line_h = 82
    total_h = len(lines) * line_h
    start_y = 1250 - total_h // 2

    pad_x, pad_y = 40, 25
    box_w = min(WIDTH - 100, max(draw.textbbox((0,0), l, font=sub_font)[2] - draw.textbbox((0,0), l, font=sub_font)[0] for l in lines) + pad_x*2)
    box_x = (WIDTH - box_w) // 2
    draw.rounded_rectangle([box_x, start_y - pad_y, box_x + box_w, start_y + total_h + pad_y], radius=24, fill=(15, 20, 30, 215), outline=(255, 255, 255, 45), width=2)

    for i, line in enumerate(lines):
        l_bbox = draw.textbbox((0, 0), line, font=sub_font)
        draw.text(((WIDTH - (l_bbox[2] - l_bbox[0])) // 2, start_y + i * line_h), line, font=sub_font, fill=(255, 255, 255), stroke_width=3, stroke_fill=(10, 10, 15))

    if keyword:
        kw_font = get_font(38)
        kw_text = f"#{keyword}"
        kw_bbox = draw.textbbox((0, 0), kw_text, font=kw_font)
        draw.text(((WIDTH - (kw_bbox[2] - kw_bbox[0])) // 2, 1720), kw_text, font=kw_font, fill=(240, 240, 240), stroke_width=2, stroke_fill=(10, 10, 10))

    bar_w, bar_y = 960, 1830
    bar_x = (WIDTH - bar_w) // 2
    draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + 10], radius=5, fill=(60, 70, 90, 180))
    fill_w = int(bar_w * max(0.05, min(1.0, progress)))
    draw.rounded_rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + 10], radius=5, fill=(255, 204, 0, 240))
    return img

def elevenlabs_tts(text, voice_key, out_path, api_key):
    voice_id = ELEVEN_VOICES.get(voice_key, ELEVEN_VOICES["yohan"])
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    payload = json.dumps({
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.38,
            "similarity_boost": 0.75,
            "speed": 1.12
        }
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        with open(out_path, "wb") as f:
            f.write(resp.read())

async def edge_fallback_tts(text, out_path):
    c = edge_tts.Communicate(text, "ko-KR-HyunsuMultilingualNeural", rate="+14%")
    await c.save(out_path)

def trim_silence(in_path, out_path):
    cmd = [
        FFMPEG, "-y", "-i", in_path,
        "-af", "silenceremove=start_periods=1:start_duration=0.04:start_threshold=-40dB,areverse,silenceremove=start_periods=1:start_duration=0.04:start_threshold=-40dB,areverse",
        out_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def get_audio_duration(path):
    cmd = [FFMPEG, "-i", path]
    p = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    for line in p.stderr.split("\n"):
        if "Duration:" in line:
            t = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t.split(":")
            return float(h)*3600 + float(m)*60 + float(s)
    return 3.0

MOTION_FILTERS = [
    "zoompan=z='min(zoom+0.0015,1.25)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30",
    "zoompan=z='min(zoom+0.0018,1.28)':d={frames}:x='(iw-iw/zoom)*0.55':y='(ih-ih/zoom)*0.45':s=1080x1920:fps=30",
    "zoompan=z='max(1.22-0.0015*on,1.0)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30",
    "zoompan=z='min(zoom+0.0016,1.26)':d={frames}:x='iw/2-(iw/zoom/2)':y='(ih-ih/zoom)*0.6':s=1080x1920:fps=30",
    "zoompan=z='min(zoom+0.0014,1.22)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30"
]

async def main():
    voice_choice = os.environ.get("VOICE_CHOICE", "yohan").lower()
    eleven_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()

    os.makedirs("temp_dynamic", exist_ok=True)
    os.makedirs("downloads", exist_ok=True)

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
            "text": "아침 공복에는 따뜻한 물 한 잔과 함께 삶은 계란이나 양배추를 드시는 것이 가장 안전합니다.",
            "keyword": "건강한 아침 식단"
        }
    ]

    concat_list = []
    print(f"🎬 Processing with Voice: {voice_choice} (ElevenLabs: {'ON' if eleven_key else 'Fallback Edge-TTS'})...")

    for idx, sc in enumerate(scenes):
        raw_a = f"temp_dynamic/raw_a_{idx}.mp3"
        trim_a = f"temp_dynamic/trim_a_{idx}.mp3"
        ui_png = f"temp_dynamic/ui_{idx}.png"
        scene_mp4 = f"temp_dynamic/scene_{idx}.mp4"
        prog = (idx + 1) / len(scenes)

        if eleven_key:
            print(f"  [{idx+1}/{len(scenes)}] ElevenLabs TTS ({voice_choice})...")
            elevenlabs_tts(sc["text"], voice_choice, raw_a, eleven_key)
        else:
            print(f"  [{idx+1}/{len(scenes)}] Fallback Edge-TTS...")
            await edge_fallback_tts(sc["text"], raw_a)

        trim_silence(raw_a, trim_a)
        dur = get_audio_duration(trim_a)
        total_frames = int(dur * FPS) + 1

        ui_img = create_ui_overlay(sc["header_title"], sc["header_sub"], sc["text"], sc["keyword"], prog)
        ui_img.save(ui_png)

        motion_vf = MOTION_FILTERS[idx % len(MOTION_FILTERS)].format(frames=total_frames)
        complex_filter = f"[0:v]{motion_vf}[bg];[bg][1:v]overlay=0:0[outv]"

        cmd = [
            FFMPEG, "-y",
            "-loop", "1", "-i", sc["bg"],
            "-loop", "1", "-i", ui_png,
            "-i", trim_a,
            "-filter_complex", complex_filter,
            "-map", "[outv]", "-map", "2:a",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
            "-t", str(dur),
            scene_mp4
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        concat_list.append(f"file '{os.path.abspath(scene_mp4)}'")

    concat_txt = "temp_dynamic/concat.txt"
    with open(concat_txt, "w") as f:
        f.write("\n".join(concat_list))

    out_mp4 = "downloads/health_empty_stomach_dynamic.mp4"
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", concat_txt, "-c", "copy", out_mp4], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    print("✅ Complete")

if __name__ == "__main__":
    asyncio.run(main())
