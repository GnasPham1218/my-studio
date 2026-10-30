// Brand có thể đổi font qua CSS variable trong ExplainerVideo.
export const fontDisplay =
  'var(--font-display, "Be Vietnam Pro", "Segoe UI", system-ui, sans-serif)';
export const fontMono =
  'var(--font-mono, "JetBrains Mono", "Consolas", monospace)';

export const withAlpha = (hex: string, alpha: number) => {
  const clean = hex.replace("#", "");
  const r = parseInt(clean.slice(0, 2), 16);
  const g = parseInt(clean.slice(2, 4), 16);
  const b = parseInt(clean.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

export const mulberry32 = (seed: number) => {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
};

export const hashSeed = (text: string) => {
  let hash = 2166136261;
  for (let i = 0; i < text.length; i += 1) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
};

/** Tên màu trong palette (primary, accent, ...) hoặc mã hex. */
export const resolveColor = (
  ref: string,
  colors: Record<string, string>,
): string => (ref.startsWith("#") ? ref : (colors[ref] ?? ref));
