import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import type { Brand, CaptionCard, SafeArea } from "../lib/types";
import type { CaptionTheme } from "../styles";
import { fontDisplay, withAlpha } from "../lib/theme";

/**
 * Phụ đề một khối cố định:
 * - không scale/pop mỗi card,
 * - không nhảy từng từ,
 * - khung 3 dòng cố định nên card 1 dòng hay 3 dòng đều không đổi vị trí.
 * - đổi card bằng cắt thẳng tại ranh giới thời gian (không mờ dần rồi trắng),
 *   nên không có nhấp nháy giữa hai card.
 *
 * `theme="paper"` dùng cho style whiteboard: chữ tối trên thẻ giấy, viền marker.
 */
export const Captions: React.FC<{
  cards: CaptionCard[];
  brand: Brand;
  format: "short" | "long";
  safeArea: SafeArea;
  theme?: CaptionTheme;
}> = ({ cards, brand, format, safeArea, theme = "tech" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const time = frame / fps;
  const paper = theme === "paper";

  const scrim = (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: 0,
        height: paper
          ? format === "short"
            ? 560
            : 280
          : format === "short"
            ? 620
            : 300,
        background: paper
          ? `linear-gradient(to top, ${withAlpha(
              brand.colors.bg,
              0.98,
            )} 0%, ${withAlpha(brand.colors.bg, 0.86)} 28%, transparent 100%)`
          : format === "short"
            ? `linear-gradient(to top, ${withAlpha(
                brand.colors.bg,
                0.94,
              )} 0%, ${withAlpha(brand.colors.bg, 0.72)} 30%, transparent 100%)`
            : `linear-gradient(to top, ${withAlpha(
                brand.colors.bg,
                0.85,
              )} 0%, transparent 100%)`,
      }}
    />
  );

  let card = cards.find(
    (item) => time >= item.start && time < item.end,
  );

  // Whiteboard: giữ card trước trong khoảng lặng ngắn giữa hai câu.
  // Không có bước này, khung caption biến mất rồi hiện lại ~0,4-0,7s,
  // nhìn như nhấp nháy dù từng card không hề pop.
  if (!card && paper) {
    for (const candidate of cards) {
      if (candidate.start > time) break;
      if (candidate.end <= time && time - candidate.end <= 0.85) {
        card = candidate;
      }
    }
  }

  if (!card) {
    return (
      <AbsoluteFill style={{ pointerEvents: "none" }}>
        {scrim}
      </AbsoluteFill>
    );
  }

  const activeIndex = card.words.findIndex(
    (word) => time >= word.start && time < word.end,
  );

  const size = format === "short" ? (paper ? 54 : 52) : paper ? 40 : 42;
  const bottom = format === "short" ? 300 : safeArea.bottom;
  // Đủ chỗ cho 3 dòng; can đáy nên card 1 dòng hay 3 dòng đều không nhảy.
  const boxHeight = format === "short" ? 214 : 160;
  const maxWidth = format === "short" ? 920 : 1400;

  const text = (
    <div
      style={{
        maxWidth,
        fontFamily: fontDisplay,
        fontSize: size,
        fontWeight: paper ? 400 : 600,
        lineHeight: 1.22,
        letterSpacing: paper ? 0.2 : -0.2,
        textAlign: "center",
        color: brand.colors.fg,
        textShadow: paper
          ? undefined
          : `0 2px 10px ${withAlpha(
              "#000000",
              0.8,
            )}, 0 12px 36px ${withAlpha("#000000", 0.5)}`,
      }}
    >
      {card.words.map((word, index) => (
        <span
          key={index}
          style={{
            color:
              index === activeIndex ? brand.colors.primary : brand.colors.fg,
            boxShadow:
              paper && index === activeIndex
                ? `inset 0 -6px 0 ${withAlpha(brand.colors.accent, 0.3)}`
                : undefined,
          }}
        >
          {word.w}
          {index < card.words.length - 1 ? " " : ""}
        </span>
      ))}
    </div>
  );

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {scrim}
      <div
        style={{
          position: "absolute",
          left: format === "short" ? 64 : 120,
          right: format === "short" ? 64 : 120,
          bottom,
          height: boxHeight,
          display: "flex",
          alignItems: paper ? "center" : "flex-end",
          justifyContent: "center",
        }}
      >
        {paper ? (
          <div
            style={{
              width: "100%",
              height: "100%",
              boxSizing: "border-box",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "18px 26px",
              borderRadius: 12,
              border: `2px solid ${withAlpha(brand.colors.fg, 0.68)}`,
              backgroundColor: withAlpha(brand.colors.surface, 0.96),
              boxShadow: `6px 6px 0 ${withAlpha(brand.colors.fg, 0.06)}`,
            }}
          >
            {text}
          </div>
        ) : (
          text
        )}
      </div>
    </AbsoluteFill>
  );
};
