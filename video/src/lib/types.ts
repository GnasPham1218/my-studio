export type Brand = {
  channel: { name: string; handle: string; tagline: string; language: string };
  colors: {
    bg: string;
    surface: string;
    fg: string;
    muted: string;
    primary: string;
    accent: string;
  };
  fonts: { display: string; body: string; mono: string };
  logo: { wordmark: string; opacity: number; path: string };
  watermark: { position: string; heightPx: number; marginPx: number };
  cta: { text: string; handle: string };
  visuals: { generated: string; palette: string[] };
};

export type Word = { w: string; start: number; end: number };

export type CaptionCard = { start: number; end: number; words: Word[] };

export type ChartDatum = { label: string; value: number };

export type Scene = {
  id: string;
  type: string;
  startSec: number;
  durationSec: number;
  narration: string;
  onScreenText?: string;
  kicker?: string;
  bullets?: string[];
  emphasis?: string[];
  visual?: {
    kind: string;
    prompt?: string;
    src?: string;
    label?: string;
    sub?: string;
    /** Pose cho visual "stick": wave | point | think | write | cheer. */
    pose?: string;
  };
  sfx?: string | null;
  sfxAtSec?: number;
  sfxVolume?: number;
  chart?: {
    title?: string;
    unit?: string;
    source?: string;
    data: ChartDatum[];
  };
  stat?: { value: string; unit?: string; label?: string; note?: string };
  timeline?: { label: string; text: string; active?: boolean }[];
  compare?: {
    unit?: string;
    note?: string;
    items: { label: string; value: string; ratio: number; accent?: boolean }[];
  };
  words: Word[];
};

export type SafeArea = { top: number; bottom: number; left: number; right: number };

export type SfxItem = {
  file: string;
  durationSec: number;
  defaultVolume: number;
};

export type Props = {
  format: "short" | "long";
  /** ID trong video/src/styles; mặc định tech-explainer. */
  styleId?: string;
  audioDir: string;
  sfxDir?: string;
  sfxCatalog: Record<string, SfxItem>;
  width: number;
  height: number;
  fps: number;
  totalSec: number;
  projectId: string;
  title: string;
  brand: Brand;
  safeArea: SafeArea;
  scenes: Scene[];
  captions: CaptionCard[];
};
