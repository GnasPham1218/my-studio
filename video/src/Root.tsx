import React from "react";
import { Composition } from "remotion";
import { defaultProps } from "./lib/defaults";
import type { Props } from "./lib/types";
import { ExplainerVideo } from "./compositions/ExplainerVideo";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="DiveCode"
      component={ExplainerVideo}
      durationInFrames={Math.round(defaultProps.totalSec * defaultProps.fps)}
      fps={defaultProps.fps}
      width={defaultProps.width}
      height={defaultProps.height}
      defaultProps={defaultProps}
      calculateMetadata={({ props }: { props: Props }) => ({
        durationInFrames: Math.max(1, Math.round(props.totalSec * props.fps)),
        fps: props.fps,
        width: props.width,
        height: props.height,
      })}
    />
  );
};
