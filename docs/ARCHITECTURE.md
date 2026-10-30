# Kiến trúc

Tài liệu này mô tả **ranh giới** giữa các phần của repo. Mục tiêu: thêm một
loại video, một khung hình, một template, một scene hay một visual mới mà không
phải sửa lan sang TTS, render hay các dự án cũ.

## 1. Hai vùng dữ liệu

| Vùng | Vai trò | Có được sửa? | Có thể xoá? |
|---|---|---|---|
| `projects/<id>/` | **Source**: research, kịch bản, style, review | Có | Không (hãy backup) |
| `out/<id>/` | **Output**: audio, caption, props, video, log | Không sửa tay | Có, render lại được |
| `references/<id>/` | Số đo từ video mẫu (`pipeline.analyze`) | Không sửa tay | Có, phân tích lại được |

```
projects/<id>/
  project.json          # style (= id template), aspect, defaultFormat, review.<fmt>
  research.md
  scripts/<format>.json
  review/factcheck-<format>.json

out/<id>/
  status.json
  01-script/            # snapshot + review-<format>.md
  02-audio/<format>/    # wav + manifest + sfx/            (dùng chung mọi aspect)
  03-captions/<format>/ # words.json                       (dùng chung mọi aspect)
  03-captions/<format>/<aspect>/   # srt, ass (chia card theo khung hình)
  04-props/<format>/<aspect>/props.json
  05-video/<format>-<aspect>.mp4
  99-logs/
```

`out/<id>/01-script/` chỉ là snapshot một chiều. Pipeline **không bao giờ**
đọc ngược từ snapshot. Mọi đường dẫn đi qua `pipeline/paths.py`.

## 2. Ba trục độc lập

Một video là tổ hợp của ba lựa chọn, mỗi lựa chọn nằm ở một nơi:

| Trục | Câu hỏi | Nơi định nghĩa | Ví dụ |
|---|---|---|---|
| **format** | Nội dung dài bao nhiêu, luật gì? | `config/formats.json` | `short`, `long` |
| **aspect** | Khung hình nào, cỡ chữ/vị trí thế nào? | `config/aspects.json` | `vertical`, `horizontal`, `square` |
| **template** | Trông như thế nào (màu, nền, phụ đề, chrome)? | `config/templates/<id>.json` | `tech-explainer`, `whiteboard`, bản sinh từ video mẫu |

Cùng một kịch bản render ở nhiều khung hình và nhiều template. Component Remotion
không bao giờ so sánh tên format hay aspect; chỉ đọc `useLayout()` và
`useTemplate()`.

Visual có thêm catalog `config/visuals.json`: kind hợp lệ, schema của
`visual.data`, giá trị mặc định.

`pipeline/config.py` là nơi duy nhất đọc các file config này. Module khác không
tự `json.loads`.

## 3. Luồng chạy

```
pipeline.script ──► projects/<id>/research.md + scripts/<format>.json
                         │
pipeline.review ─────────┼──► review/factcheck-<format>.json, project.json → review.<format>
                         │    (cổng duyệt: tts/build từ chối nếu chưa duyệt đúng hash)
pipeline.tts ────────────┼──► out/<id>/02-audio/<format>/
pipeline.align ──────────┼──► out/<id>/03-captions/<format>/words.json
pipeline.build ──────────┼──► out/<id>/04-props/<format>/<aspect>/props.json   (+ srt/ass)
pipeline.render ─────────┴──► out/<id>/05-video/<format>-<aspect>.mp4
```

- `pipeline.make` chạy tuần tự TTS → align → build → render; `--aspect a,b,c` lặp
  build + render cho nhiều khung hình mà không đọc lại giọng.
- `pipeline.build.compose()` là hàm thuần ghép props (không ghi file, không kiểm
  duyệt); `main()` ghi file. `pipeline.analyze compare` dùng lại `compose()` để thử
  một template lên project có sẵn.
- Hợp đồng Python ↔ Remotion là `props.json`; type nằm ở `video/src/lib/types.ts`.
  Props mang theo: `layout` (khối của aspect được chọn), `template` (đã gộp với
  `_base.json`), `brand` (đã áp màu/font của template), mỗi `scene.visual.data`
  (đã gộp default).

## 4. Code video

```
video/src/
  Root.tsx                     # đăng ký composition "DiveCode"
  compositions/ExplainerVideo.tsx   # <VideoProvider> + timeline, SFX, chrome, caption
  lib/
    types.ts                   # Props, Layout, Template (khớp config + schema)
    context.tsx                # VideoProvider, useLayout(), useTemplate()
    motion.ts                  # useEnter/useProgress đọc template.motion
    theme.ts  defaults.ts      # font, màu; props mặc định cho Remotion Studio
  scenes/
    shared.tsx                 # Layout (padding theo layout), Headline, Kicker...
    Hook Punch Stat List Timeline Compare Chart Outro  index.tsx (SceneRenderer)
  visuals/
    registry.tsx               # Visual + hasVisual, ràng buộc với config/visuals.json
    tech/*.tsx  stick/*.tsx  icons.tsx
  components/
    SceneBackground.tsx        # chọn nền theo template.background.kind
    Background.tsx PaperBackground.tsx
    Captions.tsx Watermark.tsx SceneIndex.tsx ProgressBar.tsx
video/stills.mjs  render.mjs  node-utils.mjs
```

### Quy ước

- **Scene** quyết định bố cục và nội dung một cảnh; kích thước lấy từ
  `useLayout().scenes.<loại>`. Scene không tự đọc file.
- **Visual** vẽ bằng code và nhận `visual.data`; không chứa nội dung riêng của
  video nào. Thêm/bớt kind: catalog + registry (`tsc` bắt lệch).
- **Template** chỉ quyết định giao diện; **layout** chỉ quyết định kích thước/vị trí;
  hai thứ này không lẫn vào nhau.
- **lib** là code thuần: type, context, motion hook, theme.

## 5. Pipeline Python

| Module | Trách nhiệm |
|---|---|
| `config.py` | Đọc `formats`, `aspects`, `templates`; gộp template; kiểm schema template |
| `paths.py` | Quy ước source/output, aspect, brand, snapshot, status, hash script |
| `script.py` | Gọi agent research/script, validate + repair, rồi fact-check |
| `review.py` | Báo cáo duyệt, kiểm link, fact-check, approve/reject, `require_approved` |
| `validate.py` | JSON Schema + luật ngữ nghĩa (kể cả `visual.data`, `claims`) |
| `visuals.py` | Catalog visual: kiểm `data`, gộp default |
| `tts.py`, `voice/` | Chọn giọng theo ngôn ngữ/segment, cache, chuẩn hoá âm lượng |
| `align.py` | faster-whisper từng segment → word timing (không phụ thuộc khung hình) |
| `captions.py` | Chia từ thành card theo `layout.caption`, ghi SRT/ASS |
| `sfx.py` | Copy asset thật theo catalog |
| `build.py` | `compose()` ghép props; `main()` ghi file |
| `render.py` | Gọi Remotion, đọc tiến trình |
| `analyze/` | Phân tích video mẫu → template (xem `docs/ANALYZE.md`) |
| `make.py` | Chạy cả chuỗi, nhiều aspect |

## 6. Bất biến cần giữ

- **Ảnh:** chỉ visual procedural; không ảnh AI/stock.
- **Giọng:** OmniVoice `clone` với mẫu cố định hoặc preset VieNeu cố định;
  không clone giọng người ngoài. Kênh song ngữ dùng `voices[lang]`.
- **CUDA:** OmniVoice chỉ chạy GPU; CPU chỉ dùng khi debug có chủ đích.
- **Caption:** khung cố định, cắt thẳng giữa card, không scale/pop, không nhảy
  từng từ; từ đang đọc chỉ đổi màu.
- **SFX:** chỉ dùng khi có điểm nhấn thật; asset thật. **Whoosh bị cấm**.
- **Nguồn:** `projects/` là nguồn sự thật; `out/` là sản phẩm sinh lại.
- **Duyệt:** không sinh audio/props từ script chưa duyệt. Phê duyệt và
  fact-check gắn với hash nội dung script (`paths.script_hash`); sửa script là
  phải duyệt lại. Chỉ bỏ qua bằng `--unapproved` khi chạy nháp.
- **Một nguồn sự thật cho số liệu bố cục:** không viết cứng cỡ chữ, bề rộng,
  vị trí trong component; thêm khoá vào `config/aspects.json`.
- **Một nguồn sự thật cho dữ liệu visual:** nội dung visual nằm ở
  `config/visuals.json` hoặc `visual.data`, không nằm trong component.

## 7. Lệnh kiểm tra

```powershell
python -m pytest
ruff check pipeline tools tests
cd video; npx tsc --noEmit; cd ..
```

CI (`.github/workflows/ci.yml`) chạy đúng ba lệnh này. Test không cần GPU, model
hay dữ liệu dự án thật: mọi thứ dựng trong thư mục tạm (`tests/conftest.py`).
`tsc` còn kiểm catalog visual khớp registry.
