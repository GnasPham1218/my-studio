import React from "react";
import type { Brand } from "../../lib/types";
import { fontDisplay, fontMono, withAlpha } from "../../lib/theme";
import { useEnter, useProgress } from "../../lib/motion";
import { WIDE } from "../layout";

const DeclineChart: React.FC<{ brand: Brand; delay?: number }> = ({
  brand,
  delay = 5,
}) => {
  const enter = useEnter(delay);
  const draw = useProgress(delay + 2, 1.1);
  const points = [
    [30, 160],
    [170, 132],
    [310, 100],
    [450, 66],
    [590, 60],
    [730, 76],
    [830, 86],
  ];
  const path = points
    .map(([x, y], index) => `${index === 0 ? "M" : "L"}${x} ${y}`)
    .join(" ");
  const last = points[points.length - 1];

  return (
    <div style={{ ...enter, width: WIDE }}>
      <div
        style={{
          fontFamily: fontMono,
          fontSize: 19,
          letterSpacing: 2,
          color: brand.colors.muted,
          marginBottom: 10,
        }}
      >
        ĐẦU TƯ / KỲ VỌNG
      </div>
      <svg width={WIDE} height={300} viewBox="0 0 860 300">
        {[50, 120, 190, 260].map((y) => (
          <line
            key={y}
            x1="20"
            x2="840"
            y1={y}
            y2={y}
            stroke={withAlpha(brand.colors.fg, 0.07)}
            strokeWidth="1"
          />
        ))}
        <path
          d={`${path} L830 290 L30 290 Z`}
          fill={`url(#declineFill)`}
          opacity={draw * 0.55}
        />
        <defs>
          <linearGradient id="declineFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={brand.colors.primary} stopOpacity="0.28" />
            <stop offset="100%" stopColor={brand.colors.primary} stopOpacity="0" />
          </linearGradient>
        </defs>
        <path
          d={path}
          fill="none"
          stroke={brand.colors.primary}
          strokeWidth="3.4"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeDasharray="1200"
          strokeDashoffset={1200 * (1 - draw)}
        />
        <circle
          cx={last[0]}
          cy={last[1]}
          r={8}
          fill={brand.colors.primary}
          opacity={draw}
        />
        <text
          x={last[0] - 12}
          y={last[1] - 22}
          textAnchor="end"
          fill={brand.colors.fg}
          fontFamily={fontMono}
          fontSize="18"
          letterSpacing="1"
          opacity={draw}
        >
          2023
        </text>
      </svg>
    </div>
  );
};
export { DeclineChart };
