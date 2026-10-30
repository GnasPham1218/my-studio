# Phân tích video mẫu → template

Gửi một video có giao diện bạn thích, pipeline đo các đặc điểm giao diện và sinh
một **template** (`config/templates/<id>.json`). Template áp lên mọi project có sẵn
mà không sửa nội dung.

```powershell
# Cài một lần (OCR, ~50 MB, chạy CPU, không cần mạng khi chạy)
uv pip install --python .venv\Scripts\python.exe -r requirements-analyze.txt

# 1. Phân tích: ghi số đo + contact sheet + template
python -m pipeline.analyze run D:\video\mau.mp4 --id kenh-abc

# 2. Áp template lên project có sẵn (không sửa project.json)
python -m pipeline.make --project-id ai-nho-tren-may --template kenh-abc --still 300

# 3. Kiểm tra độ giống bằng số đo, không phải bằng mắt
python -m pipeline.analyze compare --id kenh-abc --project-id ai-nho-tren-may
```

Muốn project dùng template lâu dài: đặt `"style": "kenh-abc"` trong
`projects/<id>/project.json`.

## Đo được gì, đo thế nào

| Đại lượng | Cách đo | Vào template |
|---|---|---|
| Khung hình, fps, thời lượng | PyAV | `source`, chọn aspect gần nhất |
| Nhịp dựng (cảnh/phút) | Chênh lệch giữa các frame, tách đỉnh cắt cảnh khỏi chuyển động trong cảnh bằng Otsu | `pacing` |
| Màu nền, kiểu nền | Trung vị lưới 3×3 + khớp mặt phẳng độ sáng: phẳng → `solid`, tuyến tính → `gradient`, quầng sáng → `tech` | `background` |
| Bảng màu | Màu nét chữ (OCR) + pixel rực + k-means toàn khung | `colors` |
| Phụ đề: vị trí, cỡ, độ rộng | OCR, dải chữ căn giữa vừa hiện lâu vừa đổi nội dung | `caption.bottomRel`, `fontSizeRel`, `maxWidthRel` |
| Phụ đề: màu chữ, màu từ nhấn, viền, thẻ nền, scrim | Phân cụm màu trong khối chữ, so màu hai bên chữ | `caption.*` |
| Watermark, số scene `03 / 13` | Chữ cố định ≥ 60% số frame | `chrome` |
| Độ ồn, nhạc nền | RMS theo khung 50 ms, sàn nhiễu | `audio` (chỉ tham khảo) |

Độ chính xác khi tự phân tích video do chính pipeline render (đã biết đáp án):
đáy phụ đề 0,1562 → đo 0,156; cỡ chữ 0,0481 → 0,0493; cắt cảnh 12/12 (sai số
≤ 0,02 s); watermark và số scene phát hiện đúng; màu trong ΔE < 5.

## Không đo được, cần bạn hoặc agent

Template không phải bản sao điểm ảnh. Những thứ **không** được sao chép:

- **Font**: không nhận diện từ ảnh. Dùng font của brand; muốn đổi, điền
  `fonts` trong template (xem `python -m pipeline.analyze fonts`).
- **Bố cục từng scene** (cỡ headline, vị trí visual): lấy từ `config/aspects.json`.
  Template chỉ điều khiển màu, nền, phụ đề, chrome, chuyển động.
- **Đồ hoạ riêng** (icon, nhân vật, hiệu ứng): không có component tương ứng. Cần
  thêm visual (xem `docs/ADDING.md` mục 4).
- **Vị trí watermark/số scene**: cố định theo layout; nếu video mẫu đặt ở phía
  khác, báo cáo sẽ ghi chú.
- **Nền**: chỉ có `tech`, `paper`, `solid`, `gradient`. Nền ảnh/video không dựng lại được.

Phần cuối lệnh `run` liệt kê đúng những điểm cần xem lại cho video đó.

### Tinh chỉnh bằng agent nhìn ảnh

`references/<id>/contact_sheet.png` là lưới frame của video mẫu;
`references/<id>/compare/compare_sheet.png` đặt video mẫu (hàng trên) cạnh
template đang render (hàng dưới). Agent `template-analyst`
(`.opencode/agents/template-analyst.md`) đọc hai ảnh này cùng `analysis.json`,
chỉ được sửa `config/templates/<id>.json` ở các khoá không đo được (font, kiểu
nền, độ đậm chữ, viền thẻ, chuyển động). Nếu bạn dùng Claude Code, chỉ cần đưa
hai ảnh này vào cuộc trò chuyện và yêu cầu chỉnh template.

## Độ giống (compare)

`compare` không so từng pixel (nội dung hai video khác nhau). Nó render project
mẫu bằng template, chạy **cùng bộ đo** trên các frame vừa render, rồi so từng đại
lượng với video gốc và cho điểm 0-100:

| Đại lượng | Dung sai |
|---|---|
| màu bg / fg / primary | ΔE ≤ 14 |
| loại nền | cùng loại |
| đáy phụ đề | ± 0,02 chiều cao |
| cỡ chữ phụ đề | ± 15% |
| bề rộng phụ đề | ± 0,12 (phụ thuộc độ dài câu) |
| màu từ nhấn, viền, thẻ nền | cùng có/không |
| số scene, watermark | cùng có/không |

Màu nhấn thứ hai chỉ tính khi cả hai bên đều thấy một màu rực đủ sáng (màu này
chỉ hiện ở vài scene nên ít frame mẫu sẽ không bắt được).

## Sửa quy tắc suy luận mà không đọc lại video

`analysis.json` lưu số đo, kể cả nguyên liệu chọn bảng màu và toàn bộ box OCR.
Sau khi sửa `pipeline/analyze/infer.py` hoặc `frames.pick_palette`:

```powershell
python -m pipeline.analyze infer --id kenh-abc --force
```

## Cấu trúc code

```
pipeline/analyze/
  media.py     PyAV: probe, quét video (chênh lệch frame + ảnh mẫu), đọc audio
  colors.py    Phép màu thuần (hex, ΔE Lab, độ sáng, độ rực)
  frames.py    Cắt cảnh, nền (solid/gradient/glow), bảng màu     ← thuần numpy
  text.py      OCR → TextBox; tìm phụ đề, chrome, màu chữ        ← logic thuần, OCR tách riêng
  audio.py     Độ ồn, nhạc nền
  measure.py   Ghép các bước trên thành một dict số đo (dùng cho cả video mẫu lẫn ảnh render)
  infer.py     Số đo → template (đã kiểm schema)
  compare.py   Render project mẫu bằng template, đo lại, so sánh
  store.py     references/<id>/: analysis.json, contact sheet
  cli.py       run | infer | show | compare | fonts
```

Mỗi tầng chỉ nhận/trả dữ liệu thuần nên test được bằng ảnh PIL tự vẽ và box
OCR giả (`tests/test_analyze_*.py`), không cần video hay OCR.

Thêm một đại lượng đo mới: (1) hàm thuần trong `frames.py`/`text.py` kèm test,
(2) ghi vào dict ở `measure.py`, (3) ánh xạ sang khoá template trong `infer.py`,
(4) thêm vào `compare_measures` nếu muốn kiểm tra vòng khứ hồi, (5) nếu cần khoá
template mới thì thêm vào `schemas/template.schema.json` + `video/src/lib/types.ts`
và dùng trong component Remotion.
