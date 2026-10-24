import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import type { Brand, Scene } from "../../lib/types";
import { fontDisplay, fontMono, withAlpha } from "../../lib/theme";
import { useEnter } from "../../lib/motion";
import { WIDE } from "../layout";

type Pose = "wave" | "point" | "think" | "write" | "cheer";

const POSES: Pose[] = ["wave", "point", "think", "write", "cheer"];

const poseFor = (scene: Scene): Pose => {
  const explicit = scene.visual?.pose as Pose | undefined;
  if (explicit && POSES.includes(explicit)) {
    return explicit;
  }
  if (scene.type === "hook" || scene.type === "outro") {
    return "wave";
  }
  if (scene.type === "list" || scene.type === "timeline") {
    return "write";
  }
  return "point";
};

/**
 * Nhân vật que vẽ hoàn toàn bằng SVG.
 *
 * `visual.label` là câu trong bong bóng thoại, `visual.sub` là ghi chú nhỏ
 * (phiên âm / quy tắc). Pose lấy từ `visual.pose`, nếu không có thì suy ra
 * từ loại scene.
 */
export const StickFigure: React.FC<{
  scene: Scene;
  brand: Brand;
}> = ({ scene, brand }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pose = poseFor(scene);
  const bubble = useEnter(7);
  const bob = Math.sin((frame / fps) * 2.1) * 3;
  const wave = Math.sin((frame / fps) * 5.2) * 9;
  const write = Math.sin((frame / fps) * 6.0) * 5;
  const blink = Math.floor(frame / 6) % 22 === 0;

  const label = scene.visual?.label ?? "";
  const sub = scene.visual?.sub ?? "";

  const rightHand = (() => {
    switch (pose) {
      case "wave":
        return { x: 286, y: 82 + wave, elbow: { x: 228, y: 158 } };
      case "think":
        return { x: 208, y: 132, elbow: { x: 225, y: 228 } };
      case "write":
        return { x: 294, y: 250 + write, elbow: { x: 232, y: 236 } };
      case "cheer":
        return { x: 288, y: 72, elbow: { x: 230, y: 158 } };
      case "point":
      default:
        return { x: 302, y: 180, elbow: { x: 232, y: 202 } };
    }
  })();

  const leftHand =
    pose === "cheer"
      ? { x: 58, y: 78, elbow: { x: 116, y: 160 } }
      : { x: 108, y: 286, elbow: { x: 134, y: 244 } };

  const stroke = brand.colors.fg;
  const accent = brand.colors.accent;
  const primary = brand.colors.primary;

  return (
    <div
      style={{
        width: WIDE,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <svg
        viewBox="0 0 860 470"
        width="100%"
        style={{ overflow: "visible" }}
        role="presentation"
      >
        <ellipse
          cx={185}
          cy={442}
          rx={118}
          ry={12}
          fill={withAlpha(brand.colors.fg, 0.1)}
        />

        <g transform={`translate(0 ${bob})`}>
          {/* chân */}
          <path
            d="M170 300 L132 420 M170 300 L210 420"
            stroke={stroke}
            strokeWidth={12}
            strokeLinecap="round"
            fill="none"
          />
          {/* thân */}
          <path
            d="M170 158 L170 302"
            stroke={stroke}
            strokeWidth={13}
            strokeLinecap="round"
            fill="none"
          />
          {/* tay trái */}
          <path
            d={`M170 198 L${leftHand.elbow.x} ${leftHand.elbow.y} L${leftHand.x} ${leftHand.y}`}
            stroke={stroke}
            strokeWidth={11}
            strokeLinecap="round"
            fill="none"
          />
          <circle
            cx={leftHand.x}
            cy={leftHand.y}
            r={10}
            fill={brand.colors.bg}
            stroke={stroke}
            strokeWidth={8}
          />
          {/* tay phải */}
          <path
            d={`M170 198 L${rightHand.elbow.x} ${rightHand.elbow.y} L${rightHand.x} ${rightHand.y}`}
            stroke={stroke}
            strokeWidth={11}
            strokeLinecap="round"
            fill="none"
          />
          <circle
            cx={rightHand.x}
            cy={rightHand.y}
            r={10}
            fill={brand.colors.bg}
            stroke={stroke}
            strokeWidth={8}
          />

          {/* marker khi viết */}
          {pose === "write" ? (
            <g>
              <path
                d={`M${rightHand.x} ${rightHand.y} L${rightHand.x + 34} ${
                  rightHand.y - 34
                }`}
                stroke={primary}
                strokeWidth={9}
                strokeLinecap="round"
              />
              <circle
                cx={rightHand.x + 37}
                cy={rightHand.y - 37}
                r={5}
                fill={accent}
              />
            </g>
          ) : null}

          {/* đầu */}
          <circle
            cx={170}
            cy={112}
            r={46}
            fill={brand.colors.bg}
            stroke={stroke}
            strokeWidth={12}
          />
          {/* tóc */}
          <path
            d="M138 78 Q150 58 170 62 Q190 56 204 78"
            stroke={stroke}
            strokeWidth={9}
            strokeLinecap="round"
            fill="none"
          />
          {/* mắt + miệng */}
          {blink ? (
            <path
              d="M146 108 L158 108 M182 108 L194 108"
              stroke={stroke}
              strokeWidth={6}
              strokeLinecap="round"
            />
          ) : (
            <>
              <circle cx={152} cy={108} r={4.5} fill={stroke} />
              <circle cx={188} cy={108} r={4.5} fill={stroke} />
            </>
          )}
          <path
            d="M152 132 Q170 148 188 132"
            stroke={stroke}
            strokeWidth={6}
            strokeLinecap="round"
            fill="none"
          />
          {/* cà vạt nhỏ để phân biệt giáo viên */}
          <path d="M170 158 L158 206 L170 218 L182 206 Z" fill={accent} />
        </g>

        {label ? (
          <g style={bubble}>
            <rect
              x={356}
              y={70}
              width={470}
              height={270}
              rx={24}
              fill={brand.colors.surface}
              stroke={stroke}
              strokeWidth={5}
            />
            <path
              d="M356 210 L314 246 L356 252 Z"
              fill={brand.colors.surface}
              stroke={stroke}
              strokeWidth={5}
              strokeLinejoin="round"
            />
            <foreignObject x={380} y={92} width={422} height={228}>
              <div
                style={{
                  width: "100%",
                  height: "100%",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  textAlign: "center",
                  fontFamily: fontDisplay,
                  color: brand.colors.fg,
                }}
              >
                <div
                  style={{
                    fontSize: 46,
                    lineHeight: 1.12,
                    letterSpacing: 0.2,
                  }}
                >
                  {label}
                </div>
                {sub ? (
                  <div
                    style={{
                      marginTop: 14,
                      fontFamily: fontMono,
                      fontSize: 26,
                      fontWeight: 700,
                      letterSpacing: 1,
                      color: primary,
                    }}
                  >
                    {sub}
                  </div>
                ) : null}
              </div>
            </foreignObject>
          </g>
        ) : null}
      </svg>
    </div>
  );
};
