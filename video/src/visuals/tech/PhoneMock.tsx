import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import type { Brand } from "../../lib/types";
import { fontDisplay, fontMono, withAlpha } from "../../lib/theme";
import { useEnter } from "../../lib/motion";
import { ChipIcon } from "../icons";

export const PhoneMock: React.FC<{
  brand: Brand;
  label: string;
  sub?: string;
  badge?: string;
  width?: number;
  delay?: number;
}> = ({ brand, label, sub, badge = "ON-DEVICE", width = 292, delay = 5 }) => {
  const enter = useEnter(delay);
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pulse = 0.5 + 0.5 * Math.sin((frame / fps) * 1.7);
  const height = width * 1.98;

  return (
    <div
      style={{
        ...enter,
        width,
        filter: `drop-shadow(0 40px 60px ${withAlpha("#000000", 0.55)})`,
      }}
    >
      <div
        style={{
          width,
          height,
          borderRadius: width * 0.13,
          border: `2px solid ${withAlpha(brand.colors.fg, 0.2)}`,
          background: "#080E16",
          padding: width * 0.036,
          position: "relative",
        }}
      >
        <div
          style={{
            position: "absolute",
            top: width * 0.062,
            left: "50%",
            transform: "translateX(-50%)",
            width: width * 0.28,
            height: 8,
            borderRadius: 4,
            backgroundColor: withAlpha(brand.colors.fg, 0.16),
          }}
        />
        <div
          style={{
            height: "100%",
            borderRadius: width * 0.1,
            border: `1px solid ${withAlpha(brand.colors.fg, 0.06)}`,
            background: `radial-gradient(90% 55% at 50% 40%, ${withAlpha(
              brand.colors.primary,
              0.13,
            )}, transparent 72%), linear-gradient(180deg, #0C1624, #070C13)`,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: width * 0.035,
          }}
        >
          <div
            style={{
              fontFamily: fontMono,
              fontSize: 19,
              fontWeight: 700,
              letterSpacing: 4,
              color: brand.colors.muted,
            }}
          >
            {badge}
          </div>
          <div
            style={{
              fontFamily: fontDisplay,
              fontSize: width * 0.22,
              fontWeight: 800,
              lineHeight: 1,
              letterSpacing: -2,
              color: brand.colors.fg,
            }}
          >
            {label}
          </div>
          {sub ? (
            <div
              style={{
                maxWidth: width * 0.8,
                textAlign: "center",
                fontFamily: fontDisplay,
                fontSize: 19,
                lineHeight: 1.3,
                color: brand.colors.muted,
              }}
            >
              {sub}
            </div>
          ) : null}
          <div
            style={{
              marginTop: width * 0.03,
              width: width * 0.3,
              height: width * 0.3,
              borderRadius: width * 0.07,
              border: `2px solid ${withAlpha(
                brand.colors.primary,
                0.45 + pulse * 0.4,
              )}`,
              backgroundColor: withAlpha(brand.colors.primary, 0.1),
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: `0 0 ${28 + pulse * 24}px ${withAlpha(
                brand.colors.primary,
                0.24,
              )}`,
            }}
          >
            <ChipIcon size={width * 0.14} color={brand.colors.primary} />
          </div>
        </div>
      </div>
    </div>
  );
};
