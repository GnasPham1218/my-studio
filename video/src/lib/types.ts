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
    /** Dữ liệu riêng của kind, đã gộp default ở pipeline.build (config/visuals.json). */
    data?: Record<string, unknown>;
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

export type SfxItem = {
  file: string;
  durationSec: number;
  defaultVolume: number;
};

// ---------------------------------------------------------------- layout

export type SafeArea = { top: number; bottom: number; left: number; right: number };

/**
 * Bố cục theo khung hình. Khớp từng khoá với config/aspects.json; pipeline.build
 * copy nguyên khối của aspect được chọn vào props.layout. Component chỉ đọc
 * khối này (qua useLayout), không bao giờ so sánh tên format hay aspect.
 */
export type Layout = {
  aspect: string;
  width: number;
  height: number;
  fps: number;
  safeArea: SafeArea;
  /** Vùng nội dung của scene. */
  padding: { top: number; bottom: number; left: number; right: number };
  /** Bề rộng cột nội dung mặc định. */
  column: number;
  /** Bề rộng chuẩn của một visual. */
  wide: number;
  /** Thu nhỏ visual khi khung không đủ cao (CSS zoom, ảnh hưởng cả layout). */
  visualScale: number;
  type: {
    hero: number;
    h1: number;
    h2: number;
    body: number;
    small: number;
    stat: number;
    kicker: number;
    gap: number;
  };
  scenes: {
    hook: {
      headline: number;
      headlineWithPhone: number;
      maxWidth: number;
      tagline: number;
      visualWidth: number;
    };
    punch: {
      headline: number;
      headlineWithVisual: number;
      maxWidth: number;
      visualWidth: number;
    };
    stat: {
      value: number;
      valueWithVisual: number;
      unit: number;
      unitWithVisual: number;
      label: number;
      labelWithVisual: number;
      visualWidth: number;
    };
    list: {
      headline: number;
      maxWidth: number;
      width: number;
      rowPaddingY: number;
      rowText: number;
    };
    chart: { headline: number; barAreaHeight: number };
    compare: { headline: number; value: number; width: number };
    timeline: {
      headline: number;
      width: number;
      rowPaddingY: number;
      rowText: number;
    };
    outro: { headline: number; maxWidth: number; visualWidth: number };
  };
  caption: {
    fontSize: number;
    fontSizePaper: number;
    strokePx: number;
    bottom: number;
    boxHeight: number;
    maxWidth: number;
    sideMargin: number;
    scrimHeight: number;
    scrimHeightPaper: number;
    maxWordsPerCard: number;
    maxChars: number;
    minCardSec: number;
  };
  chrome: {
    watermark: { top: number; right: number; fontSize: number };
    sceneIndex: { top: number; left: number };
  };
};

// ---------------------------------------------------------------- template

/** Tên màu trong palette hoặc mã hex. */
export type ColorRef = string;

export type BackgroundVariant = "hero" | "data" | "calm" | "glitch";

/**
 * Giao diện (look) đã gộp với config/templates/_base.json, khớp
 * schemas/template.schema.json. Mọi trường đều có giá trị khi tới Remotion.
 */
export type Template = {
  id: string;
  label?: string;
  background: {
    kind: "tech" | "paper" | "solid" | "gradient";
    defaultVariant: BackgroundVariant;
    variants: Record<string, BackgroundVariant>;
    gradient: { angle: number; stops: string[] };
  };
  caption: {
    fontWeight: number;
    letterSpacing: number;
    uppercase: boolean;
    textShadow: boolean;
    textColor?: ColorRef;
    stroke?: { px: number; color: ColorRef } | null;
    highlight: { color: ColorRef | null; underline: ColorRef | null };
    card: {
      background?: ColorRef;
      backgroundAlpha?: number;
      border?: ColorRef;
      borderAlpha?: number;
      radius?: number;
    } | null;
    /** [[phần trăm từ đáy, alpha], ...]; rỗng = không có scrim. */
    scrim: number[][];
    holdGapSec: number;
    fontSizeRel: number | null;
    bottomRel: number | null;
    maxWidthRel: number | null;
  };
  chrome: {
    sceneIndex: boolean;
    progress: boolean;
    watermark: {
      enabled: boolean;
      glow: boolean;
      uppercase: boolean;
      letterSpacing: number;
      opacity: number;
    };
  };
  motion: { enterDistancePx: number; enterSec: number };
  transition: {
    kind: TransitionKind;
    sec: number;
    /** Ghi đè kind theo scene.type. */
    byType: Record<string, TransitionKind>;
  };
};

export type TransitionKind =
  | "none"
  | "fade"
  | "slide"
  | "push"
  | "wipe"
  | "zoom"
  | "blur";

// ---------------------------------------------------------------- props

export type Props = {
  /** Độ dài/loại nội dung của kịch bản (short | long). Không dùng để chọn bố cục. */
  format: "short" | "long";
  /** Khung hình đã chọn (vertical | horizontal | square). */
  aspect: string;
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
  template: Template;
  layout: Layout;
  scenes: Scene[];
  captions: CaptionCard[];
  /** Xuất cho CapCut: bỏ chuyển cảnh, caption và audio (CapCut tự thêm). */
  capcut?: boolean;
  /** Chữ trên thumbnail (project.json → thumbnail); thiếu thì dùng title. */
  thumbnail?: { text?: string; emphasis?: string[]; kicker?: string };
};
