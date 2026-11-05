import asyncio
import os
import edge_tts

async def synthesize_scene(text: str, voice: str, output_path: str):
    """
    Synthesize speech for a single scene using Microsoft Edge TTS (high-quality free neural voices).
    Available Korean voices:
    - ko-KR-SunHiNeural (Female, natural & clear)
    - ko-KR-InJoonNeural (Male, warm & confident)
    """
    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(output_path)

def generate_scene_audio(text: str, voice: str, output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    asyncio.run(synthesize_scene(text, voice, output_path))

if __name__ == "__main__":
    test_text = "여러분, 문어에게 심장이 세 개나 있다는 사실, 알고 계셨나요?"
    test_voice = "ko-KR-SunHiNeural"
    test_out = "temp/test.mp3"
    print(f"Generating test audio with voice {test_voice}...")
    generate_scene_audio(test_text, test_voice, test_out)
    print(f"Saved to {test_out}")
