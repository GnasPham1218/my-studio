// Render nhiều ảnh tĩnh chỉ với MỘT lần bundle (render.mjs --still bundle lại mỗi lần).
//
//   node stills.mjs <thư-mục-publicDir> --props props.json --outdir <dir> \
//        --frames 0,90,300 [--scale 0.5]
//
// Dùng cho: so sánh trước/sau khi refactor, và so khớp template với video mẫu
// (pipeline.analyze compare). In mỗi file đã ghi dạng `STILL <frame> <path>`.
import path from "node:path";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { bundle } from "@remotion/bundler";
import {
  ensureBrowser,
  renderStill,
  selectComposition,
} from "@remotion/renderer";
import { browserOption, makeFlag } from "./node-utils.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const flag = makeFlag(argv);
const projectArg = argv.find((item) => !item.startsWith("--"));
const propsArg = flag("props");
const outdir = flag("outdir");
const frames = (flag("frames") ?? "")
  .split(",")
  .map((item) => item.trim())
  .filter(Boolean)
  .map(Number);

if (!projectArg || !propsArg || !outdir || frames.length === 0) {
  console.error(
    "Cách dùng: node stills.mjs <publicDir> --props <props.json> --outdir <dir> --frames 0,90 [--scale 0.5]",
  );
  process.exit(1);
}

const props = JSON.parse(fs.readFileSync(path.resolve(propsArg), "utf8"));
const scale = Number(flag("scale") ?? 1);
const browser = browserOption();
await ensureBrowser({ ...browser, logLevel: "error" });

const serveUrl = await bundle({
  entryPoint: path.join(here, "src", "index.ts"),
  publicDir: path.resolve(projectArg),
  onProgress: () => {},
});
const composition = await selectComposition({
  serveUrl,
  id: "DiveCode",
  inputProps: props,
  ...browser,
  logLevel: "error",
});

fs.mkdirSync(path.resolve(outdir), { recursive: true });
for (const frame of frames) {
  const output = path.resolve(outdir, `frame-${String(frame).padStart(6, "0")}.png`);
  await renderStill({
    composition,
    serveUrl,
    output,
    frame,
    inputProps: props,
    scale,
    ...browser,
    logLevel: "error",
  });
  console.log(`STILL ${frame} ${output}`);
}
