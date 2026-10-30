import React from "react";
import { spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { SceneProps } from "./shared";
import { Headline, Kicker, Layout } from "./shared";
import { fontDisplay, fontMono, withAlpha } from "../lib/theme";
import { useLayout } from "../lib/context";
import { Punch } from "./Punch";

export const Chart: React.FC<SceneProps> = (props) => {
  const { scene, brand } = props;
  const t = useLayout().scenes.chart;
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const data = scene.chart?.data ?? [];
  if (data.length === 0) {
    return <Punch {...props} />;
  }
  const max = Math.max(...data.map((item) => item.value), 1);
  const maxHeight = t.barAreaHeight;

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
          display: "flex",
          alignItems: "flex-end",
          gap: 30,
          height: maxHeight + 110,
          marginTop: 40,
        }}
      >
        {data.map((item, index) => {
          const grow = spring({
            frame: frame - 8 - index * 4,
            fps,
            config: { damping: 200, mass: 0.9 },
            durationInFrames: 24,
          });
          return (
            <div
              key={index}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "flex-end",
                width: 150,
              }}
            >
              <div
                style={{
                  fontFamily: fontMono,
                  fontSize: 30,
                  fontWeight: 700,
                  color: brand.colors.fg,
                  marginBottom: 10,
                  opacity: grow,
                }}
              >
                {Math.round(item.value * grow)}
                {scene.chart?.unit ?? ""}
              </div>
              <div
                style={{
                  width: "100%",
                  height: (item.value / max) * maxHeight * grow,
                  borderRadius: "10px 10px 3px 3px",
                  background: `linear-gradient(to top, ${brand.colors.primary}, ${withAlpha(
                    brand.colors.primary,
                    0.4,
                  )})`,
                }}
              />
              <div
                style={{
                  marginTop: 14,
                  fontFamily: fontDisplay,
                  fontSize: 26,
                  fontWeight: 600,
                  color: brand.colors.muted,
                  textAlign: "center",
                }}
              >
                {item.label}
              </div>
            </div>
          );
        })}
      </div>
    </Layout>
  );
};
