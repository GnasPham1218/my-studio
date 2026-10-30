import React from "react";
import type { SceneProps } from "./shared";
import { Divider, Headline, Kicker, Layout } from "./shared";
import { useLayout } from "../lib/context";
import { Visual, hasVisual } from "../visuals";

export const Punch: React.FC<SceneProps> = ({ scene, brand, videoTitle }) => {
  const t = useLayout().scenes.punch;
  const visual = hasVisual(scene);
  const size = visual ? t.headlineWithVisual : t.headline;
  const text = scene.onScreenText ?? videoTitle;
  const quote = scene.type === "quote";

  return (
    <Layout align="left" vertical={visual ? "top" : "center"}>
      {scene.kicker ? (
        <Kicker brand={brand} delay={0}>
          {scene.kicker}
        </Kicker>
      ) : null}
      <Headline
        text={text}
        emphasis={scene.emphasis}
        brand={brand}
        size={size}
        maxWidth={t.maxWidth}
        delay={3}
        weight={quote ? 600 : 800}
      />
      <Divider brand={brand} delay={10} />
      {visual ? (
        <div
          style={{
            width: t.visualWidth,
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginTop: 36,
          }}
        >
          <Visual scene={scene} brand={brand} />
        </div>
      ) : null}
    </Layout>
  );
};
