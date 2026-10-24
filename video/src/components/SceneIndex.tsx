import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import type { Brand, Scene } from "../lib/types";
import { fontMono, withAlpha } from "../lib/theme";

/**
 * Chỉ số scene ở góc trên trái, đối xứng với watermark bên phải.
 * Tĩnh trong suốt scene, chỉ đổi khi cắt cảnh.
 */
export const SceneIndex: React.FC<{ scenes: Scene[]; brand: Brand }> = ({
  scenes,
  brand,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const time = frame / fps;

  const index = scenes.findIndex(
    (scene) =>
      time >= scene.startSec && time < scene.startSec + scene.durationSec,
  );
  const current = index < 0 ? 0 : index;
  const total = scenes.length;
  const ratio = (current + 1) / total;

  return (
    <div
      style={{
        position: "absolute",
        top: 116,
        left: 44,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: 6,
          fontFamily: fontMono,
          fontSize: 22,
          fontWeight: 700,
          letterSpacing: 2,
          color: withAlpha(brand.colors.fg, 0.55),
        }}
      >
        <span>{String(current + 1).padStart(2, "0")}</span>
        <span style={{ color: withAlpha(brand.colors.fg, 0.28) }}>
          / {String(total).padStart(2, "0")}
        </span>
      </div>
      <div
        style={{
          marginTop: 9,
          width: 58,
          height: 2,
          borderRadius: 1,
          backgroundColor: withAlpha(brand.colors.fg, 0.14),
        }}
      >
        <div
          style={{
            width: `${ratio * 100}%`,
            height: "100%",
            borderRadius: 1,
            backgroundColor: brand.colors.primary,
            opacity: 0.75,
          }}
        />
      </div>
    </div>
  );
};
