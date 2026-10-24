import React from "react";
import type { SceneProps } from "./shared";
import { Divider, Headline, Kicker, Layout } from "./shared";
import { fontDisplay, fontMono, withAlpha } from "../lib/theme";
import { useEnter } from "../lib/motion";
import { Visual, hasVisual } from "../visuals";

export const Outro: React.FC<SceneProps> = ({
  scene,
  brand,
  format,
  videoTitle,
}) => {
  const pill = useEnter(14);
  return (
    <Layout format={format} align="center" vertical="center">
      <Kicker brand={brand} align="center" delay={0}>
        {scene.kicker ?? brand.channel.handle}
      </Kicker>
      <Headline
        text={scene.onScreenText ?? videoTitle}
        emphasis={scene.emphasis}
        brand={brand}
        size={format === "short" ? 68 : 62}
        align="center"
        maxWidth={format === "short" ? 880 : 1300}
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
            width: format === "short" ? 780 : 1000,
            marginTop: 24,
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Visual scene={scene} brand={brand} format={format} />
        </div>
      ) : null}
    </Layout>
  );
};
