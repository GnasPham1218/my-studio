import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import type { TransitionKind } from "../lib/types";

export type TransitionEdge = { kind: TransitionKind; frames: number };

const NONE: TransitionEdge = { kind: "none", frames: 0 };

const ease = Easing.bezier(0.65, 0, 0.35, 1);

const progressOf = (frame: number, start: number, frames: number) =>
  frames <= 0
    ? 1
    : interpolate(frame, [start, start + frames], [0, 1], {
        easing: ease,
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });

/** Style cho cảnh đang vào, p chạy 0→1. */
const enterStyle = (kind: TransitionKind, p: number): React.CSSProperties => {
  switch (kind) {
    case "fade":
      return { opacity: p };
    case "slide":
    case "push":
      return { transform: `translateX(${(1 - p) * 100}%)` };
    case "wipe":
      return { clipPath: `inset(0 ${(1 - p) * 100}% 0 0)` };
    case "zoom":
      return { opacity: p, transform: `scale(${1.18 - 0.18 * p})` };
    case "blur":
      return { opacity: p, filter: `blur(${(1 - p) * 28}px)` };
    case "none":
    default:
      return {};
  }
};

/** Style cho cảnh đang ra (dưới cảnh mới), p chạy 0→1. */
const exitStyle = (kind: TransitionKind, p: number): React.CSSProperties => {
  switch (kind) {
    case "push":
      return { transform: `translateX(${-p * 100}%)` };
    case "zoom":
      return { transform: `scale(${1 + 0.08 * p})` };
    case "slide":
      return { transform: `translateX(${-p * 25}%)`, filter: `brightness(${1 - 0.4 * p})` };
    default:
      return {};
  }
};

/**
 * Bọc phần hình của một scene. Sequence chứa nó phải bắt đầu sớm `enter.frames`
 * frame so với mốc thật, để cảnh mới chồng lên đuôi cảnh trước; `exit` là
 * chuyển cảnh của scene kế tiếp (chiếm `exit.frames` frame cuối Sequence).
 */
export const SceneTransition: React.FC<{
  enter?: TransitionEdge;
  exit?: TransitionEdge;
  children: React.ReactNode;
}> = ({ enter = NONE, exit = NONE, children }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  // Hai cửa sổ không chồng nhau: composition giới hạn frames <= nửa scene.
  const pIn = progressOf(frame, 0, enter.frames);
  const pOut =
    exit.frames > 0
      ? progressOf(frame, durationInFrames - exit.frames, exit.frames)
      : 0;

  const inStyle = pIn < 1 ? enterStyle(enter.kind, pIn) : {};
  const outStyle = pOut > 0 ? exitStyle(exit.kind, pOut) : {};

  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <AbsoluteFill style={{ ...outStyle, ...inStyle }}>{children}</AbsoluteFill>
    </AbsoluteFill>
  );
};
