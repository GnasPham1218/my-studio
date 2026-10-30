import React from "react";
import { AbsoluteFill } from "remotion";
import type { Brand } from "../lib/types";
import { fontMono, withAlpha } from "../lib/theme";
import { useLayout, useTemplate } from "../lib/context";

export const Watermark: React.FC<{ brand: Brand }> = ({ brand }) => {
  const { chrome } = useLayout();
  const { watermark: look } = useTemplate().chrome;
  const place = chrome.watermark;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          top: place.top,
          right: place.right,
          display: "flex",
          alignItems: "center",
          gap: 10,
          opacity: look.opacity,
          fontFamily: fontMono,
          fontSize: place.fontSize,
          fontWeight: 700,
          letterSpacing: look.letterSpacing,
          textTransform: look.uppercase ? "uppercase" : "none",
          color: brand.colors.fg,
          textShadow: look.glow
            ? `0 2px 12px ${withAlpha("#000000", 0.5)}`
            : undefined,
        }}
      >
        <span
          style={{
            width: 9,
            height: 9,
            borderRadius: "50%",
            backgroundColor: brand.colors.primary,
            boxShadow: look.glow ? `0 0 14px ${brand.colors.primary}` : undefined,
          }}
        />
        {brand.logo.wordmark}
      </div>
    </AbsoluteFill>
  );
};
