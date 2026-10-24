import React from "react";
import type { SceneProps } from "./shared";
import { COLUMN, Divider, Headline, Kicker, Layout } from "./shared";
import { sizes } from "../lib/theme";
import { Visual, hasVisual } from "../visuals";

export const Punch: React.FC<SceneProps> = ({
  scene,
  brand,
  format,
  videoTitle,
}) => {
  const visual = hasVisual(scene);
  const size = format === "short" ? (visual ? 68 : 92) : visual ? 46 : sizes(format).h1;
  const text = scene.onScreenText ?? videoTitle;
  const quote = scene.type === "quote";

  return (
    <Layout
      format={format}
      align="left"
      vertical={visual ? "top" : "center"}
    >
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
        maxWidth={format === "short" ? 880 : 1400}
        delay={3}
        weight={quote ? 600 : 800}
      />
      <Divider brand={brand} delay={10} />
      {visual ? (
        <div
          style={{
            width: COLUMN,
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginTop: 36,
          }}
        >
          <Visual scene={scene} brand={brand} format={format} />
        </div>
      ) : null}
    </Layout>
  );
};
