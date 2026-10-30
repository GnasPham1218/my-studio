import React from "react";
import type { Brand } from "../lib/types";
import type { SceneProps } from "./shared";
import { Headline, Kicker, Layout } from "./shared";
import { fontDisplay, fontMono, withAlpha } from "../lib/theme";
import { useEnter } from "../lib/motion";
import { useLayout } from "../lib/context";

const TimelineRow: React.FC<{
  label: string;
  text: string;
  active?: boolean;
  brand: Brand;
  delay: number;
}> = ({ label, text, active = false, brand, delay }) => {
  const t = useLayout().scenes.timeline;
  const enter = useEnter(delay);
  return (
    <div
      style={{
        ...enter,
        display: "flex",
        alignItems: "flex-start",
        gap: 26,
        padding: `${t.rowPaddingY}px 0`,
      }}
    >
      <span
        style={{
          marginTop: 8,
          width: 16,
          height: 16,
          flexShrink: 0,
          borderRadius: "50%",
          border: `3px solid ${
            active ? brand.colors.primary : withAlpha(brand.colors.fg, 0.28)
          }`,
          backgroundColor: active ? brand.colors.primary : brand.colors.bg,
          boxShadow: active
            ? `0 0 20px ${withAlpha(brand.colors.primary, 0.55)}`
            : undefined,
        }}
      />
      <div>
        <div
          style={{
            fontFamily: fontMono,
            fontSize: 26,
            fontWeight: 700,
            letterSpacing: 2.5,
            color: active ? brand.colors.primary : brand.colors.muted,
          }}
        >
          {label}
        </div>
        <div
          style={{
            marginTop: 6,
            fontFamily: fontDisplay,
            fontSize: t.rowText,
            fontWeight: active ? 700 : 600,
            lineHeight: 1.25,
            color: active
              ? brand.colors.fg
              : withAlpha(brand.colors.fg, 0.72),
          }}
        >
          {text}
        </div>
      </div>
    </div>
  );
};

export const Timeline: React.FC<SceneProps> = ({ scene, brand }) => {
  const t = useLayout().scenes.timeline;
  const items = scene.timeline ?? [];
  return (
    <Layout align="left" vertical="center">
      {scene.kicker ? (
        <Kicker brand={brand} delay={0}>
          {scene.kicker}
        </Kicker>
      ) : null}
      <Headline
        text={scene.onScreenText ?? scene.narration}
        emphasis={scene.emphasis}
        brand={brand}
        size={t.headline}
        delay={2}
        weight={700}
      />
      <div
        style={{
          position: "relative",
          width: t.width,
          marginTop: 34,
        }}
      >
        <div
          style={{
            position: "absolute",
            left: 7,
            top: 34,
            bottom: 34,
            width: 2,
            backgroundColor: withAlpha(brand.colors.fg, 0.12),
          }}
        />
        {items.map((item, index) => (
          <TimelineRow
            key={index}
            label={item.label}
            text={item.text}
            active={item.active}
            brand={brand}
            delay={6 + index * 5}
          />
        ))}
      </div>
    </Layout>
  );
};
