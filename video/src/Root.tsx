import React from "react";
import { Composition } from "remotion";
import { defaultProps } from "./lib/defaults";
import type { Props } from "./lib/types";
import { ExplainerVideo } from "./compositions/ExplainerVideo";
import { THUMBNAIL_FRAME, Thumbnail } from "./compositions/Thumbnail";

const metadata = ({ props }: { props: Props }) => ({
  durationInFrames: Math.max(1, Math.round(props.totalSec * props.fps)),
  fps: props.fps,
  width: props.width,
  height: props.height,
});

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="DiveCode"
        component={ExplainerVideo}
        durationInFrames={Math.round(defaultProps.totalSec * defaultProps.fps)}
        fps={defaultProps.fps}
        width={defaultProps.width}
        height={defaultProps.height}
        defaultProps={defaultProps}
        calculateMetadata={metadata}
      />
      {/* Ảnh bìa: chỉ cần đủ frame để hiệu ứng vào cảnh chạy xong. */}
      <Composition
        id="Thumbnail"
        component={Thumbnail}
        durationInFrames={THUMBNAIL_FRAME + 1}
        fps={defaultProps.fps}
        width={defaultProps.width}
        height={defaultProps.height}
        defaultProps={defaultProps}
        calculateMetadata={({ props }: { props: Props }) => ({
          ...metadata({ props }),
          durationInFrames: THUMBNAIL_FRAME + 1,
        })}
      />
    </>
  );
};
