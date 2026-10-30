# Hướng dẫn sử dụng

Tài liệu này dành cho người **làm video**: từ một chủ đề tới video MP4,
thumbnail và dự án CapCut mở lên là chỉnh tiếp được. Phần kỹ thuật (kiến trúc,
thêm scene/visual mới) xem [README](../README.md) và [ADDING](ADDING.md).

Mọi lệnh chạy từ thư mục gốc repo, trong PowerShell. Nếu dùng virtualenv, thay
`python` bằng `.\.venv\Scripts\python.exe`.

---

## 1. Cài đặt một lần

Cần có: Python 3.13, Node 20+, Chrome hoặc Edge, GPU NVIDIA (cho giọng
OmniVoice). CapCut desktop là tuỳ chọn (để chỉnh tiếp video).

```powershell
uv venv --python 3.13
uv pip install --python .\.venv\Scripts\python.exe -r requirements.txt
cd video; npm install; cd ..
```

Chi tiết torch/CUDA và giọng đọc: xem mục *Cài đặt* trong [README](../README.md).

---

## 2. Làm một video từ đầu

### Bước 1. Viết kịch bản

```powershell
python -m pipeline.script --topic "Vì sao AI đang quay về máy của bạn" --format short
```

Bước này (và fact-check ở bước 2) cần AI. Có **hai chế độ**, chọn một:

| Chế độ | Cần cài | Cách chọn |
|---|---|---|
| **OpenCode** (mặc định) | `opencode` | không cần làm gì, hoặc `--llm opencode` |
| **Claude** | Claude Code (`claude`), đã đăng nhập | thêm `--llm claude` |

```powershell
python -m pipeline.script --topic "..." --format short --llm claude
python -m pipeline.script --topic "..." --format short --llm claude --model opus
python -m pipeline.review --project-id <id> --format short --factcheck --llm claude
```

Muốn lúc nào cũng dùng Claude mà không gõ `--llm`, đặt biến môi trường một
lần (mở terminal mới để có hiệu lực):

```powershell
[Environment]::SetEnvironmentVariable("MY_STUDIO_LLM", "claude", "User")
```

Hai chế độ dùng **chung** các agent trong `.opencode/agents/` (cùng prompt,
cùng quyền): agent chỉ được đọc web và chỉ ghi vào `projects/`, không chạy lệnh.
`--model` với OpenCode là `provider/model`, với Claude là `sonnet`, `opus`,
`haiku` hoặc id model.

Agent tự research và viết kịch bản vào `projects/<id>/scripts/short.json`.
`<id>` in ra cuối lệnh (ví dụ `ai-nho-tren-may`). Muốn sửa câu chữ thì sửa
thẳng file này.

### Bước 2. Duyệt nội dung (bắt buộc)

**Cách dễ nhất: giao diện duyệt.**

```powershell
python -m pipeline.ui
```

Trình duyệt mở `http://127.0.0.1:8765` (chỉ chạy trên máy bạn):

Làm theo 3 bước, hiện ở đầu trang:

1. **Đọc kịch bản & nguồn**
   - Giữa: lời đọc của từng cảnh, sửa trực tiếp được. Dưới mỗi cảnh: lỗi (đỏ),
     số liệu chưa gắn nguồn (vàng), các khẳng định kèm số nguồn `[n]` và kết quả
     fact-check.
   - Phải: **nguồn tham khảo** (tên, link, ngày truy cập, cảnh nào trích dẫn),
     nút **Kiểm tra link**, các **giả định**, và **research.md** (ghi chép
     nghiên cứu agent đã làm).
   - **Lưu** → **Fact-check** (tuỳ chọn) → sang bước 2.
2. **Duyệt…** (hoặc **Từ chối…** kèm lý do). Sửa kịch bản sau khi duyệt thì
   phải duyệt lại.
3. **Animation & tạo video**: chỉ mở sau khi đã duyệt.
   - Mỗi cảnh có **mô tả chuyển động** theo thứ tự xảy ra: chuyển cảnh vào,
     nền, phần tử nào hiện lúc nào (giây), hình minh hoạ chuyển động ra sao,
     âm thanh, phụ đề.
   - Ô **Ghi chú / yêu cầu chỉnh animation** cho từng cảnh → **Lưu ghi chú
     animation**. Ghi chú lưu riêng ở `projects/<id>/review/animation-<format>.json`
     (không sửa kịch bản nên không mất phê duyệt); agent `motion-sfx` đọc file
     này khi được nhờ chỉnh animation.
   - Bên phải: xem trước animation (không có giọng đọc, thời lượng ước tính),
     **▶ Xem cảnh** để nhảy tới cảnh. Ổn thì **Tạo video** (chạy `pipeline.make`,
     tuỳ chọn kèm dự án CapCut, log hiện ngay bên dưới).

Server cũng chặn dựng animation khi kịch bản chưa được duyệt, không chỉ ẩn nút.

Fact-check từ giao diện dùng chế độ AI đang chọn: `python -m pipeline.ui --llm claude`.

Hoặc dùng dòng lệnh:

```powershell
python -m pipeline.review --project-id ai-nho-tren-may --format short
python -m pipeline.review --project-id ai-nho-tren-may --format short --approve --note "ok"
```

Đọc báo cáo ở `out/<id>/01-script/review-short.md`. Sửa kịch bản sau khi duyệt
thì phải duyệt lại.

### Bước 3. Đọc giọng, phụ đề, render video + thumbnail

```powershell
python -m pipeline.make --project-id ai-nho-tren-may --format short
```

Thêm `--capcut` để tạo luôn dự án CapCut (xem mục 4):

```powershell
python -m pipeline.make --project-id ai-nho-tren-may --format short --capcut
```

Kết quả nằm trong `out/<id>/05-video/`:

| File | Là gì |
|---|---|
| `short-vertical.mp4` | Video hoàn chỉnh (giọng, phụ đề, chuyển cảnh, SFX) |
| `short-vertical.thumbnail.jpg` | Ảnh bìa cùng khung hình với video |

Muốn cả bản dọc và ngang từ cùng một giọng đọc:
`--aspect vertical,horizontal`.

---

## 3. Thumbnail

`pipeline.make` tự tạo thumbnail sau mỗi video. Chỉ render lại thumbnail:

```powershell
python -m pipeline.render --project-id ai-nho-tren-may --format short --thumbnail
```

Đổi chữ trên thumbnail trong `projects/<id>/project.json` (không phải kịch
bản, nên sửa không làm mất phê duyệt):

```json
"thumbnail": {
  "text": "Vì sao AI đang quay về máy của bạn?",
  "emphasis": ["AI", "máy"],
  "kicker": "AI trên máy"
}
```

- `text`: tiêu đề lớn. Bỏ trống thì dùng `title` của project.
- `emphasis`: các từ tô màu nhấn.
- `kicker`: nhãn nhỏ phía trên. Bỏ trống thì dùng kicker của cảnh mở đầu.

Hình minh hoạ lấy từ visual của cảnh đầu tiên. Sửa `project.json` xong thì
chạy lại `pipeline.build` (hoặc `pipeline.make`) trước khi render thumbnail.

---

## 4. Mở và chỉnh tiếp trong CapCut

```powershell
python -m pipeline.capcut --project-id ai-nho-tren-may --format short --aspect vertical
```

Mở CapCut desktop (khởi động lại nếu đang mở), dự án
`ai-nho-tren-may-short-vertical` có sẵn trong danh sách:

- track video: mỗi cảnh một clip, không chữ, không chuyển cảnh, để bạn tự thêm
  hiệu ứng của CapCut;
- track giọng đọc từng cảnh và track SFX, đặt đúng thời điểm;
- phụ đề chạy chữ: tối đa 3 chữ một lần, chữ đang đọc đổi màu, luôn một dòng.

Các file gốc nằm ở `out/<id>/06-capcut/short-vertical/` (clip, `audio.wav`,
`captions.srt`, `thumbnail.jpg`). Dự án CapCut trỏ thẳng vào các file này, **đừng
xoá thư mục đó** khi còn dùng dự án.

Chạy lại lệnh sẽ ghi đè dự án CapCut cùng tên (chỉ dự án do pipeline tạo). Muốn
giữ bản đang chỉnh, thêm `--name <tên-mới>`.

### Đổi kiểu phụ đề trong CapCut

Kiểu phụ đề lưu ở `config/capcut/caption-style.json`, học từ chính CapCut:

| Muốn đổi | Cách làm |
|---|---|
| Màu, font | Chỉnh một câu phụ đề trong CapCut, **đóng CapCut**, rồi chạy `python -m pipeline.capcut --learn-look "<tên dự án>"` |
| Kiểu chữ chạy | Sửa `wordHighlight` trong `caption-style.json`: `wordsPerPage` (số chữ mỗi lần), `size`, `stroke` (viền), `base` (màu chữ chưa đọc), `mode` (`current`: chỉ tô chữ đang đọc, `spoken`: tô dồn) |
| Dùng caption template của CapCut | Áp template cho một câu, đóng CapCut, chạy `--learn-style "<tên dự án>"`. Lưu ý: nhiều template tự xuống dòng và có hiệu ứng mờ |
| Quay về phụ đề thường | `--learn-style "<tên dự án>" --plain` |

---

## 5. Đổi giao diện video

| Muốn đổi | Ở đâu |
|---|---|
| Giao diện (nền, chữ, phụ đề) | `style` trong `projects/<id>/project.json`, chọn một file trong `config/templates/` |
| Chuyển cảnh | Khối `transition` trong template: `kind` = `fade`, `slide`, `push`, `wipe`, `zoom`, `blur`, `none`; `sec` = độ dài; `byType` = riêng cho từng loại cảnh |
| Màu, font, tên kênh | `config/brand.json` (hoặc `config/brands/<id>.json`) |
| Khung hình | `--aspect vertical`, `horizontal`, `square` |

Xem trước giao diện mà không render cả video:

```powershell
cd video; npm run studio      # mở Remotion Studio
python -m pipeline.render --project-id ai-nho-tren-may --format short --preview 5
```

---

## 6. Sự cố thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| Render báo *not a valid Remotion project* | Remotion Studio đang chiếm cổng 3000. Tắt Studio hoặc chạy Studio ở cổng khác (`.claude/launch.json` dùng 3005) |
| CapCut crash khi mở dự án | CapCut vừa cập nhật và đổi định dạng. Tạo một dự án trống trong CapCut, kéo vào 1 clip + 1 file âm thanh, đóng lại, rồi báo để trích lại khuôn trong `config/capcut/` |
| Không thấy dự án trong CapCut | Khởi động lại CapCut. Thư mục draft mặc định ở `%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft`; đặt biến `CAPCUT_DRAFTS` nếu cài chỗ khác |
| Phụ đề CapCut bị 2 dòng | Giảm `wordsPerPage` hoặc `size` trong `wordHighlight` |
| TTS/build báo chưa duyệt | Chạy lại bước duyệt (mục 2), hoặc thêm `--unapproved` để chạy nháp |

---

## 7. Lưu ý về Git

`out/` (video, thumbnail, audio, bộ file CapCut) **không** được đưa lên Git:
đây là output sinh lại được. Chỉ commit code, cấu hình và `projects/`.
