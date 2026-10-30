import React, { useMemo } from "react";
import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { Brand, Scene } from "../lib/types";
import { fontDisplay, fontMono, withAlpha } from "../lib/theme";
import { useEnter, useProgress } from "../lib/motion";
import { useLayout } from "../lib/context";

export type SceneProps = {
  scene: Scene;
  brand: Brand;
  videoTitle: string;
};

const normalize = (value: string) =>
  value
    .toLowerCase()
    .normalize("NFC")
    .replace(/[^\p{L}\p{N}%]+/gu, "");

/**
 * Khung chung của mọi scene. Một trục duy nhất theo layout.padding:
 * header ở trên, nội dung ở giữa, chừa chỗ cho caption ở dưới.
 */
export const Layout: React.FC<{
  align?: "left" | "center";
  vertical?: "top" | "center" | "bottom";
  children: React.ReactNode;
}> = ({ align = "left", vertical = "top", children }) => {
  const { padding } = useLayout();
  return (
  <AbsoluteFill
    style={{
      display: "flex",
      flexDirection: "column",
      justifyContent:
        vertical === "center"
          ? "center"
          : vertical === "bottom"
            ? "flex-end"
            : "flex-start",
      alignItems: align === "center" ? "center" : "flex-start",
      textAlign: align === "center" ? "center" : "left",
      paddingTop: padding.top,
      paddingBottom: padding.bottom,
      paddingLeft: padding.left,
      paddingRight: padding.right,
    }}
  >
    {children}
  </AbsoluteFill>
  );
};

export const Kicker: React.FC<{
  children: React.ReactNode;
  brand: Brand;
  align?: "left" | "center";
  delay?: number;
}> = ({ children, brand, align = "left", delay = 0 }) => {
  const enter = useEnter(delay);
  return (
    <div
      style={{
        ...enter,
        display: "flex",
        alignItems: "center",
        justifyContent: align === "center" ? "center" : "flex-start",
        gap: 16,
        marginBottom: 26,
      }}
    >
      <span
        style={{
          width: 26,
          height: 3,
          borderRadius: 2,
          backgroundColor: brand.colors.primary,
        }}
      />
      <span
        style={{
          fontFamily: fontMono,
          fontSize: 27,
          fontWeight: 700,
          letterSpacing: 5,
          textTransform: "uppercase",
          color: brand.colors.muted,
        }}
      >
        {children}
      </span>
    </div>
  );
};

export const Headline: React.FC<{
  text: string;
  emphasis?: string[];
  brand: Brand;
  size: number;
  align?: "left" | "center";
  maxWidth?: number;
  delay?: number;
  weight?: number;
}> = ({
  text,
  emphasis = [],
  brand,
  size,
  align = "left",
  maxWidth,
  delay = 0,
  weight = 800,
}) => {
  const enter = useEnter(delay);
  const layout = useLayout();
  const words = useMemo(() => text.split(" "), [text]);
  const keys = useMemo(() => {
    const set = new Set<string>();
    (emphasis ?? []).forEach((phrase) => {
      phrase
        .toLowerCase()
        .split(/[^\p{L}\p{N}%]+/u)
        .filter(Boolean)
        .forEach((word) => set.add(normalize(word)));
    });
    return set;
  }, [emphasis]);

  return (
    <div
      style={{
        ...enter,
        fontFamily: fontDisplay,
        fontWeight: weight,
        fontSize: size,
        lineHeight: 1.14,
        letterSpacing: -1.5,
        color: brand.colors.fg,
        maxWidth: maxWidth ?? layout.column,
        textAlign: align,
      }}
    >
      {words.map((word, index) => (
        <span
          key={index}
          style={{
            color: keys.has(normalize(word)) ? brand.colors.primary : undefined,
          }}
        >
          {word}
          {index < words.length - 1 ? " " : ""}
        </span>
      ))}
    </div>
  );
};

export const Divider: React.FC<{
  brand: Brand;
  delay?: number;
  width?: number;
  align?: "left" | "center";
}> = ({ brand, delay = 10, width = 104, align = "left" }) => {
  const progress = useProgress(delay, 0.45);
  return (
    <div
      style={{
        width,
        height: 4,
        borderRadius: 2,
        marginTop: 34,
        opacity: progress,
        transform: `translateY(${(1 - progress) * 10}px) scaleX(${progress})`,
        transformOrigin: align === "center" ? "center" : "left",
        background: `linear-gradient(90deg, ${brand.colors.primary}, ${withAlpha(
          brand.colors.primary,
          0,
        )})`,
      }}
    />
  );
};

export const useCountUp = (target: number, decimals: number, delay: number) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const progress = spring({
    frame: frame - delay,
    fps,
    config: { damping: 200, mass: 1.1 },
    durationInFrames: Math.round(fps * 0.9),
  });
  const value = target * progress;
  return decimals > 0 ? value.toFixed(decimals) : Math.round(value).toString();
};
