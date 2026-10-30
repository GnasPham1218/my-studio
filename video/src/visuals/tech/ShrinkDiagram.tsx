import React from "react";
import type { Brand } from "../../lib/types";
import { fontDisplay, fontMono, withAlpha } from "../../lib/theme";
import { useEnter, useProgress } from "../../lib/motion";
import { useLayout } from "../../lib/context";
import { ChipIcon } from "../icons";

export type ShrinkData = {
  title: string;
  rows: { label: string; ratio: number; accent?: boolean }[];
  caption: string;
};

const ShrinkDiagram: React.FC<{
  brand: Brand;
  data: ShrinkData;
  delay?: number;
}> = ({ brand, data, delay = 6 }) => {
  const enter = useEnter(delay);
  const grow = useProgress(delay + 2, 0.9);
  const { wide } = useLayout();
  // Hàng thường nhạt dần theo thứ tự (0.3, 0.5, ...); hàng accent dùng màu chính.
  let plain = 0;
  const rows = data.rows.map((row) => ({
    ...row,
    color: row.accent
      ? brand.colors.primary
      : withAlpha(brand.colors.fg, 0.3 + 0.2 * plain++),
  }));

  return (
    <div
      style={{
        ...enter,
        width: wide,
        display: "flex",
        alignItems: "center",
        gap: 38,
      }}
    >
      <div style={{ flex: 1 }}>
        <div
          style={{
            fontFamily: fontMono,
            fontSize: 18,
            letterSpacing: 2,
            color: brand.colors.muted,
            marginBottom: 22,
          }}
        >
          {data.title}
        </div>
        {rows.map((row) => (
          <div key={row.label} style={{ marginBottom: 30 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: 10,
                fontFamily: fontMono,
                fontSize: 21,
                letterSpacing: 1.2,
                color: brand.colors.muted,
              }}
            >
              <span>{row.label}</span>
              <span style={{ color: row.color }}>
                {Math.round(row.ratio * 100)}%
              </span>
            </div>
            <div
              style={{
                height: 30,
                borderRadius: 8,
                backgroundColor: withAlpha(brand.colors.fg, 0.07),
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${row.ratio * 100 * grow}%`,
                  height: "100%",
                  borderRadius: 8,
                  backgroundColor: row.color,
                }}
              />
            </div>
          </div>
        ))}
        <div
          style={{
            fontFamily: fontDisplay,
            fontSize: 23,
            color: withAlpha(brand.colors.fg, 0.55),
          }}
        >
          {data.caption}
        </div>
      </div>
      <div
        style={{
          width: 208,
          height: 378,
          borderRadius: 38,
          border: `2px solid ${withAlpha(brand.colors.fg, 0.2)}`,
          background: `linear-gradient(180deg, #0C1624, #070C13)`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: `0 26px 60px ${withAlpha("#000000", 0.5)}`,
        }}
      >
        <ChipIcon size={92} color={brand.colors.primary} />
      </div>
    </div>
  );
};
export { ShrinkDiagram };
