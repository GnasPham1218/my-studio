# Scripts

- `short.json` — bản 9:16, do agent `scriptwriter` (hoặc `shortener`) tạo.
- `long.json` — bản dài, chỉ cần khi sản xuất format long.

Không sửa trực tiếp bằng tay nếu có thể dùng pipeline, vì pipeline sẽ validate
bằng `schemas/script.schema.json` + `config/formats.json` và tự gọi agent sửa.

Lệnh tạo:

```powershell
# Research + script mới
python -m pipeline.script --topic "Chủ đề" --format short --project-id ten-du-an

# Cắt short từ long đã có
python -m pipeline.script --from-long --project-id ten-du-an
```
