import React from "react";
import type { Brand } from "../../lib/types";
import { fontDisplay, fontMono, withAlpha } from "../../lib/theme";
import { useEnter, useProgress } from "../../lib/motion";
import { CloudIcon, PhoneIcon } from "../icons";
import { WIDE } from "../layout";

const QuestionDiagram: React.FC<{ brand: Brand; delay?: number }> = ({
  brand,
  delay = 6,
}) => {
  const enter = useEnter(delay);
  const left = useProgress(delay + 1, 0.6);
  const right = useProgress(delay + 4, 0.6);

  const panel = (
    title: string,
    sub: string,
    icon: React.ReactNode,
    progress: number,
    offset: number,
  ) => (
    <div
      style={{
        width: 360,
        padding: "30px 28px",
        borderRadius: 22,
        border: `1px solid ${withAlpha(brand.colors.fg, 0.14)}`,
        background: withAlpha(brand.colors.surface, 0.7),
        opacity: progress,
        transform: `translateX(${(1 - progress) * offset}px)`,
        display: "flex",
        flexDirection: "column",
        gap: 14,
      }}
    >
      {icon}
      <div
        style={{
          fontFamily: fontMono,
          fontSize: 22,
          fontWeight: 700,
          letterSpacing: 3,
          color: brand.colors.fg,
        }}
      >
        {title}
      </div>
      <div
        style={{
          fontFamily: fontDisplay,
          fontSize: 20,
          lineHeight: 1.3,
          color: brand.colors.muted,
        }}
      >
        {sub}
      </div>
    </div>
  );

  return (
    <div
      style={{
        ...enter,
        width: WIDE,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 8,
        position: "relative",
      }}
    >
      {panel(
        "MÁY",
        "nhanh, riêng tư",
        <PhoneIcon size={52} color={brand.colors.primary} />,
        left,
        -24,
      )}
      {panel(
        "CLOUD",
        "mạnh, context dài",
        <CloudIcon size={52} color={withAlpha(brand.colors.fg, 0.55)} />,
        right,
        24,
      )}
      <div
        style={{
          position: "absolute",
          fontFamily: fontDisplay,
          fontSize: 90,
          fontWeight: 800,
          color: brand.colors.accent,
          textShadow: `0 0 40px ${withAlpha(brand.colors.accent, 0.4)}`,
          opacity: Math.min(left, right),
        }}
      >
        ?
      </div>
    </div>
  );
};
export { QuestionDiagram };
