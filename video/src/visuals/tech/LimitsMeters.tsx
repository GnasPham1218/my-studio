import React from "react";
import type { Brand } from "../../lib/types";
import { fontDisplay, fontMono, withAlpha } from "../../lib/theme";
import { useEnter, useProgress } from "../../lib/motion";
import { CloudIcon } from "../icons";
import { WIDE } from "../layout";

const LimitsMeters: React.FC<{ brand: Brand; delay?: number }> = ({
  brand,
  delay = 6,
}) => {
  const enter = useEnter(delay);
  const grow = useProgress(delay + 2, 0.8);
  const rows = [
    { label: "Suy luận phức tạp", value: 0.28 },
    { label: "Context dài", value: 0.2 },
  ];

  return (
    <div style={{ ...enter, width: WIDE }}>
      {rows.map((row) => (
        <div key={row.label} style={{ marginBottom: 44 }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: 14,
              fontFamily: fontDisplay,
              fontSize: 28,
              fontWeight: 600,
              color: withAlpha(brand.colors.fg, 0.86),
            }}
          >
            <span>{row.label}</span>
            <span
              style={{
                fontFamily: fontMono,
                fontSize: 20,
                letterSpacing: 1,
                color: brand.colors.accent,
              }}
            >
              MÁY
            </span>
          </div>
          <div
            style={{
              height: 24,
              borderRadius: 8,
              backgroundColor: withAlpha(brand.colors.fg, 0.07),
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${row.value * 100 * grow}%`,
                height: "100%",
                borderRadius: 8,
                backgroundColor: brand.colors.accent,
              }}
            />
          </div>
        </div>
      ))}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 18,
          marginTop: 20,
        }}
      >
        <CloudIcon size={50} color={withAlpha(brand.colors.fg, 0.4)} />
        <span
          style={{
            fontFamily: fontMono,
            fontSize: 21,
            letterSpacing: 2,
            color: withAlpha(brand.colors.fg, 0.4),
          }}
        >
          PHẦN CÒN LẠI CẦN CLOUD
        </span>
      </div>
    </div>
  );
};
export { LimitsMeters };
