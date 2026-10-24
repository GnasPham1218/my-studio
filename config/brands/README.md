# Brand profiles

`config/brand.json` là brand mặc định (DiveCode1218). Mỗi kênh khác dùng một
file trong thư mục này và project chọn bằng `"brand": "<id>"`.

```
config/brand.json                          # mặc định
config/brands/english-learner-1218.json    # EnglishLearner1218
```

## Thêm brand

1. Copy một file brand làm mẫu.
2. Đổi `channel`, `colors`, `fonts`, `logo`, `cta`.
3. Trong `projects/<id>/project.json`, thêm `"brand": "<id>"`.
4. Chạy lại `pipeline.build` để props nhận brand mới.

`pipeline.tts` và `pipeline.align` cùng đọc brand của project, nên giọng đọc
và caption debug sẽ theo đúng kênh.

## Một giọng mặc định

Mỗi brand có khối `voice` riêng. Không dùng chung file mẫu giữa hai kênh nếu
muốn hai giọng khác nhau. Quy trình gợi ý cho OmniVoice:

1. Dùng `tools/voice/make_channel_voice.py` để sinh vài ứng viên.
2. Nghe, chọn một ứng viên.
3. Khoá ứng viên đó thành file riêng trong `assets/voice/`.
4. Trỏ `voice.omnivoice.refAudio` của brand tới file đó và dùng
   `mode: "clone"` để mọi scene giữ đúng một giọng.

`EnglishLearner1218` dùng giọng tiếng Anh riêng, không dùng lại mẫu giọng
tiếng Việt của DiveCode1218. Voice mẫu nằm ở
`assets/voice/omnivoice-englishlearner.wav`.

## Nhiều giọng theo ngôn ngữ

Kênh song ngữ có thể thêm `voices` theo mã ngôn ngữ. `voice` vẫn là giọng
mặc định; `voices[lang]` chỉ override khi scene/segment khai báo ngôn ngữ đó.
Nếu không có override, pipeline fallback về `voice`.

Ví dụ `EnglishLearner1218` dùng hai engine:

```json
"voice": {
  "provider": "omnivoice",
  "omnivoice": {
    "mode": "clone",
    "refAudio": "assets/voice/omnivoice-englishlearner.wav",
    "refText": "Hello, welcome to EnglishLearner1218. …",
    "language": "en"
  }
},
"voices": {
  "vi": {
    "provider": "vieneu",
    "vieneu": { "voiceId": "Mai Anh", "language": "vi" }
  }
}
```

- Giọng Anh: OmniVoice clone từ mẫu do model sinh ra.
- Giọng Việt: preset `Mai Anh` của VieNeu, cố định bằng `voiceId`, không nhân
  bản giọng người ngoài.
- Có thể dùng OmniVoice cho cả hai ngôn ngữ nếu muốn; chỉ cần thêm `voices.vi`
  với `provider: "omnivoice"` và một `refAudio` riêng.

Scene có thể chọn giọng theo hai cách:

```json
{ "id": "s01", "language": "vi", "narration": "Hôm nay học một mẹo nhỏ." }
```

hoặc trộn ngay trong scene:

```json
{
  "id": "s05",
  "narration": "Chữ h ở đây câm. An hour, the first sound is a vowel.",
  "segments": [
    { "language": "vi", "text": "Chữ h ở đây câm.", "pauseAfterMs": 180 },
    { "language": "en", "text": "An hour, the first sound is a vowel." }
  ]
}
```

`narration` là bản gộp để đọc/fallback; validation và timing dùng `segments`.
Cache audio gắn với từng đoạn + provider + spec, nên đổi giọng tiếng Việt chỉ
sinh lại các scene có tiếng Việt.

Demo `english-whiteboard-demo` đã được render với cả hai giọng; xem
`projects/english-whiteboard-demo/README.md`.
