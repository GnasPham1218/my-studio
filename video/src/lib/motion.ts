import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useTemplate } from "./context";

/**
 * Tiến trình spring 0→1, không vượt biên, dùng chung cho mọi chuyển động.
 * Thời lượng mặc định lấy từ template.motion.enterSec.
 */
export const useProgress = (delayFrames = 0, durationSec?: number) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { motion } = useTemplate();
  return spring({
    frame: frame - delayFrames,
    fps,
    config: { damping: 200, mass: 0.9 },
    durationInFrames: Math.max(
      1,
      Math.round(fps * (durationSec ?? motion.enterSec)),
    ),
  });
};

/** Vào cảnh: opacity + nhích lên (khoảng cách theo template.motion). */
export const useEnter = (delayFrames = 0) => {
  const progress = useProgress(delayFrames);
  const { motion } = useTemplate();
  return {
    opacity: progress,
    transform: `translateY(${(1 - progress) * motion.enterDistancePx}px)`,
  };
};
