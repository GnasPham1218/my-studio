import React from "react";
import type { Brand } from "../../lib/types";
import { fontDisplay, fontMono, withAlpha } from "../../lib/theme";
import { useEnter, useProgress } from "../../lib/motion";
import { useLayout } from "../../lib/context";

export type StorageData = {
  title: string;
  beforeLabel: string;
  afterLabel: string;
  reductionPct: number;
  caption: string;
};

const StorageBar: React.FC<{
  brand: Brand;
  data: StorageData;
  delay?: number;
}> = ({ brand, data, delay = 8 }) => {
  const enter = useEnter(delay);
  const shrink = useProgress(delay + 4, 1.2);
  const { wide } = useLayout();
  const remain = 100 - data.reductionPct * shrink;
  const rows = [
    { label: data.beforeLabel, value: 100, color: withAlpha(brand.colors.fg, 0.32) },
    { label: data.afterLabel, value: remain, color: brand.colors.primary },
  ];

  return (
    <div style={{ ...enter, width: wide }}>
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          marginBottom: 26,
          fontFamily: fontMono,
          fontSize: 20,
          letterSpacing: 2,
          color: brand.colors.muted,
        }}
      >
        <span>{data.title}</span>
        <span style={{ color: brand.colors.primary }}>
          −{data.reductionPct}%
        </span>
      </div>
      {rows.map((row, index) => (
        <div key={row.label} style={{ marginBottom: index === 0 ? 30 : 18 }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: 12,
              fontFamily: fontMono,
              fontSize: 21,
              letterSpacing: 1.2,
              color: brand.colors.muted,
            }}
          >
            <span>{row.label}</span>
            <span style={{ color: row.color }}>{Math.round(row.value)}%</span>
          </div>
          <div
            style={{
              height: 42,
              borderRadius: 10,
              backgroundColor: withAlpha(brand.colors.fg, 0.07),
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${row.value}%`,
                height: "100%",
                borderRadius: 10,
                backgroundColor: row.color,
              }}
            />
          </div>
        </div>
      ))}
      <div
        style={{
          marginTop: 6,
          fontFamily: fontDisplay,
          fontSize: 22,
          color: withAlpha(brand.colors.fg, 0.55),
        }}
      >
        {data.caption}
      </div>
    </div>
  );
};
export { StorageBar };
