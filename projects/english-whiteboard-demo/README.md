# EnglishLearner1218 demo

Demo cho style `whiteboard` + brand `english-learner-1218`. Video dạy tiếng Anh
có giải thích tiếng Việt, nên dùng **hai giọng**:

- Tiếng Anh: OmniVoice clone từ `assets/voice/omnivoice-englishlearner.wav`.
- Tiếng Việt: VieNeu preset `Mai Anh`, cấu hình trong `voices.vi` của brand.

Mỗi scene có hai đoạn (`segments`): một đoạn tiếng Việt giải thích ngắn, một
đoạn tiếng Anh đọc câu mẫu. Nhờ vậy tiếng Anh được đọc bằng giọng Anh và tiếng
Việt được đọc bằng giọng Việt, không đọc lẫn.

## Chạy

```powershell
$env:PYTHONUTF8=1

# 1. Sinh audio cho từng scene (tự chọn giọng theo segments)
.\.venv\Scripts\python.exe -u -m pipeline.tts `
    --project-id english-whiteboard-demo --format short

# Chỉ sinh lại vài scene sau khi sửa text
.\.venv\Scripts\python.exe -u -m pipeline.tts `
    --project-id english-whiteboard-demo --format short --only s04,s05

# 2. Can word timing + caption
.\.venv\Scripts\python.exe -u -m pipeline.align `
    --project-id english-whiteboard-demo --format short --force

# 3. Props
.\.venv\Scripts\python.exe -u -m pipeline.build `
    --project-id english-whiteboard-demo --format short

# 4. Still để kiểm tra bố cục
.\.venv\Scripts\python.exe -u -m pipeline.render `
    --project-id english-whiteboard-demo --format short --still 60 --scale 0.5

# 5. Render full
.\.venv\Scripts\python.exe -u -m pipeline.render `
    --project-id english-whiteboard-demo --format short
```

## Ghi chú

- 8 scene, khoảng **35,4 giây**, **18 caption card**. Đa số scene có 2 segment
  (`vi` + `en`); s04 tách câu tiếng Anh thành 2 đoạn để ngắt rõ `a` / `an`.
  Tổng từ mỗi scene không quá 14.
- Nền trắng dấu, thẻ caption giấy, nhân vật que và thanh tiến trình mảnh.
- Caption dùng một khung 3 dòng cố định; chỉ từ đang đọc đổi màu. Khi có
  khoảng lặng ngắn, card trước được giữ tối đa 0,85 giây để không nhấp nháy.
- Voice mẫu tiếng Anh nằm ở `assets/voice/omnivoice-englishlearner.wav`; giọng
  Việt là preset VieNeu `Mai Anh` (không nhân bản giọng ngoài).
- Cấu hình brand ở `config/brands/english-learner-1218.json`; `voice` là giọng
  Anh mặc định, `voices.vi` là giọng Việt.
- Script nằm ở `scripts/short.json`; `narration` là bản gộp, `segments` là nguồn
  quyết định ngôn ngữ/giọng cho từng đoạn.
- `tools/oneoff/make_demo_media.py` chỉ dùng khi muốn xem style **không cần
  TTS**. Chạy script đó sẽ ghi audio bằng silence, nên đừng chạy trước lần
  render cuối.
- Style nằm ở `video/src/styles/whiteboard.ts`; nhân vật ở
  `video/src/visuals/stick/StickFigure.tsx`.
