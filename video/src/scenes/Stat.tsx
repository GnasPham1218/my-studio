import React from "react";
import type { SceneProps } from "./shared";
import { Kicker, Layout, useCountUp } from "./shared";
import { withAlpha } from "../lib/theme";
import { fontDisplay, fontMono } from "../lib/theme";
import { useEnter } from "../lib/motion";
import { useLayout } from "../lib/context";
import { Visual, hasVisual } from "../visuals";

export const Stat: React.FC<SceneProps> = ({ scene, brand, videoTitle }) => {
  const t = useLayout().scenes.stat;
  const fallback = scene.onScreenText ?? scene.narration ?? videoTitle;
  const match = fallback.match(
    /(\d+(?:[.,]\d+)?)\s*(%|bit|TOPS|GB|TB|ms|tỷ|triệu)?/i,
  );
  const value = scene.stat?.value ?? match?.[1] ?? "";
  const unit = scene.stat?.unit ?? match?.[2] ?? "";
  const label = scene.stat?.label ?? fallback;
  const note = scene.stat?.note ?? "";
  const numeric = Number(value.replace(",", "."));
  const isNumeric = /^\d+(?:[.,]\d+)?$/.test(value);
  const counted = useCountUp(
    isNumeric ? numeric : 0,
    value.includes(",") ? 1 : 0,
    3,
  );
  const display = isNumeric ? counted : value;
  const visual = hasVisual(scene);
  const enter = useEnter(3);
  const labelEnter = useEnter(9);
  const noteEnter = useEnter(13);

  return (
    <Layout align="center" vertical={visual ? "top" : "center"}>
      {scene.kicker ? (
        <Kicker brand={brand} align="center" delay={0}>
          {scene.kicker}
        </Kicker>
      ) : null}
      <div
        style={{
          ...enter,
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "center",
          gap: 10,
        }}
      >
        <span
          style={{
            fontFamily: fontDisplay,
            fontSize: visual ? t.valueWithVisual : t.value,
            fontWeight: 800,
            lineHeight: 0.95,
            letterSpacing: -8,
            color: brand.colors.fg,
          }}
        >
          {display}
        </span>
        {unit ? (
          <span
            style={{
              fontFamily: fontDisplay,
              fontSize: visual ? t.unitWithVisual : t.unit,
              fontWeight: 700,
              lineHeight: 1,
              marginTop: 18,
              color: brand.colors.primary,
            }}
          >
            {unit}
          </span>
        ) : null}
      </div>
      <div
        style={{
          ...labelEnter,
          marginTop: 18,
          maxWidth: 780,
          fontFamily: fontDisplay,
          fontSize: visual ? t.labelWithVisual : t.label,
          fontWeight: 600,
          lineHeight: 1.3,
          color: withAlpha(brand.colors.fg, 0.9),
        }}
      >
        {label}
      </div>
      {note ? (
        <div
          style={{
            ...noteEnter,
            marginTop: 20,
            fontFamily: fontMono,
            fontSize: 26,
            letterSpacing: 1,
            color: brand.colors.muted,
          }}
        >
          {note}
        </div>
      ) : null}
      {visual ? (
        <div
          style={{
            width: t.visualWidth,
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginTop: 28,
          }}
        >
          <Visual scene={scene} brand={brand} />
        </div>
      ) : null}
    </Layout>
  );
};
