import React from "react";
import type { SceneProps } from "./shared";
import { Divider, Headline, Kicker, Layout } from "./shared";
import { fontDisplay, sizes } from "../lib/theme";
import { useEnter } from "../lib/motion";
import { Visual, hasVisual } from "../visuals";

export const Hook: React.FC<SceneProps> = ({
  scene,
  brand,
  format,
  videoTitle,
}) => {
  const size = format === "short" ? (scene.visual?.kind === "phone" ? 92 : 100) : sizes(format).hero;
  const text = scene.onScreenText ?? videoTitle;
  const tagline = useEnter(14);

  return (
    <Layout format={format} align="center" vertical="center">
      <Kicker brand={brand} align="center" delay={0}>
        {scene.kicker ?? brand.channel.handle}
      </Kicker>
      <Headline
        text={text}
        emphasis={scene.emphasis}
        brand={brand}
        size={size}
        align="center"
        maxWidth={format === "short" ? 840 : 1400}
        delay={3}
      />
      <Divider brand={brand} delay={10} align="center" />
      <div
        style={{
          ...tagline,
          marginTop: 30,
          fontFamily: fontDisplay,
          fontSize: format === "short" ? 31 : 28,
          fontWeight: 500,
          letterSpacing: 0.4,
          color: brand.colors.muted,
        }}
      >
        {brand.channel.tagline}
      </div>
      {hasVisual(scene) ? (
        <div
          style={{
            width: format === "short" ? 860 : 1200,
            marginTop: 34,
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
