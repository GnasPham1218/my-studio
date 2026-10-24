# my-studio — pipeline video tự động cho nhiều kênh (DiveCode1218, EnglishLearner1218)

Research → kịch bản → voiceover → phụ đề → render MP4. Chạy hoàn toàn local,
không API trả phí, không LLM local (việc viết do OpenCode agent đảm nhiệm).

## Kiến trúc

```
OpenCode agents            Python                      Remotion (Node)
─────────────────          ──────────────────────      ────────────────
researcher   ──┐           pipeline/script.py
scriptwriter ──┼─ projects/ ─► pipeline/tts.py  ──┐
shortener    ──┘   *.json    pipeline/align.py ──┼──► props.json ──► render.mjs
                             pipeline/build.py ──┘                   └─► MP4
```

- **Python điều phối toàn bộ.** Node/Remotion chỉ là worker render, gọi qua
  `node video/render.mjs <outDir> --props <props.json> --out <mp4>`.
- Hợp đồng giữa hai bên là `04-props/<format>/props.json` (type ở
  `video/src/lib/types.ts`). Remotion không chứa business logic.
- **`projects/` là source** (research, script, style, metadata); **`out/` là
  output** (audio, caption, props, video, log) và có thể xoá/render lại.
- Agent ghi kết quả **ra file** (đường dẫn trong prompt), Python đọc file — không
  parse JSON từ chat.
- Mọi đường dẫn do `pipeline/paths.py` quy định; không module nào tự ghép chuỗi.
- Style trình bày nằm ở `video/src/styles/`, scene ở `video/src/scenes/`, visual
  metaphor ở `video/src/visuals/`. Thêm loại video mới = thêm style/scene/visual,
  không sửa pipeline Python.

## Yêu cầu

| Thành phần | Ghi chú |
|---|---|
| Python **3.13** | `uv venv --python 3.13` (3.14 thiếu wheel `kaldi-native-fbank` cho win_amd64) |
| Node 20+ | Remotion 4 |
| GPU NVIDIA + CUDA | Cần cho OmniVoice; VieNeu chạy ONNX CPU cho tiếng Việt |
| Chrome hoặc Edge | Renderer tự dò; fallback nếu Chrome Headless Shell bị chặn |
| FFmpeg hệ thống | **Không bắt buộc** — Remotion tự mang ffmpeg để encode/mux |

## Cài đặt

```powershell
uv venv --python 3.13
uv pip install --python .\.venv\Scripts\python.exe -r requirements.txt

# torch bản CUDA (tự chọn đúng backend theo driver). Bản +cpu sẽ bị chặn.
uv pip install --python .\.venv\Scripts\python.exe --torch-backend=auto `
    --reinstall-package torch --reinstall-package torchaudio torch torchaudio

cd video; npm install; cd ..
```

## Quy trình

> **Hiện tại kênh chỉ sản xuất short dọc 9:16.** `pipeline.make` mặc định
> `--format short` (không cần truyền), và output chỉ có `02-audio/short`,
> `03-captions/short`, `04-props/short`, `05-video/short.mp4`. Format long vẫn
> dùng được khi cần bằng `--format long`.

### 1. Research + kịch bản (agent)

```powershell
# Video dài từ chủ đề mới
.\.venv\Scripts\python.exe -m pipeline.script --topic "..." --format long

# Short, dùng lại research đã có
.\.venv\Scripts\python.exe -m pipeline.script --topic "..." --format short `
    --project-id ai-nho-tren-may --skip-research

# Short cắt từ kịch bản dài (không research lại)
.\.venv\Scripts\python.exe -m pipeline.script --from-long --project-id ai-nho-tren-may
```

Kết quả: `projects/<projectId>/research.md` và
`projects/<projectId>/scripts/short.json`, `long.json`.
Kịch bản được validate bằng `schemas/script.schema.json` + luật trong
`config/formats.json`; nếu sai, pipeline tự gọi agent sửa (tối đa 2 lần).
`out/<projectId>/01-script/` chỉ là bản snapshot một chiều để đọc output.

Scene có số liệu nên khai `claims` (khẳng định + số thứ tự nguồn trong
`meta.sources`). Sau khi viết xong, `pipeline.script` tự gọi agent
`factchecker` và in báo cáo duyệt (bỏ qua bằng `--skip-factcheck`).

### 2. Duyệt nội dung (bắt buộc trước TTS)

```powershell
# Báo cáo: lỗi validate, số liệu chưa gắn nguồn, link nguồn chết, kết quả fact-check
python -m pipeline.review --project-id ai-nho-tren-may --format short

# Chạy (lại) agent fact-check sau khi sửa script
python -m pipeline.review --project-id ai-nho-tren-may --format short --factcheck

# Duyệt / từ chối
python -m pipeline.review --project-id ai-nho-tren-may --format short --approve --note "ok"
python -m pipeline.review --project-id ai-nho-tren-may --format short --reject --note "hook yếu"
```

- Báo cáo đầy đủ từng scene ở `out/<id>/01-script/review-<format>.md`; kết quả
  fact-check lưu ở `projects/<id>/review/factcheck-<format>.json`.
- Verdict: `ok`, `doubtful`, `wrong`, `unsupported`. Còn `wrong` thì không duyệt
  được (trừ `--force` khi đã kiểm tay). Chưa fact-check thì phải ghi rõ
  `--no-factcheck`.
- Phê duyệt gắn với **hash nội dung script** (lưu trong `project.json` →
  `review.<format>`). Sửa script sau khi duyệt thì `pipeline.tts`/`build` sẽ
  từ chối chạy cho tới khi duyệt lại.
- Chạy nháp không cần duyệt: thêm `--unapproved` vào `make`/`tts`/`build`/`render`.

### 3. TTS → phụ đề → render

```powershell
.\.venv\Scripts\python.exe -m pipeline.make --project-id ai-nho-tren-may --format short
```

Hoặc chạy từng bước (project có cả `short.json` và `long.json` thì luôn truyền
`--format`):

```powershell
python -m pipeline.tts   --project-id ai-nho-tren-may --format short
python -m pipeline.align --project-id ai-nho-tren-may --format short
python -m pipeline.build --project-id ai-nho-tren-may --format short
python -m pipeline.render --project-id ai-nho-tren-may --format short
```

Xem nhanh giao diện mà không render cả video:

```powershell
python -m pipeline.render --project-id ai-nho-tren-may --format short `
    --still 207 --scale 0.5
python -m pipeline.render --project-id ai-nho-tren-may --format short --preview 5
```

#### Thanh tiến trình

Mọi bước chạy lâu (TTS, align, render) đều có thanh tiến trình riêng, gồm
phần trăm, số scene/frame, thời gian đã chạy và thời gian còn lại:

```
▶ [4/4] Render
  Render · [████████████░░░░░░░░░░] ·  58.4% · 6720/11503 frame · đã 12:04 · còn 08:36
```

- Chạy trong terminal: thanh vẽ lại tại chỗ (`\r`), không spam log.
- Chạy nền / chuyển output vào file: mỗi 5 giây ghi một dòng, log vẫn đọc được.
- Khi chạy nền bằng PowerShell, thêm `-u` để Python không đệm output:

```powershell
.\.venv\Scripts\python.exe -u -m pipeline.make --project-id ai-nho-tren-may --format long
```

### 4. Engine TTS (OmniVoice + VieNeu)

Pipeline dùng hai engine local, không gọi API trả phí:

- **OmniVoice**: engine chính, chạy CUDA. Giọng được khoá bằng `mode=clone` với
  một mẫu do chính model sinh ra, nên không nhân bản giọng người ngoài.
- **VieNeu**: preset tiếng Việt, chạy ONNX trên CPU, xuất 48 kHz. Dùng khi kênh
  cần đọc tiếng Việt thật chuẩn mà không muốn phụ thuộc chất lượng tiếng Việt
  của OmniVoice.

#### Một giọng mặc định

`voice` là giọng mặc định, dùng cho scene không khai báo ngôn ngữ riêng. Cấu
hình nằm trong brand của project: `config/brand.json` (mặc định) hoặc
`config/brands/<id>.json` nếu project khai báo `"brand": "<id>"`:

```json
"voice": {
  "provider": "omnivoice",
  "omnivoice": {
    "mode": "clone",
    "refAudio": "assets/voice/omnivoice-nam.wav",
    "refText": "Xin chào, đây là kênh DiveCode1218. Hôm nay …",
    "language": "vi",
    "speed": 1.0,
    "numStep": 32
  }
}
```

`refText` phải khớp đúng câu đã đọc trong file mẫu, nếu không clone sẽ lệch.

> **Đừng dùng `mode=auto` cho video nhiều scene.** `auto` nghĩa là model tự bốc
> giọng cho **từng lần generate**, nên có scene ra giọng nam (~120 Hz), scene ra
> giọng nữ (~230 Hz) — nghe như nhiều người đọc xen kẽ.

#### Nhiều giọng theo ngôn ngữ

Brand có thể thêm `voices`, mỗi ngôn ngữ một cấu hình riêng. `voice` vẫn là
mặc định để tương thích brand cũ; nếu không có `voices[lang]`, pipeline fallback
về `voice`.

Ví dụ brand `EnglishLearner1218`: tiếng Anh dùng OmniVoice, tiếng Việt dùng
preset **Mai Anh** của VieNeu:

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

`pipeline.tts` chọn giọng theo ngôn ngữ của từng đoạn, nạp mỗi provider một
lần, chuẩn hoá loudness từng đoạn rồi ghép với khoảng lặng ngắn. Vì vậy một
video có thể có giọng Anh và giọng Việt khác nhau mà vẫn liền mạch.

#### Scene một ngôn ngữ

Thêm `language` vào scene để đổi giọng cho cả scene:

```json
{
  "id": "s01",
  "language": "vi",
  "narration": "Hôm nay học một mẹo nhỏ."
}
```

#### Scene trộn tiếng Việt và tiếng Anh

Dùng `segments` khi muốn đổi giọng ngay trong cùng một scene. `narration` vẫn
là bản gộp để đọc/fallback; validation và timing lấy theo `segments`:

```json
{
  "id": "s05",
  "narration": "Chữ h ở đây câm. An hour, the first sound is a vowel.",
  "segments": [
    {
      "language": "vi",
      "text": "Chữ h ở đây câm.",
      "pauseAfterMs": 180
    },
    {
      "language": "en",
      "text": "An hour, the first sound is a vowel."
    }
  ]
}
```

`pipeline.align` transcribe từng đoạn bằng đúng ngôn ngữ, cộng offset thời gian
rồi ghép word timing. Caption vì thế vẫn là một dòng thời gian liên tục, không
bị lệch khi đổi giọng.

#### Lệnh thường dùng

```powershell
# Sinh audio cho mọi scene (tự chọn giọng theo language/segments)
python -m pipeline.tts --project-id english-whiteboard-demo --format short

# Chỉ sinh lại vài scene sau khi sửa text
python -m pipeline.tts --project-id english-whiteboard-demo --format short --only s04,s05

# Can word timing + caption
python -m pipeline.align --project-id english-whiteboard-demo --format short --force

# Xem danh sách preset VieNeu
python -m pipeline.tts --list-voices --provider vieneu
```

`--voice`, `--mode`, `--ref-audio`, `--ref-text`, `--instruct` chỉ áp dụng cho
ngôn ngữ mặc định; giọng của ngôn ngữ khác phải lấy từ `brand.voices`.
`--speed` và `--num-step` áp dụng cho mọi giọng.

Cache audio gắn với `provider + fingerprint(spec) + text + pauseAfterMs` của
từng đoạn. Đổi giọng tiếng Việt chỉ làm mới các scene có đoạn tiếng Việt; scene
tiếng Anh vẫn dùng lại cache nếu không đổi.

| | OmniVoice | VieNeu |
|---|---|---|
| Giọng | `clone` với mẫu cố định (hoặc `auto`/`design`) | 25 preset |
| Backend | PyTorch + CUDA, bf16 | ONNX, không cần torch |
| Tốc độ GPU | RTF ~0.6-0.8, riêng lần đầu ~30 s warmup | không dùng GPU |
| Sample rate | 24 kHz (tự resample về 48 kHz) | 48 kHz |
| Bắt buộc | GPU NVIDIA + torch CUDA | CPU là đủ |

Provider **không fallback về CPU**: nếu torch không thấy CUDA, pipeline dừng
ngay với hướng dẫn cài. Chỉ khi debug mới đặt `OMNIVOICE_DEVICE=cpu`.

#### Đổi / roll giọng OmniVoice

```powershell
# Sinh 4 ứng viên (cùng một câu mẫu), in thời lượng + f0 để phân biệt nam/nữ
python tools/voice/make_voice_ref.py --candidates 4

# Nghe tools/voice/out/samples/voice-1.wav … rồi khoá giọng đã chọn
python tools/voice/make_voice_ref.py --lock tools/voice/out/samples/voice-2.wav --name nam

# Kiểm tra: f0 giữa các câu phải gần nhau (chính xác ~25 Hz)
python tools/voice/make_voice_ref.py --test
```

Với kênh khác, dùng `tools/voice/make_channel_voice.py` để sinh/khoá giọng
OmniVoice riêng. Với tiếng Việt, có thể dùng preset VieNeu cố định bằng
`voiceId`; preset không phải file nhân bản bên ngoài.

OmniVoice hay chèn khoảng lặng ~1 giây giữa các câu; provider tự rút các
khoảng lặng dài hơn 0.5 s xuống còn 0.35 s (`MAX_PAUSE_SEC` trong
`pipeline/voice/omnivoice_provider.py`), nhờ đó nhịp video không bị dài ra.

Model lấy từ **weights local** ở `models/omnivoice/` (khoảng 3.1 GB). Khi thư
mục đã có `config.json`, provider tự bật `HF_HUB_OFFLINE=1` nên không phát sinh
request nào tới Hugging Face. Chỉ khi chưa có weights local mới tải từ HF.

Đo trên máy này (RTX 3050 Laptop 4 GB): nạp model ~13 s, scene đầu (warmup) chậm
hơn, sau đó RTF ~0.4-0.6. Video long 6 phút tốn khoảng 3-4 phút cho khâu đọc.

## Cấu trúc dữ liệu

**Source** — giữ lâu dài, backup, chỉnh sửa trực tiếp:

```
projects/<projectId>/
  project.json                       # style, brand, format mặc định, metadata, review
  research.md                        # bước 1 — nghiên cứu
  scripts/
    short.json  long.json            # bước 1 — kịch bản nguồn
  review/
    factcheck-short.json             # bước 2 — kết quả fact-check (gắn hash script)
```

**Output** — sinh lại được, có thể xoá bất cứ lúc nào:

```
out/<projectId>/
  status.json                        # tiến độ/thống kê lần chạy gần nhất
  01-script/                         # snapshot một chiều từ projects/ (đừng sửa)
    research.md
    short.json  long.json
    review-short.md                  # báo cáo duyệt của pipeline.review
  02-audio/                          # bước 2 — voiceover
    short/  manifest.json  s01.wav …  sfx/tick.wav
    long/   manifest.json  s01.wav …
  03-captions/                       # bước 3 — căn thời gian + phụ đề
    short/  words.json  captions.srt  captions.ass
    long/   …
  04-props/                          # bước 4 — dữ liệu cho Remotion
    short/  props.json
    long/   props.json
  05-video/                          # bước 5 — sản phẩm cuối
    short.mp4  long.mp4
  99-logs/                           # log/ảnh debug, xoá được
    brief.txt  repair.txt  invalid.json
    attempts/  stills/
```

> Quy tắc: sửa nội dung trong `projects/`, không sửa `out/01-script/`. Muốn đổi
> style của một dự án, sửa `style` trong `projects/<projectId>/project.json`
> (ví dụ `tech-explainer`). Tên thư mục đánh số theo đúng thứ tự chạy; mỗi
> format nằm riêng trong bước của nó.

## Thành phần

| File / thư mục | Vai trò |
|---|---|
| `projects/<id>/project.json` | Source metadata: `style`, `brand`, `defaultFormat`, `formats` |
| `projects/_template/` | Mẫu tối thiểu để tạo dự án mới |
| `schemas/script.schema.json` | Hợp đồng JSON của kịch bản (2 format) |
| `config/formats.json` | Kích thước, safe area, giới hạn scene/từ/giây |
| `config/brand.json` | Brand mặc định (DiveCode1218): tên kênh, màu, font, giọng, CTA |
| `config/brands/<id>.json` | Brand cho kênh khác; project chọn bằng `"brand": "<id>"` |
| `config/sfx.json` | Danh mục SFX, volume mặc định, policy (whoosh bị cấm) |
| `pipeline/paths.py` | Nguồn duy nhất quy định `projects/` (source) vs `out/` (output), snapshot, status |
| `pipeline/llm.py` | Bọc `opencode run --format json` |
| `pipeline/validate.py` | JSON Schema + luật ngữ nghĩa |
| `pipeline/script.py` | Research → script → repair loop → fact-check |
| `pipeline/review.py` | Báo cáo duyệt, kiểm link nguồn, fact-check, approve/reject, cổng chặn trước TTS/build |
| `.opencode/agents/factchecker.md` | Agent kiểm chứng từng khẳng định, ghi `review/factcheck-<fmt>.json` |
| `pipeline/tts.py` | Orchestrate TTS, cache, chuẩn hoá âm lượng, resample |
| `pipeline/voice/` | Adapter engine: `omnivoice` (torch + CUDA, 24 kHz), `vieneu` (ONNX 48 kHz) |
| `tools/voice/make_voice_ref.py` | Sinh ứng viên giọng OmniVoice, khoá giọng (`--lock`), kiểm tra f0 (`--test`) |
| `tools/voice/make_channel_voice.py` | Sinh/khoá giọng riêng cho từng brand/kênh |
| `tools/voice/` | Công cụ dev cho giọng đọc (không thuộc pipeline chính) |
| `pipeline/align.py` | faster-whisper → word timing → SRT/ASS |
| `pipeline/build.py` | Ghép timeline thật từ audio → props.json, copy SFX, đọc `style` + `brand` |
| `pipeline/sfx.py` | Copy SFX thật theo `config/sfx.json` từ `assets/sfx/` (Mixkit free license) |
| `pipeline/render.py` | Gọi Node renderer, đọc tiến trình và vẽ thanh |
| `pipeline/progress.py` | Thanh tiến trình dùng chung (%, ETA, tự ASCII khi ghi file) |
| `pipeline/make.py` | Chạy TTS → align → build → render |
| `video/src/scenes/` | Mỗi file một template cảnh + `shared.tsx` (grid, headline, divider) |
| `video/src/scenes/index.tsx` | `SceneRenderer` — ánh xạ `scene.type` → component |
| `video/src/visuals/` | Visual metaphor vẽ bằng code; `tech/` và `stick/` chứa từng metaphor |
| `video/src/visuals/stick/StickFigure.tsx` | Nhân vật que + bong bóng thoại cho bài giảng |
| `video/src/visuals/index.tsx` | `Visual` dispatcher + `hasVisual` |
| `video/src/lib/` | `types.ts`, `theme.ts`, `motion.ts`, `defaults.ts` dùng chung |
| `video/src/styles/` | Registry style; `tech-explainer` (tối) và `whiteboard` (giấy sáng) |
| `video/src/compositions/ExplainerVideo.tsx` | Timeline scene, caption, SFX, style, watermark |
| `video/src/components/Captions.tsx` | Phụ đề khung cố định, cắt thẳng giữa card, không pop/nhảy từng từ |
| `video/src/components/Background.tsx` | Nền tối: gradient + lưới mờ + quầng sáng "thở" chậm |
| `video/src/components/PaperBackground.tsx` | Nền giấy cho whiteboard: dòng kẻ nhẹ + lề đỏ |
| `video/src/components/SceneIndex.tsx` | Số scene `01 / 13` + thanh tiến độ ở góc trên trái |
| `.opencode/agents/motion-sfx.md` | Subagent thiết kế animation + chọn thời điểm SFX khớp điểm nhấn |
| `docs/ARCHITECTURE.md` | Ranh giới source/output, luồng dữ liệu, quy ước mở rộng |
| `docs/ADDING.md` | Công thức thêm project/style/scene/visual/SFX |

## Ghi chú thiết kế

- **Whiteboard Lesson:** style `whiteboard` dùng nền giấy sáng, chữ marker
  (Patrick Hand), caption thẻ giấy. Nhân vật que nằm ở `visual.kind: "stick"`,
  có bong bóng thoại (`label`), ghi chú (`sub`) và pose
  `wave/point/think/write/cheer`. Brand mẫu: `config/brands/english-learner-1218.json`;
  demo có giọng: `projects/english-whiteboard-demo/`. Mỗi kênh dùng brand và
  voice riêng; EnglishLearner1218 dùng giọng Anh OmniVoice trong
  `assets/voice/omnivoice-englishlearner.wav` và giọng Việt VieNeu `Mai Anh`
  trong `voices.vi`.
- **Tech Explainer (hướng đã chọn):** mỗi cảnh punch/stat có một visual metaphor
  vẽ bằng code, đặt ngay dưới headline — điện thoại + chip, thẻ MIT, vòng lặp
  2018→2025, thanh nén mô hình, line chart, thanh dung lượng, meter giới hạn,
  hai panel máy/cloud. Motion nhẹ: line draw, bar grow, count-up, pulse.
- **Caption không nhảy:** khung 3 dòng cố định, căn đáy; đổi card bằng cắt thẳng
  tại ranh giới thời gian, không fade về 0 nên không nháy và không chồng chữ.
  Không scale/pop, không dịch từng từ. Từ đang đọc chỉ đổi màu.
- **Một grid dùng chung** cho mọi scene: header ~13 %, vùng visual 25–70 %,
  caption 78–88 %. Chuyển động vào cảnh là opacity + 14 px rise (0,5 s).
- **SFX tối giản, đặt theo điểm nhấn:** whoosh đã bỏ. Chỉ còn tick, đặt khi số
  liệu chốt hoặc một item khớp vào vị trí — không đặt ở mọi lần cắt cảnh. Danh
  mục nằm ở `config/sfx.json`; mỗi scene khai báo `sfx`, `sfxAtSec` (giây tính
  từ đầu scene) và `sfxVolume` nếu cần. Asset thật ở `assets/sfx/` (Mixkit Free
  License, xem `assets/sfx/SOURCES.md`); build copy sang
  `02-audio/<format>/sfx/`, render không cần mạng.
- **Subagent `motion-sfx`:** chuyên thiết kế animation Remotion và chọn thời
  điểm SFX khớp với điểm nhấn thị giác. Định nghĩa ở
  `.opencode/agents/motion-sfx.md`; đọc `config/sfx.json` trước khi thêm SFX.
  Cách gọi: “Dùng subagent motion-sfx để thêm animation cho scene s07 và đặt
  tick đúng lúc số 69% chốt.”
- **`visual.kind`:** các kind explainer gồm `phone`, `award`, `loop`, `shrink`,
  `decline`, `storage`, `limits`, `question`; whiteboard dùng `stick`;
  `generated`/`chart`/`none` không kích hoạt visual explainer.
- **Giọng đọc** lấy từ `voice` mặc định và `voices[lang]` trong brand
  (`provider` + khối riêng của provider). Scene có thể chọn bằng `language`
  hoặc tách `segments` để trộn tiếng Việt/Anh trong cùng scene. Có thể ghi đè
  giọng mặc định bằng `--provider` / `--voice` / `--mode`. Danh sách 25 giọng
  VieNeu: `python tools/voice/test_vieneu.py --all`.
- **Kiểm tra nhanh 1 engine** mà không đụng project:
  `python tools/voice/check_providers.py --provider omnivoice --mode clone --out tools/voice/out/check.wav`.
- **`voice`/`music` trong kịch bản bị xoá** — đây là cấu hình runtime, không
  phải nội dung; pipeline gắn từ brand config.
- **Tốc độ nói thực tế ~3.1 từ/giây** (đã hiệu chỉnh trong
  `config/formats.json`), nên kịch bản 168 từ ≈ 55 s thoại.
- **Thêm loại video mới:** xem `docs/ADDING.md`; không cần sửa `pipeline/` nếu
  chỉ thay cách trình bày. Nếu cần format/aspect ratio mới, thêm vào
  `config/formats.json` + composition tương ứng.
