import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import type { Brand } from "../lib/types";
import { hashSeed, withAlpha } from "../lib/theme";

type Variant = "hero" | "data" | "calm" | "glitch";

/**
 * Nền tĩnh, chỉ có một quầng sáng "thở" rất chậm.
 * Bỏ hạt trôi, grid cuộn, scanline: nội dung là phần chuyển động duy nhất.
 */
export const Background: React.FC<{
  brand: Brand;
  seed: string;
  variant?: Variant;
}> = ({ brand, seed, variant = "calm" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const seconds = frame / fps;
  const seedValue = hashSeed(seed);

  // Vị trí quầng sáng cố định theo scene, không trôi ngang dọc.
  const glowX = 16 + (seedValue % 46);
  const glowY = 14 + ((seedValue >> 8) % 18);
  const breathe =
    0.5 + 0.5 * Math.sin(seconds * 0.42 + ((seedValue % 100) / 100) * Math.PI * 2);
  const tint = variant === "hero" ? 0.19 : variant === "data" ? 0.15 : 0.12;

  return (
    <AbsoluteFill style={{ backgroundColor: brand.colors.bg }}>
      <AbsoluteFill
        style={{
          background: `linear-gradient(165deg, #0A1420 0%, ${brand.colors.bg} 58%, #04070C 100%)`,
        }}
      />
      <AbsoluteFill
        style={{
          background: `radial-gradient(58% 40% at ${glowX}% ${glowY}%, ${withAlpha(
            brand.colors.primary,
            tint + breathe * 0.03,
          )} 0%, transparent 72%)`,
        }}
      />
      <AbsoluteFill
        style={{
          background: `radial-gradient(44% 34% at 88% 74%, ${withAlpha(
            brand.colors.accent,
            0.045 + breathe * 0.012,
          )} 0%, transparent 70%)`,
        }}
      />
      <AbsoluteFill
        style={{
          backgroundImage: `linear-gradient(${withAlpha(
            brand.colors.fg,
            0.035,
          )} 1px, transparent 1px), linear-gradient(90deg, ${withAlpha(
            brand.colors.fg,
            0.035,
          )} 1px, transparent 1px)`,
          backgroundSize: "96px 96px",
          WebkitMaskImage:
            "radial-gradient(72% 58% at 50% 34%, #000 0%, transparent 100%)",
          maskImage:
            "radial-gradient(72% 58% at 50% 34%, #000 0%, transparent 100%)",
        }}
      />
      <AbsoluteFill
        style={{
          background: `radial-gradient(120% 85% at 50% 42%, transparent 42%, ${withAlpha(
            "#000000",
            0.55,
          )} 100%)`,
        }}
      />
    </AbsoluteFill>
  );
};
