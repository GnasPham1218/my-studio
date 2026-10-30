import path from "node:path";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { bundle } from "@remotion/bundler";
import {
  ensureBrowser,
  renderMedia,
  renderStill,
  selectComposition,
} from "@remotion/renderer";
import { browserOption as findBrowser, makeFlag } from "./node-utils.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));

const argv = process.argv.slice(2);
const projectArg = argv.find((item) => !item.startsWith("--"));
const flag = makeFlag(argv);

if (!projectArg) {
  console.error(
    "Cách dùng: node render.mjs <thư-mục-project> [--props <props.json>] [--out <file>] [--still <frame>] [--preview <giây>] [--scale 0.5]",
  );
  process.exit(1);
}

const projectDir = path.resolve(projectArg);
const propsPath = path.resolve(
  flag("props") ?? path.join(projectDir, "props.json"),
);

if (!fs.existsSync(propsPath)) {
  console.error(
    `Không thấy ${propsPath}. Chạy: python -m pipeline.build --project-id <projectId>`,
  );
  process.exit(1);
}

const props = JSON.parse(fs.readFileSync(propsPath, "utf8"));
// --capcut <thư-mục>: mỗi scene một clip không tiếng + audio.wav cả video.
const capcutDir = flag("capcut");
if (capcutDir) {
  props.capcut = true;
}
const stillFrame = flag("still");
const previewSeconds = flag("preview");
const scale = Number(flag("scale") ?? 1);
const concurrency = flag("concurrency")
  ? Number(flag("concurrency"))
  : null;
const logLevel = argv.includes("--verbose") ? "verbose" : "info";
const browserOption = findBrowser();

console.log(
  `Project: ${path.basename(projectDir)} · ${props.format} ${props.width}x${props.height} · ${props.totalSec.toFixed(1)}s`,
);

await ensureBrowser({ ...browserOption, logLevel });

console.log("Bundle…");
const serveUrl = await bundle({
  entryPoint: path.join(here, "src", "index.ts"),
  publicDir: projectDir,
  onProgress: () => {},
});

const composition = await selectComposition({
  serveUrl,
  id: "DiveCode",
  inputProps: props,
  ...browserOption,
  logLevel,
});

console.log(
  `Composition: ${composition.durationInFrames} frames @ ${composition.fps}fps`,
);

if (capcutDir) {
  const scenesDir = path.join(capcutDir, "scenes");
  fs.mkdirSync(scenesDir, { recursive: true });
  const fps = composition.fps;
  const ranges = props.scenes.map((scene) => {
    const from = Math.round(scene.startSec * fps);
    const duration = Math.max(1, Math.round(scene.durationSec * fps));
    return [from, Math.min(composition.durationInFrames, from + duration) - 1];
  });
  const totalFrames =
    ranges.reduce((sum, [a, b]) => sum + (b - a + 1), 0) +
    composition.durationInFrames;
  let done = 0;
  const emit = (extra) =>
    process.stdout.write(`PROGRESS ${done + extra} ${totalFrames}\n`);

  for (const [index, scene] of props.scenes.entries()) {
    const [start, end] = ranges[index];
    await renderMedia({
      composition,
      serveUrl,
      codec: "h264",
      outputLocation: path.join(scenesDir, `${scene.id}.mp4`),
      inputProps: props,
      scale,
      frameRange: [start, end],
      crf: 18,
      muted: true,
      concurrency,
      ...browserOption,
      logLevel,
      onProgress: ({ renderedFrames }) => emit(renderedFrames ?? 0),
    });
    done += end - start + 1;
    console.log(`✓ ${scene.id}.mp4`);
  }

  // Giọng + SFX gộp thành một file, khớp từ giây 0 của video.
  await renderMedia({
    composition,
    serveUrl,
    codec: "wav",
    outputLocation: path.join(capcutDir, "audio.wav"),
    inputProps: props,
    ...browserOption,
    logLevel,
    onProgress: ({ progress }) =>
      emit(Math.round(progress * composition.durationInFrames)),
  });
  done = totalFrames;
  emit(0);
  console.log(`\n✓ ${capcutDir}`);
} else if (stillFrame !== undefined) {
  const frame = Number(stillFrame);
  const output =
    flag("out") ?? path.join(path.dirname(propsPath), `still-${frame}.png`);
  fs.mkdirSync(path.dirname(output), { recursive: true });
  await renderStill({
    composition,
    serveUrl,
    output,
    frame,
    inputProps: props,
    scale,
    ...browserOption,
    logLevel,
  });
  console.log(`\n✓ ${output}`);
} else {
  const suffix = previewSeconds ? `preview-${previewSeconds}s` : props.format;
  const output =
    flag("out") ??
    path.join(path.dirname(propsPath), `render.${suffix}.mp4`);
  fs.mkdirSync(path.dirname(output), { recursive: true });
  const frameRange = previewSeconds
    ? [0, Math.max(0, Math.round(Number(previewSeconds) * props.fps) - 1)]
    : undefined;
  const totalFrames = frameRange
    ? frameRange[1] - frameRange[0] + 1
    : composition.durationInFrames;

  let lastEmit = 0;
  const onProgress = ({ progress, renderedFrames }) => {
    const now = Date.now();
    if (progress < 1 && now - lastEmit < 300) {
      return;
    }
    lastEmit = now;
    const done =
      typeof renderedFrames === "number"
        ? renderedFrames
        : Math.round(progress * totalFrames);
    // Dòng máy đọc: pipeline/render.py vẽ thanh tiến trình từ số này.
    process.stdout.write(`PROGRESS ${done} ${totalFrames}\n`);
  };

  const started = Date.now();
  await renderMedia({
    composition,
    serveUrl,
    codec: "h264",
    outputLocation: output,
    inputProps: props,
    scale,
    frameRange,
    crf: 18,
    audioCodec: "aac",
    audioBitrate: "192k",
    concurrency,
    ...browserOption,
    logLevel,
    onProgress,
  });
  const seconds = ((Date.now() - started) / 1000).toFixed(1);
  console.log(`\n✓ ${output} (${seconds}s)`);
}
