import React from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  staticFile,
  useVideoConfig,
} from "remotion";
import { Captions } from "../components/Captions";
import { ProgressBar } from "../components/ProgressBar";
import { SceneBackground } from "../components/SceneBackground";
import { SceneIndex } from "../components/SceneIndex";
import {
  SceneTransition,
  type TransitionEdge,
} from "../components/SceneTransition";
import { Watermark } from "../components/Watermark";
import { SceneRenderer } from "../scenes";
import { VideoProvider } from "../lib/context";
import type { Props } from "../lib/types";

export const ExplainerVideo: React.FC<Props> = (props) => {
  const { fps } = useVideoConfig();
  const { template, layout } = props;

  // Cho phép brand/template đổi font mà không phải sửa từng component.
  const fontVars = {
    "--font-display": `"${props.brand.fonts.display}", "Be Vietnam Pro", "Segoe UI", system-ui, sans-serif`,
    "--font-mono": `"${props.brand.fonts.mono}", "JetBrains Mono", "Consolas", monospace`,
  } as React.CSSProperties;

  // edges[i] = chuyển cảnh vào scene i. Cảnh đầu không có; độ dài bị kẹp tối đa
  // nửa scene ngắn hơn để cửa sổ vào/ra của một scene không chồng nhau.
  const sceneFrames = props.scenes.map((s) =>
    Math.max(1, Math.round(s.durationSec * fps)),
  );
  const edges = props.scenes.map((scene, index): TransitionEdge => {
    // Bản CapCut cắt theo từng scene nên không được chồng hình sang cảnh khác.
    if (props.capcut) {
      return { kind: "none", frames: 0 };
    }
    const kind =
      template.transition.byType[scene.type] ?? template.transition.kind;
    if (index === 0 || kind === "none") {
      return { kind, frames: 0 };
    }
    const frames = Math.min(
      Math.round(template.transition.sec * fps),
      Math.floor(sceneFrames[index - 1] / 2),
      Math.floor(sceneFrames[index] / 2),
    );
    return { kind, frames: Math.max(0, frames) };
  });

  return (
    <VideoProvider layout={layout} template={template}>
      <AbsoluteFill
        style={{ backgroundColor: props.brand.colors.bg, ...fontVars }}
      >
        {props.scenes.map((scene, index) => {
          const from = Math.round(scene.startSec * fps);
          const duration = Math.max(1, Math.round(scene.durationSec * fps));
          const enter = edges[index];
          const exit = edges[index + 1];
          // Hình vào sớm `enter.frames` để chồng lên đuôi cảnh trước; audio giữ mốc thật.
          return (
            <React.Fragment key={scene.id}>
              <Sequence
                from={from - enter.frames}
                durationInFrames={duration + enter.frames}
                name={`${scene.id} · ${scene.type}`}
              >
                <SceneTransition enter={enter} exit={exit}>
                  <SceneBackground brand={props.brand} scene={scene} />
                  <SceneRenderer
                    scene={scene}
                    brand={props.brand}
                    videoTitle={props.title}
                  />
                </SceneTransition>
              </Sequence>
              <Sequence
                from={from}
                durationInFrames={duration}
                name={`voice ${scene.id}`}
                layout="none"
              >
                <Audio src={staticFile(`${props.audioDir}/${scene.id}.wav`)} />
              </Sequence>
            </React.Fragment>
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

        {template.chrome.sceneIndex ? (
          <SceneIndex scenes={props.scenes} brand={props.brand} />
        ) : null}
        {template.chrome.progress ? (
          <ProgressBar scenes={props.scenes} brand={props.brand} />
        ) : null}
        {template.chrome.watermark.enabled ? (
          <Watermark brand={props.brand} />
        ) : null}
        {props.capcut ? null : (
          <Captions cards={props.captions} brand={props.brand} />
        )}
      </AbsoluteFill>
    </VideoProvider>
  );
};
