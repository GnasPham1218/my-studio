import React from "react";
import type { Brand } from "../../lib/types";
import { fontDisplay, fontMono, withAlpha } from "../../lib/theme";
import { useEnter, useProgress } from "../../lib/motion";
import { useLayout } from "../../lib/context";

export type LoopData = {
  nodes: { title: string; sub: string }[];
  caption: string;
};

// Vị trí hai nút trong viewBox 860x400.
const NODE_X = [20, 620];

const LoopDiagram: React.FC<{
  brand: Brand;
  data: LoopData;
  delay?: number;
}> = ({ brand, data, delay = 5 }) => {
  const enter = useEnter(delay);
  const draw = useProgress(delay + 3, 0.9);
  const { wide } = useLayout();
  const primary = brand.colors.primary;

  return (
    <div style={{ ...enter, width: wide }}>
      <svg width={wide} height={400} viewBox="0 0 860 400">
        {data.nodes.map((node, index) => {
          const x = NODE_X[index];
          return (
            <g key={node.title}>
              <rect
                x={x}
                y={105}
                width={220}
                height={132}
                rx={22}
                fill={withAlpha(brand.colors.surface, 0.75)}
                stroke={withAlpha(brand.colors.fg, 0.16)}
              />
              <text
                x={x + 110}
                y={158}
                textAnchor="middle"
                fill={brand.colors.fg}
                fontFamily={fontMono}
                fontSize="30"
                fontWeight="700"
                letterSpacing="3"
              >
                {node.title}
              </text>
              <text
                x={x + 110}
                y={196}
                textAnchor="middle"
                fill={brand.colors.muted}
                fontFamily={fontDisplay}
                fontSize="23"
              >
                {node.sub}
              </text>
            </g>
          );
        })}

        <path
          d="M252 148H608"
          stroke={primary}
          strokeWidth="2.5"
          strokeDasharray="356"
          strokeDashoffset={356 * (1 - draw)}
        />
        <path
          d="M596 138l14 10-14 10"
          fill="none"
          stroke={primary}
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity={draw}
        />

        <path
          d="M608 220C540 340 320 340 252 220"
          fill="none"
          stroke={withAlpha(primary, 0.55)}
          strokeWidth="2.5"
          strokeDasharray="460"
          strokeDashoffset={460 * (1 - draw)}
        />
        <path
          d="M266 230l-14-10 14-10"
          fill="none"
          stroke={withAlpha(primary, 0.55)}
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity={draw}
        />
        <text
          x={430}
          y={384}
          textAnchor="middle"
          fill={brand.colors.muted}
          fontFamily={fontMono}
          fontSize="19"
          letterSpacing="2"
          opacity={draw}
        >
          {data.caption}
        </text>
      </svg>
    </div>
  );
};
export { LoopDiagram };
