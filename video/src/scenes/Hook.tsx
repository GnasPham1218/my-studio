import React from "react";
import type { SceneProps } from "./shared";
import { Divider, Headline, Kicker, Layout } from "./shared";
import { fontDisplay } from "../lib/theme";
import { useEnter } from "../lib/motion";
import { useLayout } from "../lib/context";
import { Visual, hasVisual } from "../visuals";

export const Hook: React.FC<SceneProps> = ({ scene, brand, videoTitle }) => {
  const t = useLayout().scenes.hook;
  const size = scene.visual?.kind === "phone" ? t.headlineWithPhone : t.headline;
  const text = scene.onScreenText ?? videoTitle;
  const tagline = useEnter(14);

  return (
    <Layout align="center" vertical="center">
      <Kicker brand={brand} align="center" delay={0}>
        {scene.kicker ?? brand.channel.handle}
      </Kicker>
      <Headline
        text={text}
        emphasis={scene.emphasis}
        brand={brand}
        size={size}
        align="center"
        maxWidth={t.maxWidth}
        delay={3}
      />
      <Divider brand={brand} delay={10} align="center" />
      <div
        style={{
          ...tagline,
          marginTop: 30,
          fontFamily: fontDisplay,
          fontSize: t.tagline,
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
            width: t.visualWidth,
            marginTop: 34,
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
