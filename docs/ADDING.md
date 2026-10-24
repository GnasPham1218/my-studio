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

## 2. Thêm style trình bày

1. Tạo `video/src/styles/<style-id>.ts`, export một `VideoStyle`:

```ts
import type { VideoStyle } from "./tech-explainer";

export const minimal: VideoStyle = {
  id: "minimal",
  label: "Minimal",
  description: "Ít chuyển động, nhiều khoảng trắng.",
  backgroundVariant: () => "calm",
  backgroundKind: "tech",   // "tech" = nền tối, "paper" = giấy sáng
  captionTheme: "tech",     // "tech" = chữ sáng, "paper" = thẻ giấy
  showSceneIndex: false,
  showProgress: true,       // thanh tiến độ riêng khi ẩn số scene
  showWatermark: true,
};
```

2. Đăng ký trong `video/src/styles/index.ts`:

```ts
import { minimal } from "./minimal";
export const styles = { "tech-explainer": techExplainer, minimal };
```

3. Đặt `"style": "minimal"` trong `projects/<id>/project.json`.
4. Build lại props; `build.py` tự ghi `styleId` vào props.

Style không nên chứa nội dung hay đọc file. Nếu cần thay đổi bố cục sâu hơn
(ví dụ format ngang), hãy thêm composition mới thay vì nhồi vào style.

## 3. Thêm scene type

Ví dụ thêm `demo`:

1. Thêm `"demo"` vào `enum` của `scene.type` trong
   `schemas/script.schema.json`.
2. Nếu có luật riêng (số từ, field bắt buộc), thêm vào `pipeline/validate.py`.
3. Tạo `video/src/scenes/Demo.tsx`:

```tsx
import React from "react";
import type { SceneProps } from "./shared";
import { Headline, Layout } from "./shared";

export const Demo: React.FC<SceneProps> = ({ scene, brand, format }) => (
  <Layout format={format}>
    <Headline text={scene.onScreenText ?? ""} brand={brand} delay={0} />
  </Layout>
);
```

4. Import + thêm `case "demo"` trong `video/src/scenes/index.tsx`.
5. Nếu muốn nền khác, cập nhật `backgroundVariant` trong style.
6. Chạy `cd video; npx tsc --noEmit; cd ..`, build và render still để kiểm tra.

`SceneRenderer` hiện có các nhóm: `hook`, `stat`, `punch`/`quote`/`title`/…,
`list`/`bullets`/`captionStack`/`recap`, `timeline`, `compare`, `chart`,
`outro`. Scene type mới mặc định rơi vào `Punch` nếu chưa đăng ký — hãy thêm
case rõ ràng.

## 4. Thêm visual metaphor

Ví dụ thêm `pipeline`:

1. Thêm `"pipeline"` vào `visual.kind` trong `schemas/script.schema.json`.
2. Tạo `video/src/visuals/tech/PipelineDiagram.tsx`:

```tsx
import React from "react";
import type { Brand } from "../../lib/types";
import { fontMono, withAlpha } from "../../lib/theme";
import { useEnter } from "../../lib/motion";
import { WIDE } from "../layout";

export const PipelineDiagram: React.FC<{ brand: Brand }> = ({ brand }) => {
  const enter = useEnter(4);
  return (
    <div style={{ ...enter, width: WIDE, fontFamily: fontMono, color: brand.colors.fg }}>
      …
    </div>
  );
};
```

3. Import và thêm vào `visuals/index.tsx`:

```tsx
import { PipelineDiagram } from "./tech/PipelineDiagram";

// trong Visual:
case "pipeline":
  return <PipelineDiagram brand={brand} />;

// trong hasVisual:
const VISUAL_KINDS = new Set([..., "pipeline"]);
```

4. Thêm kind vào tài liệu/agent nếu cần.
5. Dùng trong script:

```json
"visual": { "kind": "pipeline", "label": "Input → Model → Output" }
```

Visual phải tự vẽ bằng code, không đọc ảnh/asset ngoài. Nếu visual cần dữ
liệu riêng, thêm field vào schema + type + props, đừng hard-code nội dung.

### Visual `stick` cho whiteboard

Style `whiteboard` dùng `visual.kind: "stick"` với nhân vật que:

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

## 6. Thêm format / tỉ lệ mới

Hiện tại chỉ short 9:16. Nếu thật sự cần thêm:

1. Thêm key vào `config/formats.json` (width, height, fps, safe area, giới hạn
   scene/từ/giây).
2. Mở rộng type `format` trong `video/src/lib/types.ts` và các layout đang dùng
   `"short" | "long"`.
3. Cập nhật `pipeline/validate.py`, `build.py` và CLI `choices`.
4. Nếu bố cục khác hẳn, tạo composition mới trong
   `video/src/compositions/`, đăng ký ở `Root.tsx`, và cho `render.mjs` chọn
   composition ID tương ứng.
5. Thêm ảnh still cho cả hai tỉ lệ trước khi render full.

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
# 1. Type + Python
cd video; npx tsc --noEmit; cd ..
python -m compileall -q pipeline tools

# 2. Build props mới
python -m pipeline.build --project-id ai-nho-tren-may --format short

# 3. Xem 1 frame, kiểm tra caption/visual
python -m pipeline.render --project-id ai-nho-tren-may --format short `
    --still 900 --scale 0.5

# 4. Render thử 5 giây (nếu có sửa timeline/SFX)
python -m pipeline.render --project-id ai-nho-tren-may --format short --preview 5

# 5. Render full + kiểm tra audio
python -m pipeline.render --project-id ai-nho-tren-may --format short
```

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
- Video đúng 1080×1920, 30 fps, thời lượng khớp props.
- `projects/` không bị ghi đè bởi output.
