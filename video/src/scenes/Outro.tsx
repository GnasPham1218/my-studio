import React from "react";
import type { SceneProps } from "./shared";
import { Divider, Headline, Kicker, Layout } from "./shared";
import { fontMono, withAlpha } from "../lib/theme";
import { useEnter } from "../lib/motion";
import { useLayout } from "../lib/context";
import { Visual, hasVisual } from "../visuals";

export const Outro: React.FC<SceneProps> = ({ scene, brand, videoTitle }) => {
  const t = useLayout().scenes.outro;
  const pill = useEnter(14);
  return (
    <Layout align="center" vertical="center">
      <Kicker brand={brand} align="center" delay={0}>
        {scene.kicker ?? brand.channel.handle}
      </Kicker>
      <Headline
        text={scene.onScreenText ?? videoTitle}
        emphasis={scene.emphasis}
        brand={brand}
        size={t.headline}
        align="center"
        maxWidth={t.maxWidth}
        delay={3}
      />
      <Divider brand={brand} delay={10} align="center" />
      <div
        style={{
          ...pill,
          marginTop: 42,
          display: "flex",
          alignItems: "center",
          gap: 12,
          padding: "18px 34px",
          borderRadius: 999,
          border: `1px solid ${withAlpha(brand.colors.primary, 0.5)}`,
          backgroundColor: withAlpha(brand.colors.primary, 0.08),
        }}
      >
        <span
          style={{
            fontFamily: fontMono,
            fontSize: 28,
            fontWeight: 700,
            letterSpacing: 2,
            color: brand.colors.primary,
          }}
        >
          {brand.cta.handle}
        </span>
      </div>
      {hasVisual(scene) ? (
        <div
          style={{
            width: t.visualWidth,
            marginTop: 24,
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Visual scene={scene} brand={brand} />
        </div>
      ) : null}
    </Layout>
  );
};
