import React from "react";
import { AbsoluteFill } from "remotion";
import type { Brand } from "../lib/types";
import { withAlpha } from "../lib/theme";

/**
 * Nền giấy cho style whiteboard.
 *
 * - Không chuyển động: nội dung là phần duy nhất chuyển động.
 * - Có dòng kẻ ngang rất nhẹ + lề đỏ, gợi vở học tiếng Anh.
 * - Viền tối nhẹ để chữ tối vẫn tách khỏi nền khi render trên mobile.
 */
export const PaperBackground: React.FC<{
  brand: Brand;
  seed: string;
}> = ({ brand }) => {
  return (
    <AbsoluteFill style={{ backgroundColor: brand.colors.bg }}>
      <AbsoluteFill
        style={{
          background: `linear-gradient(165deg, ${brand.colors.surface} 0%, ${brand.colors.bg} 58%, ${brand.colors.bg} 100%)`,
        }}
      />
      <AbsoluteFill
        style={{
          backgroundImage: `repeating-linear-gradient(
            to bottom,
            transparent 0px,
            transparent 69px,
            ${withAlpha(brand.colors.fg, 0.055)} 69px,
            ${withAlpha(brand.colors.fg, 0.055)} 71px
          )`,
          backgroundSize: "100% 71px",
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 0,
          bottom: 0,
          left: 86,
          width: 2,
          backgroundColor: withAlpha(brand.colors.accent, 0.18),
        }}
      />
      <AbsoluteFill
        style={{
          background: `radial-gradient(120% 88% at 50% 42%, transparent 58%, ${withAlpha(
            brand.colors.fg,
            0.055,
          )} 100%)`,
        }}
      />
      <AbsoluteFill
        style={{
          boxShadow: `inset 0 0 90px ${withAlpha(brand.colors.fg, 0.035)}`,
        }}
      />
    </AbsoluteFill>
  );
};
