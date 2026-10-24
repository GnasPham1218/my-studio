import { spring, useCurrentFrame, useVideoConfig } from "remotion";

/** Tiến trình spring 0→1, không vượt biên, dùng chung cho mọi chuyển động. */
export const useProgress = (delayFrames = 0, durationSec = 0.5) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({
    frame: frame - delayFrames,
    fps,
    config: { damping: 200, mass: 0.9 },
    durationInFrames: Math.max(1, Math.round(fps * durationSec)),
  });
};

/** Vào cảnh: opacity + nhích lên 14px. */
export const useEnter = (delayFrames = 0) => {
  const progress = useProgress(delayFrames);
  return {
    opacity: progress,
    transform: `translateY(${(1 - progress) * 14}px)`,
  };
};
