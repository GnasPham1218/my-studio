import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import type { Brand, Scene } from "../lib/types";
import { withAlpha } from "../lib/theme";

/**
 * Thanh tiến độ độc lập với số scene.
 *
 * Dùng cho style ẩn số scene (whiteboard) nhưng vẫn cần người xem biết
 * mình đang ở đâu trong video. Chạy liên tục theo thời gian, không nhảy
 * theo từng scene.
 */
export const ProgressBar: React.FC<{
  scenes: Scene[];
  brand: Brand;
}> = ({ scenes, brand }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const time = frame / fps;
  const last = scenes[scenes.length - 1];
  const total = last ? last.startSec + last.durationSec : 1;
  const ratio = Math.min(1, Math.max(0, time / total));

  return (
    <div
      style={{
        position: "absolute",
        top: 116,
        left: 44,
        width: 140,
        height: 4,
        borderRadius: 2,
        backgroundColor: withAlpha(brand.colors.fg, 0.14),
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          width: `${ratio * 100}%`,
          height: "100%",
          borderRadius: 2,
          backgroundColor: brand.colors.primary,
          opacity: 0.85,
        }}
      />
    </div>
  );
};
