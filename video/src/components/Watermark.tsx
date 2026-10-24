import React from "react";
import { AbsoluteFill } from "remotion";
import type { Brand } from "../lib/types";
import type { CaptionTheme } from "../styles";
import { fontMono, withAlpha } from "../lib/theme";

export const Watermark: React.FC<{
  brand: Brand;
  format: "short" | "long";
  theme?: CaptionTheme;
}> = ({ brand, format, theme = "tech" }) => {
  const paper = theme === "paper";
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          top: format === "short" ? 120 : 48,
          right: 44,
          display: "flex",
          alignItems: "center",
          gap: 10,
          opacity: paper ? 0.58 : 0.62,
          fontFamily: fontMono,
          fontSize: format === "short" ? 24 : 20,
          fontWeight: 700,
          letterSpacing: paper ? 1.5 : 3,
          textTransform: paper ? "none" : "uppercase",
          color: brand.colors.fg,
          textShadow: paper
            ? undefined
            : `0 2px 12px ${withAlpha("#000000", 0.5)}`,
        }}
      >
        <span
          style={{
            width: 9,
            height: 9,
            borderRadius: "50%",
            backgroundColor: brand.colors.primary,
            boxShadow: paper ? undefined : `0 0 14px ${brand.colors.primary}`,
          }}
        />
        {brand.logo.wordmark}
      </div>
    </AbsoluteFill>
  );
};
