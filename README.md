# 🎬 1분 상식 쇼츠 자동 생성 파이프라인 (Auto Shorts Generator)

코드로 텍스트 대본, 고음질 한국어 음성(TTS), 자막 및 9:16 세로형 프레임을 합성하여 유튜브 쇼츠 / 틱톡 / 릴스용 비디오(MP4)를 자동 생성하는 프로젝트입니다.

---

## 💡 주요 특징

1. **대본 기반 자동화**: `data/trivia_samples.json`에 문장별 텍스트만 넣으면 끝!
2. **고음질 한국어 TTS**: Microsoft Edge-TTS 엔진(`ko-KR-SunHiNeural`, `ko-KR-InJoonNeural`)을 활용해 자연스러운 음성 생성
3. **9:16 세로형 쇼츠 레이아웃**:
   - 1080x1920 Full-HD 세로 해상도
   - 상단 `💡 1분 상식` 뱃지 및 타이틀
   - 중앙 가독성 높은 자막 박스 및 자동 줄바꿈
   - 하단 키워드 태그 및 진행률 프로그레스 바
4. **GitHub Actions 클라우드 렌더링**:
   - 무거운 영상 렌더링을 내 컴퓨터 대신 GitHub 클라우드 러너(FFmpeg 지원)에서 무료로 수행
   - 버튼 클릭 한 번으로 렌더링 후 완성된 MP4 파일 다운로드 제공

---

## 📂 프로젝트 구조

```
auto-shorts-generator/
├── .github/
│   └── workflows/
│       └── render_shorts.yml     # GitHub Actions 자동 렌더링 워크플로우
├── data/
│   └── trivia_samples.json       # 1분 상식 대본 데이터 (문어 심장, 수면 뇌청소 등)
├── generate_audio.py             # TTS 음성 합성 스크립트
├── generate_video.py             # 프레임 디자인, 자막 합성 및 비디오 렌더링 스크립트
├── requirements.txt              # 파이썬 의존성 패키지
└── README.md
```

---

## 🚀 사용 방법

### 방법 1: GitHub Actions에서 클릭 한 번으로 영상 뽑기 (추천!)

1. GitHub 저장소 상단의 **Actions** 탭으로 이동합니다.
2. 왼쪽 목록에서 **🎬 Render 1-Minute Trivia Short Video**를 선택합니다.
3. 우측의 **Run workflow** 버튼을 누릅니다.
4. 제작할 주제(`item_id`)를 고른 후 초록색 **Run workflow**를 클릭합니다.
5. 1~2분 후 작업이 끝나면 완료된 실행 내역 하단의 **Artifacts**에서 `trivia-shorts-*.zip`을 다운로드합니다. 압축을 풀면 바로 볼 수 있는 MP4 영상이 들어있습니다!

---

### 방법 2: 로컬 환경에서 직접 실행하기

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 실행 (기본: 문어 심장 주제)
python generate_video.py --item-id octopus_hearts --output output/octopus.mp4

# 다른 주제 실행 (수면과 뇌)
python generate_video.py --item-id sleep_brain_clean --output output/sleep.mp4
```

---

## ✍️ 새로운 상식 주제 추가하기

`data/trivia_samples.json` 파일에 아래와 같이 새로운 객체를 추가하면 바로 영상으로 만들 수 있습니다:

```json
{
  "id": "banana_seeds",
  "title": "바나나는 원래 씨가 가득했다?",
  "voice": "ko-KR-SunHiNeural",
  "scenes": [
    {
      "text": "우리가 마트에서 사 먹는 바나나에는 왜 씨가 없을까요?",
      "keyword": "바나나의 비밀"
    },
    {
      "text": "사실 원래 야생 바나나는 딱딱한 검은 씨앗으로 가득 차 있었습니다.",
      "keyword": "야생 바나나 씨앗"
    },
    {
      "text": "우리가 먹는 건 돌연변이 품종을 복제해서 번식시킨 것이랍니다!",
      "keyword": "씨 없는 바나나"
    }
  ]
}
```
