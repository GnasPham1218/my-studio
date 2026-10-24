# Kiến trúc

Tài liệu này mô tả **ranh giới** giữa các phần của repo. Mục tiêu: thêm một
loại video, một scene hay một visual mới mà không phải sửa lan sang TTS,
render hay các dự án cũ.

## 1. Hai vùng dữ liệu

| Vùng | Vai trò | Có được sửa? | Có thể xoá? |
|---|---|---|---|
| `projects/<id>/` | **Source**: research, kịch bản, style, metadata dự án | Có | Không (hãy backup) |
| `out/<id>/` | **Output**: audio, caption, props, video, log | Không sửa tay | Có, render lại được |

`out/<id>/01-script/` chỉ là bản snapshot một chiều từ `projects/` để đọc
output cho tiện. Pipeline **không bao giờ** đọc ngược từ snapshot.

```
projects/<id>/
  project.json          # style, defaultFormat, formats, metadata, review.<fmt>
  research.md
  scripts/
    short.json
    long.json
  review/
    factcheck-<fmt>.json

out/<id>/
  status.json           # thống kê lần chạy gần nhất
  01-script/            # snapshot
  02-audio/<fmt>/       # wav + manifest + sfx/
  03-captions/<fmt>/    # words.json, srt, ass
  04-props/<fmt>/       # props.json
  05-video/<fmt>.mp4
  99-logs/
```

Mọi đường dẫn đi qua `pipeline/paths.py`. Không module nào tự ghép
`out/...` hay `projects/...` bằng chuỗi.

## 2. Luồng chạy

```
pipeline.script ──► projects/<id>/research.md + scripts/*.json
                         │
pipeline.review ─────────┼──► review/factcheck-<fmt>.json, project.json → review.<fmt>
                         │    (cổng duyệt: tts/build từ chối nếu chưa duyệt đúng hash)
pipeline.tts ────────────┼──► out/<id>/02-audio/<fmt>/
pipeline.align ──────────┼──► out/<id>/03-captions/<fmt>/
pipeline.build ──────────┼──► out/<id>/04-props/<fmt>/props.json
pipeline.render ─────────┴──► out/<id>/05-video/<fmt>.mp4
```

- `pipeline.make` gọi tuần tự TTS → align → build → render.
- `pipeline.build` đọc `projects/<id>/project.json` để lấy `style` và `brand`,
  rồi ghi `styleId` + brand vào props. Renderer chọn style tương ứng.
- Brand mặc định là `config/brand.json`; kênh khác đặt
  `"brand": "<id>"` và dùng `config/brands/<id>.json`.
- Hợp đồng Python ↔ Remotion là `props.json`; type nằm ở
  `video/src/lib/types.ts`.

## 3. Code video

```
video/src/
  Root.tsx                     # đăng ký composition "DiveCode"
  compositions/
    ExplainerVideo.tsx         # timeline, SFX, style, caption, watermark
  scenes/
    shared.tsx                 # grid, headline, kicker, divider, count-up
    Hook.tsx  Punch.tsx  Stat.tsx  List.tsx
    Timeline.tsx  Compare.tsx  Chart.tsx  Outro.tsx
    index.tsx                  # SceneRenderer: scene.type -> component
  visuals/
    icons.tsx
    layout.ts
    tech/
      PhoneMock.tsx  AwardCard.tsx  LoopDiagram.tsx
      ShrinkDiagram.tsx  DeclineChart.tsx  StorageBar.tsx
      LimitsMeters.tsx  QuestionDiagram.tsx
    stick/
      StickFigure.tsx          # nhân vật que + bong bóng thoại
    index.tsx                  # Visual dispatcher + hasVisual
  styles/
    tech-explainer.ts          # nền tối, visual metaphor công nghệ
    whiteboard.ts              # nền giấy, caption thẻ giấy
    index.ts                   # registry + getStyle(id)
  components/
    Captions.tsx  Background.tsx  PaperBackground.tsx
    SceneIndex.tsx  Watermark.tsx
  lib/
    types.ts  theme.ts  motion.ts  defaults.ts
```

### Quy ước

- **Scene** quyết định bố cục và nội dung của một cảnh. Scene không tự đọc
  file; mọi dữ liệu đến từ props.
- **Visual** là một metaphor vẽ bằng code, nhận `scene`, `brand`, `format`.
  Visual không tự quyết định thời lượng hay SFX.
- **Style** chỉ quyết định lớp trình bày (nền, overlay, index, watermark).
  Style không chứa nội dung video.
- **Component** là phần dùng chung toàn video (caption, background…).
- **lib** là code thuần: type, theme, motion hook, default props.

## 4. Pipeline Python

| Module | Trách nhiệm |
|---|---|
| `paths.py` | Quy ước source/output, brand, snapshot, status |
| `script.py` | Gọi agent research/script, validate + repair, rồi fact-check |
| `review.py` | Báo cáo duyệt, kiểm link, fact-check, approve/reject, `require_approved` |
| `validate.py` | JSON Schema + luật ngữ nghĩa |
| `tts.py` | Chọn giọng theo language/segment, cache, chuẩn hoá âm lượng |
| `voice/` | Adapter OmniVoice / VieNeu + `voice_config` theo ngôn ngữ |
| `align.py` | faster-whisper từng segment → word timing → SRT/ASS |
| `sfx.py` | Copy asset thật theo catalog |
| `build.py` | Ghép timeline thật → props.json |
| `render.py` | Gọi Remotion, đọc tiến trình |
| `progress.py` | Thanh tiến trình dùng chung |
| `make.py` | Chạy cả chuỗi |

## 5. Bất biến cần giữ

- **Ảnh:** chỉ visual procedural; không ảnh AI/stock.
- **Giọng:** OmniVoice `clone` với mẫu cố định hoặc preset VieNeu cố định;
  không clone giọng người ngoài. Kênh song ngữ dùng `voices[lang]` để tách
  giọng Anh/Việt; scene có thể tách `segments` theo ngôn ngữ.
- **CUDA:** OmniVoice chỉ chạy GPU; CPU chỉ dùng khi debug có chủ đích. VieNeu
  chạy ONNX CPU cho tiếng Việt.
- **Caption:** khung 3 dòng cố định, cắt thẳng giữa card, không scale/pop,
  không nhảy từng từ; từ đang đọc chỉ đổi màu.
- **SFX:** chỉ dùng khi có điểm nhấn thật; asset thật, không tự tổng hợp.
  **Whoosh bị cấm** ở mọi nơi (`config/sfx.json` → `banned`).
- **Nguồn:** `projects/` là nguồn sự thật; `out/` là sản phẩm sinh lại.
- **Duyệt:** không sinh audio/props từ script chưa duyệt. Phê duyệt và
  fact-check gắn với hash nội dung script (`paths.script_hash`); sửa script là
  phải duyệt lại. Chỉ bỏ qua bằng `--unapproved` khi chạy nháp.

## 6. Lệnh kiểm tra nhanh

```powershell
cd video; npx tsc --noEmit; cd ..
python -m pipeline.build --project-id ai-nho-tren-may --format short
python -m pipeline.render --project-id ai-nho-tren-may --format short --still 900 --scale 0.5
python -m compileall -q pipeline tools
```
