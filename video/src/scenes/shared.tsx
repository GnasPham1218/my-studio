import React, { useMemo } from "react";
import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { Brand, SafeArea, Scene } from "../lib/types";
import { fontDisplay, fontMono, withAlpha } from "../lib/theme";
import { useEnter, useProgress } from "../lib/motion";

export type SceneProps = {
  scene: Scene;
  brand: Brand;
  format: "short" | "long";
  safeArea: SafeArea;
  videoTitle: string;
};

// Một trục dọc duy nhất cho mọi scene:
// header ~13%, nội dung 25–70%, caption 78–88%.
export const COLUMN = 900;

const normalize = (value: string) =>
  value
    .toLowerCase()
    .normalize("NFC")
    .replace(/[^\p{L}\p{N}%]+/gu, "");

export const Layout: React.FC<{
  format: "short" | "long";
  align?: "left" | "center";
  vertical?: "top" | "center" | "bottom";
  children: React.ReactNode;
}> = ({ format, align = "left", vertical = "top", children }) => (
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
      paddingTop: format === "short" ? 236 : 90,
      paddingBottom: format === "short" ? 470 : 150,
      paddingLeft: format === "short" ? 90 : 150,
      paddingRight: format === "short" ? 90 : 150,
    }}
  >
    {children}
  </AbsoluteFill>
);

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
  maxWidth = COLUMN,
  delay = 0,
  weight = 800,
}) => {
  const enter = useEnter(delay);
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
        maxWidth,
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
