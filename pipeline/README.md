# Pipeline

Mỗi file là một bước hoặc một dịch vụ dùng chung. Chạy bằng module:

```powershell
python -m pipeline.script --project-id <id>
python -m pipeline.tts    --project-id <id> --format short
python -m pipeline.align  --project-id <id> --format short
python -m pipeline.build  --project-id <id> --format short
python -m pipeline.render --project-id <id> --format short
# hoặc tất cả:
python -m pipeline.make   --project-id <id> --format short
```

| File | Loại |
|---|---|
| `paths.py` | Quy ước `projects/` (source) và `out/` (output), brand, snapshot, status |
| `script.py` | Stage 1 — research + viết kịch bản bằng agent |
| `validate.py` | Dịch vụ — JSON Schema + luật ngữ nghĩa |
| `tts.py` | Stage 2 — voiceover |
| `align.py` | Stage 3 — word timing + phụ đề |
| `sfx.py` | Dịch vụ — copy asset SFX theo catalog |
| `build.py` | Stage 4 — props.json cho Remotion |
| `render.py` | Stage 5 — gọi Remotion |
| `make.py` | Orchestrator |
| `progress.py` | Dịch vụ — thanh tiến trình |
| `llm.py` | Dịch vụ — gọi OpenCode agent |
| `voice/` | Adapter TTS (OmniVoice, VieNeu) |

Quy tắc: không tự ghép đường dẫn; luôn dùng `paths.py`. Không đọc ngược từ
`out/01-script/` — source nằm ở `projects/`.
