import type { Props } from "./types";

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

export const defaultProps: Props = {
  format: "short",
  styleId: "tech-explainer",
  width: 1080,
  height: 1920,
  fps: 30,
  totalSec: 3,
  projectId: "demo",
  title: "Demo",
  brand: brand as Props["brand"],
  safeArea: { top: 220, bottom: 380, left: 60, right: 140 },
  audioDir: "",
  sfxCatalog: {},
  scenes: [sampleScene],
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
