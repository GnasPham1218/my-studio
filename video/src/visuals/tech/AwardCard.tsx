import React from "react";
import type { Brand } from "../../lib/types";
import { fontDisplay, fontMono, withAlpha } from "../../lib/theme";
import { useEnter } from "../../lib/motion";
import { WIDE } from "../layout";

const AwardCard: React.FC<{ brand: Brand; year: string; delay?: number }> = ({
  brand,
  year,
  delay = 5,
}) => {
  const enter = useEnter(delay);
  const rows = [
    { label: "AI agents", active: false },
    { label: "Small language models", active: true },
    { label: "Long-acting HIV prevention", active: false },
  ];

  return (
    <div
      style={{
        ...enter,
        width: WIDE,
        borderRadius: 26,
        border: `1px solid ${withAlpha(brand.colors.fg, 0.14)}`,
        background: `linear-gradient(180deg, ${withAlpha(
          brand.colors.surface,
          0.92,
        )}, ${withAlpha(brand.colors.bg, 0.92)})`,
        padding: "40px 42px 36px",
        boxShadow: `0 40px 90px ${withAlpha("#000000", 0.45)}`,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
        }}
      >
        <span
          style={{
            fontFamily: fontMono,
            fontSize: 19,
            fontWeight: 700,
            letterSpacing: 3,
            color: brand.colors.muted,
          }}
        >
          MIT TECHNOLOGY REVIEW
        </span>
        <span
          style={{
            fontFamily: fontMono,
            fontSize: 19,
            fontWeight: 700,
            letterSpacing: 2,
            color: brand.colors.primary,
          }}
        >
          {year}
        </span>
      </div>
      <div
        style={{
          marginTop: 20,
          fontFamily: fontDisplay,
          fontSize: 44,
          fontWeight: 700,
          lineHeight: 1.2,
          color: brand.colors.fg,
        }}
      >
        10 Breakthrough Technologies
      </div>
      <div style={{ marginTop: 28 }}>
        {rows.map((row, index) => (
          <div
            key={row.label}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 18,
              padding: "22px 22px",
              marginTop: index === 0 ? 0 : 10,
              borderRadius: 14,
              border: `1px solid ${
                row.active
                  ? withAlpha(brand.colors.primary, 0.42)
                  : "transparent"
              }`,
              backgroundColor: row.active
                ? withAlpha(brand.colors.primary, 0.08)
                : "transparent",
            }}
          >
            <span
              style={{
                fontFamily: fontMono,
                fontSize: 17,
                fontWeight: 700,
                color: row.active
                  ? brand.colors.primary
                  : withAlpha(brand.colors.fg, 0.3),
              }}
            >
              {String(index + 1).padStart(2, "0")}
            </span>
            <span
              style={{
                fontFamily: fontDisplay,
                fontSize: 28,
                fontWeight: row.active ? 700 : 500,
                color: row.active
                  ? brand.colors.fg
                  : withAlpha(brand.colors.fg, 0.5),
              }}
            >
              {row.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
export { AwardCard };
