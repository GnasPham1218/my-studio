# Pipeline

Mỗi file là một bước hoặc một dịch vụ dùng chung. Chạy bằng module:

```powershell
python -m pipeline.script --project-id <id>
python -m pipeline.tts    --project-id <id> --format short
python -m pipeline.align  --project-id <id> --format short
python -m pipeline.build  --project-id <id> --format short
python -m pipeline.render --project-id <id> --format short --aspect vertical
# hoặc tất cả (nhiều khung hình dùng chung audio):
python -m pipeline.make   --project-id <id> --format short --aspect vertical,horizontal
# xuất clip từng cảnh + audio + phụ đề + draft để chỉnh tiếp trong CapCut:
python -m pipeline.capcut --project-id <id> --format short --aspect vertical
# (hoặc thêm --capcut vào pipeline.make)
# phân tích video mẫu thành template:
python -m pipeline.analyze run <video.mp4> --id <template-id>
```

| File | Loại |
|---|---|
| `config.py` | Đọc `formats`/`aspects`/`templates`; gộp template; kiểm schema |
| `paths.py` | Quy ước `projects/` (source) và `out/` (output), aspect, brand, snapshot, status |
| `script.py` | Stage 1 — research + viết kịch bản bằng agent |
| `validate.py` | Dịch vụ — JSON Schema + luật ngữ nghĩa |
| `review.py` | Stage 1b — báo cáo duyệt, fact-check, cổng duyệt trước TTS |
| `visuals.py` | Dịch vụ — catalog visual, kiểm `visual.data`, gộp default |
| `tts.py` | Stage 2 — voiceover |
| `align.py` | Stage 3 — word timing (không phụ thuộc khung hình) |
| `captions.py` | Dịch vụ — chia card phụ đề theo khung hình, ghi SRT/ASS |
| `sfx.py` | Dịch vụ — copy asset SFX theo catalog |
| `build.py` | Stage 4 — `compose()` ghép props.json cho Remotion theo (format, aspect, template) |
| `render.py` | Stage 5 — gọi Remotion |
| `capcut.py` | Stage 6 (tuỳ chọn) — bộ file + draft CapCut (khuôn `config/capcut/draft-template.json`) |
| `make.py` | Orchestrator |
| `progress.py` | Dịch vụ — thanh tiến trình |
| `llm.py` | Dịch vụ — gọi OpenCode agent |
| `voice/` | Adapter TTS (OmniVoice, VieNeu) |
| `analyze/` | Phân tích video mẫu → template giao diện (`docs/ANALYZE.md`) |

Quy tắc: không tự ghép đường dẫn; luôn dùng `paths.py`. Không đọc ngược từ
`out/01-script/` — source nằm ở `projects/`.
