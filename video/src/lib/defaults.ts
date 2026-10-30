import aspects from "../../../config/aspects.json";
import base from "../../../config/templates/_base.json";
import techExplainer from "../../../config/templates/tech-explainer.json";
import type { Layout, Props, Template } from "./types";

/**
 * Props mặc định chỉ để xem trước trong `remotion studio`. Khi render thật,
 * pipeline.build ghi layout + template đầy đủ vào props.json; ở đây lấy thẳng
 * từ config để Studio luôn khớp với pipeline.
 */
const layout = { aspect: "vertical", ...aspects.aspects.vertical } as unknown as Layout;
const template = {
  ...base,
  ...techExplainer,
  background: { ...base.background, ...techExplainer.background },
  transition: { ...base.transition, ...techExplainer.transition },
} as unknown as Template;

const brand = {
  channel: {
    name: "DiveCode1218",
    handle: "@DiveCode1218",
    tagline: "AI và công nghệ, giải thích dễ hiểu",
    language: "vi",
  },
  voice: { provider: "vieneu", voiceId: "Mai Anh" },
  audio: {
    sampleRate: 48000,
    targetDbfs: -18,
    peakDbfs: -1,
    leadInSec: 0.15,
    tailOutSec: 0.25,
  },
  music: { enabled: false, track: "", gainDb: -22 },
  colors: {
    bg: "#070B12",
    surface: "#101827",
    fg: "#F4F7FB",
    muted: "#8A97AB",
    primary: "#22D3EE",
    accent: "#F59E0B",
  },
  fonts: {
    display: "Be Vietnam Pro",
    body: "Be Vietnam Pro",
    mono: "JetBrains Mono",
  },
  logo: { path: "", wordmark: "DiveCode1218", opacity: 0.9 },
  watermark: { position: "top-right", heightPx: 44, marginPx: 40 },
  cta: {
    text: "Theo dõi DiveCode1218 để xem tập tiếp theo",
    handle: "@DiveCode1218",
  },
  visuals: { generated: "procedural", palette: ["#22D3EE", "#6366F1", "#0EA5E9"] },
};

const sampleScene = {
  id: "s01",
  type: "hook",
  startSec: 0,
  durationSec: 3,
  narration: "Đây là bản xem trước của DiveCode1218.",
  onScreenText: "AI chạy trên máy đang trở lại",
  kicker: "@DiveCode1218",
  emphasis: ["AI"],
  visual: { kind: "none" },
  words: [
    { w: "Đây", start: 0.1, end: 0.3 },
    { w: "là", start: 0.3, end: 0.4 },
    { w: "bản", start: 0.4, end: 0.6 },
  ],
};

// Cảnh thứ hai để Studio xem được chuyển cảnh.
const sampleScene2 = {
  ...sampleScene,
  id: "s02",
  type: "list",
  startSec: 3,
  onScreenText: "Ba lý do",
  bullets: ["Riêng tư", "Không cần mạng", "Miễn phí"],
  words: [],
};

export const defaultProps: Props = {
  format: "short",
  aspect: "vertical",
  width: layout.width,
  height: layout.height,
  fps: layout.fps,
  totalSec: 6,
  projectId: "demo",
  title: "Demo",
  brand: brand as Props["brand"],
  template,
  layout,
  audioDir: "",
  sfxCatalog: {},
  scenes: [sampleScene, sampleScene2],
  captions: [
    {
      start: 0.1,
      end: 0.9,
      words: [
        { w: "Đây", start: 0.1, end: 0.3 },
        { w: "là", start: 0.3, end: 0.4 },
        { w: "bản", start: 0.4, end: 0.6 },
      ],
    },
  ],
};
