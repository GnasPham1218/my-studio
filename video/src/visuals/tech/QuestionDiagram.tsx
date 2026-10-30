import React from "react";
import type { Brand } from "../../lib/types";
import { fontDisplay, fontMono, withAlpha } from "../../lib/theme";
import { useEnter, useProgress } from "../../lib/motion";
import { useLayout } from "../../lib/context";
import { CloudIcon, PhoneIcon } from "../icons";

type Panel = { title: string; sub: string; icon?: "phone" | "cloud" };

export type QuestionData = { left: Panel; right: Panel; mark: string };

const QuestionDiagram: React.FC<{
  brand: Brand;
  data: QuestionData;
  delay?: number;
}> = ({ brand, data, delay = 6 }) => {
  const enter = useEnter(delay);
  const left = useProgress(delay + 1, 0.6);
  const right = useProgress(delay + 4, 0.6);
  const { wide } = useLayout();

  const icon = (kind: Panel["icon"], primary: boolean) =>
    kind === "cloud" ? (
      <CloudIcon
        size={52}
        color={primary ? brand.colors.primary : withAlpha(brand.colors.fg, 0.55)}
      />
    ) : (
      <PhoneIcon
        size={52}
        color={primary ? brand.colors.primary : withAlpha(brand.colors.fg, 0.55)}
      />
    );

  const panel = (
    item: Panel,
    primary: boolean,
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
      {icon(item.icon, primary)}
      <div
        style={{
          fontFamily: fontMono,
          fontSize: 22,
          fontWeight: 700,
          letterSpacing: 3,
          color: brand.colors.fg,
        }}
      >
        {item.title}
      </div>
      <div
        style={{
          fontFamily: fontDisplay,
          fontSize: 20,
          lineHeight: 1.3,
          color: brand.colors.muted,
        }}
      >
        {item.sub}
      </div>
    </div>
  );

  return (
    <div
      style={{
        ...enter,
        width: wide,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 8,
        position: "relative",
      }}
    >
      {panel(data.left, true, left, -24)}
      {panel(data.right, false, right, 24)}
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
        {data.mark}
      </div>
    </div>
  );
};
export { QuestionDiagram };
