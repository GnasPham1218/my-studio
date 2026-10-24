import React from "react";
import type { Brand } from "../../lib/types";
import { fontDisplay, fontMono, withAlpha } from "../../lib/theme";
import { useEnter, useProgress } from "../../lib/motion";
import { ChipIcon } from "../icons";
import { WIDE } from "../layout";

const ShrinkDiagram: React.FC<{ brand: Brand; delay?: number }> = ({
  brand,
  delay = 6,
}) => {
  const enter = useEnter(delay);
  const grow = useProgress(delay + 2, 0.9);
  const rows = [
    { label: "BERT · 110M", width: 1, color: withAlpha(brand.colors.fg, 0.3) },
    { label: "DistilBERT · 66M", width: 0.6, color: withAlpha(brand.colors.fg, 0.5) },
    { label: "MobileBERT · 25M", width: 0.23, color: brand.colors.primary },
  ];

  return (
    <div
      style={{
        ...enter,
        width: WIDE,
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
          SỐ THAM SỐ
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
                {Math.round(row.width * 100)}%
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
                  width: `${row.width * 100 * grow}%`,
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
          nhỏ hơn, vẫn chạy được trên điện thoại
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
