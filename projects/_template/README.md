# Mẫu dự án

Copy thư mục này thành `projects/<ten-du-an>/` rồi sửa:

1. `project.json` — `projectId` phải trùng tên thư mục, chọn `style`,
   `defaultFormat`; thêm `brand` nếu là kênh khác (xem `config/brands/`).
2. `research.md` — điền hoặc để pipeline research ghi.
3. `scripts/short.json` — để agent viết, hoặc tự tạo theo
   `schemas/script.schema.json`.

Cách nhanh hơn (pipeline tự tạo research + script):

```powershell
python -m pipeline.script --topic "Chủ đề" --format short `
    --project-id ten-du-an --style tech-explainer
```

Sau đó:

```powershell
python -m pipeline.make --project-id ten-du-an --format short
```

Quy tắc:

- `projects/` là nguồn sự thật; `out/` là output sinh lại được.
- Không sửa `out/<id>/01-script/`.
- `scripts/long.json` chỉ cần khi làm video long; short vẫn chạy độc lập.
- Xem `docs/ADDING.md` khi cần thêm style/scene/visual/SFX.
