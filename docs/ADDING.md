# Thêm tính năng

Mỗi mục dưới đây là một “đường mở rộng” độc lập. Làm xong nhớ chạy checklist ở
cuối trang.

## 1. Tạo dự án video mới

```powershell
# Cách nhanh: để pipeline tạo research + script
python -m pipeline.script --topic "Chủ đề" --format short --style tech-explainer

# Hoặc copy template rồi tự điền
Copy-Item -Recurse projects/_template projects/<ten-du-an>
```

`projects/<ten-du-an>/project.json`:

```json
{
  "schemaVersion": 1,
  "projectId": "ten-du-an",
  "title": "Tiêu đề video",
  "topic": "Chủ đề",
  "language": "vi",
  "style": "tech-explainer",
  "defaultFormat": "short",
  "formats": ["short"]
}
```

`brand` là tùy chọn. Bỏ trống = dùng `config/brand.json` (DiveCode1218).
Kênh khác đặt `"brand": "english-learner-1218"` và tạo
`config/brands/english-learner-1218.json`.

Sau khi có `scripts/short.json`, chạy:

```powershell
python -m pipeline.make --project-id <ten-du-an> --format short
```

**Không sửa** `out/<ten-du-an>/01-script/`; đó là snapshot.

### Kịch bản song ngữ (nhiều giọng)

Kênh dạy tiếng Anh có thể dùng hai giọng: một giọng Anh và một giọng Việt.
Khai báo giọng theo ngôn ngữ trong brand:

```json
"voice": { "provider": "omnivoice", "omnivoice": { "...": "giọng Anh mặc định" } },
"voices": {
  "vi": { "provider": "vieneu", "vieneu": { "voiceId": "Mai Anh" } }
}
```

Trong script, scene có thể chọn một ngôn ngữ cho cả scene:

```json
{ "id": "s01", "language": "vi", "narration": "Hôm nay học một mẹo nhỏ." }
```

Hoặc tách `segments` để trộn tiếng Việt/Anh trong cùng scene. `narration` là bản
gộp để đọc/fallback; validation, TTS và align lấy theo `segments`:

```json
{
  "id": "s05",
  "narration": "Chữ h ở đây câm. An hour, the first sound is a vowel.",
  "segments": [
    { "language": "vi", "text": "Chữ h ở đây câm.", "pauseAfterMs": 180 },
    { "language": "en", "text": "An hour, the first sound is a vowel." }
  ]
}
```

Sau khi sửa text, chỉ cần sinh lại scene bị đổi:

```powershell
python -m pipeline.tts --project-id english-whiteboard-demo --format short --only s04,s05
python -m pipeline.align --project-id english-whiteboard-demo --format short --force
```

## 2. Thêm template (giao diện)

Template là dữ liệu JSON, không phải code. Có hai cách tạo:

**Từ video mẫu** (khuyến nghị): `python -m pipeline.analyze run <video> --id <id>`
(xem `docs/ANALYZE.md`).

**Viết tay**: tạo `config/templates/<id>.json`, chỉ khai báo phần khác
`config/templates/_base.json`:

```json
{
  "schemaVersion": 1,
  "id": "minimal",
  "label": "Minimal",
  "colors": { "bg": "#FFFFFF", "fg": "#111111", "primary": "#2563EB" },
  "background": { "kind": "solid" },
  "caption": { "textShadow": false, "scrim": [] },
  "chrome": { "sceneIndex": false, "progress": true }
}
```

Khoá hợp lệ nằm ở `schemas/template.schema.json` (sai khoá hoặc sai kiểu thì
`pipeline.build` dừng và nói rõ chỗ sai). Đặt `"style": "minimal"` trong
`projects/<id>/project.json`, hoặc thử nhanh với `--template minimal` ở
`build`/`render`/`make`.

Template **chỉ** điều khiển giao diện (màu, font, nền, phụ đề, chrome, chuyển
động). Bố cục và cỡ chữ theo khung hình nằm ở `config/aspects.json`; nội dung
nằm trong `projects/`. Thêm một thuộc tính giao diện mới: thêm vào schema,
`config/templates/_base.json` (giá trị mặc định), type `Template` trong
`video/src/lib/types.ts`, rồi dùng trong component qua `useTemplate()`.

## 3. Thêm scene type

Ví dụ thêm `demo`:

1. Thêm `"demo"` vào `enum` của `scene.type` trong
   `schemas/script.schema.json`, và vào `sceneTypes` của format cần dùng
   trong `config/formats.json`.
2. Nếu có luật riêng (số từ, field bắt buộc), thêm vào `pipeline/validate.py`
   kèm test trong `tests/test_validate.py`.
3. Nếu scene cần cỡ chữ/độ rộng riêng, thêm khối `scenes.demo` vào **mọi**
   khung hình trong `config/aspects.json` và type `Layout` ở
   `video/src/lib/types.ts` (test `test_all_aspects_share_the_same_structure`
   sẽ báo nếu thiếu).
4. Tạo `video/src/scenes/Demo.tsx`, lấy kích thước từ layout, không so sánh
   tên format:

```tsx
import React from "react";
import type { SceneProps } from "./shared";
import { Headline, Layout } from "./shared";
import { useLayout } from "../lib/context";

export const Demo: React.FC<SceneProps> = ({ scene, brand }) => {
  const t = useLayout().scenes.demo;
  return (
    <Layout>
      <Headline text={scene.onScreenText ?? ""} brand={brand} size={t.headline} />
    </Layout>
  );
};
```

5. Import + thêm `case "demo"` trong `video/src/scenes/index.tsx`.
6. Nếu muốn nền khác theo loại scene, thêm vào `background.variants` của template.
7. Chạy `cd video; npx tsc --noEmit; cd ..`, build và render still ở **cả
   khung dọc lẫn ngang** để kiểm tra.

`SceneRenderer` hiện có các nhóm: `hook`, `stat`, `punch`/`quote`/`title`/…,
`list`/`bullets`/`captionStack`/`recap`, `timeline`, `compare`, `chart`,
`outro`. Scene type mới mặc định rơi vào `Punch` nếu chưa đăng ký — hãy thêm
case rõ ràng.

## 4. Thêm visual metaphor

Visual nhận **dữ liệu**, không chứa nội dung. Ba nơi phải đồng bộ, và `tsc` báo
lỗi nếu quên một trong hai nơi đầu:

1. **Component** `video/src/visuals/tech/PipelineDiagram.tsx`, nhận `data` đã có
   đủ giá trị (build đã gộp default) và lấy bề rộng từ layout:

```tsx
import React from "react";
import type { Brand } from "../../lib/types";
import { fontMono } from "../../lib/theme";
import { useEnter } from "../../lib/motion";
import { useLayout } from "../../lib/context";

export type PipelineData = { steps: string[] };

export const PipelineDiagram: React.FC<{ brand: Brand; data: PipelineData }> = ({
  brand,
  data,
}) => {
  const enter = useEnter(4);
  const { wide } = useLayout();
  return (
    <div style={{ ...enter, width: wide, fontFamily: fontMono, color: brand.colors.fg }}>
      {data.steps.join(" → ")}
    </div>
  );
};
```

2. **Registry** `video/src/visuals/registry.tsx`: thêm một mục vào `renderers`
   (khoá phải trùng tên kind trong catalog):

```tsx
pipeline: ({ scene, brand }) => (
  <PipelineDiagram brand={brand} data={dataOf<PipelineData>(scene)} />
),
```

3. **Catalog** `config/visuals.json`: khai báo `summary`, `useFor`, `requireData`,
   `dataSchema` (JSON Schema, `additionalProperties: false`) và `defaults`:

```json
"pipeline": {
  "summary": "Chuỗi bước nối nhau bằng mũi tên.",
  "useFor": "Quy trình nhiều bước.",
  "requireData": true,
  "dataSchema": {
    "type": "object",
    "additionalProperties": false,
    "properties": { "steps": { "type": "array", "minItems": 2, "maxItems": 5,
                               "items": { "type": "string", "maxLength": 24 } } }
  },
  "defaults": { "steps": ["Input", "Model", "Output"] }
}
```

`defaults` chỉ là **mẫu trung tính** để component luôn có đủ trường. Visual mang
nội dung thì đặt `"requireData": true` trong catalog: kịch bản bắt buộc có
`visual.data`, nếu không `validate.py` báo lỗi (nội dung của một video cũ không
được lọt sang video mới). Visual không mang nội dung (như `phone`, `stick`) đặt
`false`.

Dùng trong script (có thể bỏ các khoá không cần đổi):

```json
"visual": { "kind": "pipeline", "data": { "steps": ["Thu thập", "Huấn luyện", "Triển khai"] } }
```

`validate.py` kiểm `kind` và `data` theo catalog; `pipeline.build` gộp default
vào `visual.data`; agent đọc catalog bằng `python -m pipeline.visuals --list`.
`tests/test_config.py` kiểm default của mọi kind hợp lệ với schema của nó.

Visual phải tự vẽ bằng code, không đọc ảnh/asset ngoài. Kích thước dùng
`useLayout().wide` (không hard-code 860); khung hình hẹp có thể thu nhỏ bằng
`layout.visualScale`.

### Visual `stick` cho whiteboard

Template `whiteboard` dùng `visual.kind: "stick"` với nhân vật que:

```json
"visual": {
  "kind": "stick",
  "label": "an hour",
  "sub": "/aʊə/ • silent h",
  "pose": "point"
}
```

- `label`: câu trong bong bóng thoại (tối đa 60 ký tự).
- `sub`: ghi chú nhỏ, thường là phiên âm hoặc quy tắc.
- `pose`: `wave | point | think | write | cheer`.

Nhân vật nằm trong `video/src/visuals/stick/StickFigure.tsx`; sửa pose/dáng
ở đó, không hard-code nội dung bài giảng trong component.

## 5. Thêm SFX

Chỉ thêm khi thật sự có điểm nhấn thị giác. **Không dùng whoosh.**

1. Tải asset có giấy phép rõ ràng (nguồn hiện tại: Mixkit Free License).
2. Chuẩn hoá về **48 kHz**, mono/stereo thống nhất, peak khoảng −5 dBFS.
3. Lưu vào `assets/sfx/<ten>.wav`, ghi nguồn + giấy phép vào
   `assets/sfx/SOURCES.md`.
4. Thêm vào `config/sfx.json`:

```json
{
  "id": "tick",
  "file": "tick.wav",
  "volume": 0.45,
  "description": "Tick khi số liệu chốt"
}
```

5. Khai báo trong scene:

```json
"sfx": "tick",
"sfxAtSec": 0.1,
"sfxVolume": 0.5
```

6. Build sẽ copy asset sang `02-audio/<fmt>/sfx/`; render đặt đúng
   `scene.startSec + sfxAtSec`.
7. Nghe lại tại các điểm cắt; nếu SFX lấn giọng, giảm volume thay vì thêm
   asset thứ hai.

`whoosh` nằm trong `banned` của catalog và bị build từ chối.

## 6. Thêm độ dài (format) hoặc khung hình (aspect)

Hai trục độc lập:

- **format** (`short`, `long`) = luật nội dung: số scene, số từ, loại scene,
  thời lượng. Nằm ở `config/formats.json`.
- **aspect** (`vertical`, `horizontal`, `square`) = bố cục: kích thước, safe
  area, cỡ chữ, vị trí phụ đề. Nằm ở `config/aspects.json`.

Cùng một kịch bản render được ở nhiều khung hình; audio và căn thời gian dùng
chung:

```powershell
python -m pipeline.make --project-id <id> --format short --aspect vertical,horizontal,square
```

**Thêm khung hình** (ví dụ 4:5): thêm một khối vào `config/aspects.json` có
đúng bộ khoá của `vertical` (test `test_all_aspects_share_the_same_structure`
kiểm), rồi render still ở các loại scene chính (hook, stat, list, compare) để
chỉnh số. Không cần sửa code Python hay Remotion. `square` đang ở trạng thái
`draft`: dùng được nhưng số chưa tinh chỉnh kỹ.

**Thêm độ dài** (ví dụ `medium`): thêm khối vào `config/formats.json` (có
`defaultAspect`). Tên file kịch bản là `scripts/<format>.json`. Nếu agent
viết kịch bản cần luật riêng, cập nhật prompt trong `.opencode/agents/`.

Component Remotion **không bao giờ** so sánh tên format hay aspect: chỉ đọc
`useLayout()` và `useTemplate()`. Cần một con số mới theo khung hình thì thêm
khoá vào mọi khối trong `aspects.json` và type `Layout`.

## 7. Thêm composition / loại video khác

- **Cùng bố cục, khác nội dung** → chỉ cần style mới + project mới.
- **Khác bố cục** → thêm `video/src/compositions/<Ten>.tsx`, đăng ký
  `<Composition>` trong `Root.tsx`.
- `render.mjs` hiện hard-code composition `DiveCode`; nếu có nhiều
  composition, thêm trường `compositionId` vào props và truyền vào renderer.
- Pipeline Python không cần biết chi tiết hình ảnh; chỉ cần ghi đúng
  `props.json`.

## 8. Checklist sau mỗi thay đổi

```powershell
# 1. Test + lint + type (CI chạy đúng các lệnh này)
python -m pytest
ruff check pipeline tools tests
cd video; npx tsc --noEmit; cd ..

# 2. Build props mới
python -m pipeline.build --project-id ai-nho-tren-may --format short

# 3. Xem 1 frame ở khung dọc và ngang, kiểm tra caption/visual
python -m pipeline.render --project-id ai-nho-tren-may --format short `
    --aspect vertical --still 900 --scale 0.5
python -m pipeline.render --project-id ai-nho-tren-may --format short `
    --aspect horizontal --still 900 --scale 0.5

# 4. Render thử 5 giây (nếu có sửa timeline/SFX)
python -m pipeline.render --project-id ai-nho-tren-may --format short --preview 5

# 5. Render full + kiểm tra audio
python -m pipeline.render --project-id ai-nho-tren-may --format short
```

Refactor giao diện: chụp ảnh trước khi sửa và so pixel sau khi sửa. Công cụ có
sẵn: `node video/stills.mjs <outDir> --props <props.json> --outdir <dir> --frames 60,300`
(một lần bundle cho nhiều frame).

Kiểm tra nhanh style whiteboard mà không cần TTS:

```powershell
python tools/oneoff/make_demo_media.py --project-id english-whiteboard-demo --format short
python -m pipeline.build --project-id english-whiteboard-demo --format short
python -m pipeline.render --project-id english-whiteboard-demo --format short `
    --still 60 --scale 0.5
```

`make_demo_media.py` ghi audio silence để xem style nhanh; chỉ dùng khi chưa
có voice, và đừng chạy trước lần render cuối vì nó sẽ ghi đè audio.

Kiểm tra cuối:

- Caption không nhảy, không chồng, không có card trắng.
- Không có whoosh ở điểm cắt.
- SFX chỉ xuất hiện đúng điểm nhấn đã khai báo.
- Video đúng kích thước/fps của khung hình đã chọn, thời lượng khớp props.
- `projects/` không bị ghi đè bởi output.
