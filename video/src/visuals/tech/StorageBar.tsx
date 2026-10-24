import React from "react";
import type { Brand } from "../../lib/types";
import { fontDisplay, fontMono, withAlpha } from "../../lib/theme";
import { useEnter, useProgress } from "../../lib/motion";
import { WIDE } from "../layout";

const StorageBar: React.FC<{ brand: Brand; delay?: number }> = ({
  brand,
  delay = 8,
}) => {
  const enter = useEnter(delay);
  const shrink = useProgress(delay + 4, 1.2);
  const remain = 100 - 69 * shrink;
  const rows = [
    { label: "fp16 · 3B", value: 100, color: withAlpha(brand.colors.fg, 0.32) },
    { label: "4-bit · 3B", value: remain, color: brand.colors.primary },
  ];

  return (
    <div style={{ ...enter, width: WIDE }}>
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
        <span>DUNG LƯỢNG MÔ HÌNH</span>
        <span style={{ color: brand.colors.primary }}>−69%</span>
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
        cùng một mô hình, nhẹ hơn gần 2/3
      </div>
    </div>
  );
};
export { StorageBar };
