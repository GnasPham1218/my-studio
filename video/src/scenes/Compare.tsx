import React from "react";
import type { Brand } from "../lib/types";
import type { SceneProps } from "./shared";
import { COLUMN, Headline, Kicker, Layout } from "./shared";
import { fontDisplay, fontMono, withAlpha } from "../lib/theme";
import { useEnter, useProgress } from "../lib/motion";

const CompareRow: React.FC<{
  label: string;
  value: string;
  ratio: number;
  accent?: boolean;
  brand: Brand;
  format: "short" | "long";
  delay: number;
}> = ({ label, value, ratio, accent = false, brand, format, delay }) => {
  const enter = useEnter(delay);
  const grow = useProgress(delay, 0.7);
  return (
    <div style={{ ...enter, marginBottom: 40 }}>
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          gap: 20,
        }}
      >
        <span
          style={{
            fontFamily: fontMono,
            fontSize: 26,
            fontWeight: 700,
            letterSpacing: 3,
            textTransform: "uppercase",
            color: accent ? brand.colors.primary : brand.colors.muted,
          }}
        >
          {label}
        </span>
        <span
          style={{
            fontFamily: fontDisplay,
            fontSize: format === "short" ? 64 : 52,
            fontWeight: 800,
            letterSpacing: -1.5,
            color: accent ? brand.colors.primary : brand.colors.fg,
          }}
        >
          {value}
        </span>
      </div>
      <div
        style={{
          height: 12,
          marginTop: 14,
          borderRadius: 6,
          backgroundColor: withAlpha(brand.colors.fg, 0.08),
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${Math.min(100, Math.max(0, ratio * 100)) * grow}%`,
            height: "100%",
            borderRadius: 6,
            backgroundColor: accent
              ? brand.colors.primary
              : withAlpha(brand.colors.fg, 0.34),
          }}
        />
      </div>
    </div>
  );
};

export const Compare: React.FC<SceneProps> = ({ scene, brand, format }) => {
  const items = scene.compare?.items ?? [];
  const noteEnter = useEnter(20);
  return (
    <Layout format={format} align="left" vertical="center">
      {scene.kicker ? (
        <Kicker brand={brand} delay={0}>
          {scene.kicker}
        </Kicker>
      ) : null}
      <Headline
        text={scene.onScreenText ?? scene.narration}
        emphasis={scene.emphasis}
        brand={brand}
        size={format === "short" ? 54 : 46}
        delay={2}
        weight={700}
      />
      <div style={{ width: format === "short" ? COLUMN : 1400, marginTop: 46 }}>
        {items.map((item, index) => (
          <CompareRow
            key={index}
            label={item.label}
            value={item.value}
            ratio={item.ratio}
            accent={item.accent}
            brand={brand}
            format={format}
            delay={7 + index * 6}
          />
        ))}
      </div>
      {scene.compare?.note ? (
        <div
          style={{
            ...noteEnter,
            marginTop: 6,
            fontFamily: fontMono,
            fontSize: 25,
            letterSpacing: 1,
            color: brand.colors.muted,
          }}
        >
          {scene.compare.note}
        </div>
      ) : null}
    </Layout>
  );
};
