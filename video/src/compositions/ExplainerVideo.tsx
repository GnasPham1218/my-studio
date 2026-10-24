import React from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  staticFile,
  useVideoConfig,
} from "remotion";
import { Background } from "../components/Background";
import { PaperBackground } from "../components/PaperBackground";
import { Captions } from "../components/Captions";
import { ProgressBar } from "../components/ProgressBar";
import { SceneIndex } from "../components/SceneIndex";
import { Watermark } from "../components/Watermark";
import { SceneRenderer } from "../scenes";
import { getStyle } from "../styles";
import type { Props } from "../lib/types";

export const ExplainerVideo: React.FC<Props> = (props) => {
  const { fps } = useVideoConfig();
  const style = getStyle(props.styleId);

  // Cho phép brand đổi font mà không phải sửa từng component.
  const fontVars = {
    "--font-display": `"${props.brand.fonts.display}", "Be Vietnam Pro", "Segoe UI", system-ui, sans-serif`,
    "--font-mono": `"${props.brand.fonts.mono}", "JetBrains Mono", "Consolas", monospace`,
  } as React.CSSProperties;

  return (
    <AbsoluteFill style={{ backgroundColor: props.brand.colors.bg, ...fontVars }}>
      {props.scenes.map((scene) => {
        const from = Math.round(scene.startSec * fps);
        const duration = Math.max(1, Math.round(scene.durationSec * fps));
        return (
          <Sequence
            key={scene.id}
            from={from}
            durationInFrames={duration}
            name={`${scene.id} · ${scene.type}`}
          >
            {style.backgroundKind === "paper" ? (
              <PaperBackground
                brand={props.brand}
                seed={`${scene.id}-${scene.type}`}
              />
            ) : (
              <Background
                brand={props.brand}
                seed={`${scene.id}-${scene.type}`}
                variant={style.backgroundVariant(scene.type)}
              />
            )}
            <SceneRenderer
              scene={scene}
              brand={props.brand}
              format={props.format}
              safeArea={props.safeArea}
              videoTitle={props.title}
            />
            <Audio src={staticFile(`${props.audioDir}/${scene.id}.wav`)} />
          </Sequence>
        );
      })}

      {props.sfxDir
        ? props.scenes.map((scene) => {
            if (!scene.sfx || scene.sfx === "none") {
              return null;
            }
            const item = props.sfxCatalog[scene.sfx];
            if (!item) {
              return null;
            }
            const from = Math.max(
              0,
              Math.round((scene.startSec + (scene.sfxAtSec ?? 0)) * fps),
            );
            const duration = Math.max(
              1,
              Math.ceil(item.durationSec * fps) + 1,
            );
            return (
              <Sequence
                key={`sfx-${scene.id}`}
                from={from}
                durationInFrames={duration}
                name={`sfx ${scene.sfx} · ${scene.id}`}
              >
                <Audio
                  src={staticFile(`${props.sfxDir}/${item.file}`)}
                  volume={scene.sfxVolume ?? item.defaultVolume}
                />
              </Sequence>
            );
          })
        : null}

      {style.showSceneIndex ? (
        <SceneIndex scenes={props.scenes} brand={props.brand} />
      ) : null}
      {style.showProgress ? (
        <ProgressBar scenes={props.scenes} brand={props.brand} />
      ) : null}
      {style.showWatermark ? (
        <Watermark
          brand={props.brand}
          format={props.format}
          theme={style.captionTheme}
        />
      ) : null}
      <Captions
        cards={props.captions}
        brand={props.brand}
        format={props.format}
        safeArea={props.safeArea}
        theme={style.captionTheme}
      />
    </AbsoluteFill>
  );
};
