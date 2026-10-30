import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import type { Brand, CaptionCard } from "../lib/types";
import { fontDisplay, resolveColor, withAlpha } from "../lib/theme";
import { useLayout, useTemplate } from "../lib/context";

/**
 * Phụ đề một khối cố định:
 * - không scale/pop mỗi card,
 * - không nhảy từng từ,
 * - khung 3 dòng cố định nên card 1 dòng hay 3 dòng đều không đổi vị trí.
 * - đổi card bằng cắt thẳng tại ranh giới thời gian (không mờ dần rồi trắng),
 *   nên không có nhấp nháy giữa hai card.
 *
 * Kích thước và vị trí lấy từ `layout.caption` (theo khung hình); kiểu dáng
 * (thẻ giấy, viền chữ, màu từ đang đọc, scrim) lấy từ `template.caption`.
 */
export const Captions: React.FC<{
  cards: CaptionCard[];
  brand: Brand;
}> = ({ cards, brand }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const layout = useLayout();
  const { caption: tpl } = useTemplate();
  const cap = layout.caption;
  const time = frame / fps;
  const colors = brand.colors;
  const hasCard = Boolean(tpl.card);

  const scrimStops = tpl.scrim
    .map(([percent, alpha]) => `${withAlpha(colors.bg, alpha)} ${percent}%`)
    .join(", ");
  const scrim =
    tpl.scrim.length > 0 ? (
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 0,
          height: hasCard ? cap.scrimHeightPaper : cap.scrimHeight,
          background: `linear-gradient(to top, ${scrimStops})`,
        }}
      />
    ) : null;

  let card = cards.find((item) => time >= item.start && time < item.end);

  // Giữ card trước trong khoảng lặng ngắn giữa hai câu (template.holdGapSec).
  // Không có bước này, khung caption biến mất rồi hiện lại ~0,4-0,7s,
  // nhìn như nhấp nháy dù từng card không hề pop.
  if (!card && tpl.holdGapSec > 0) {
    for (const candidate of cards) {
      if (candidate.start > time) break;
      if (candidate.end <= time && time - candidate.end <= tpl.holdGapSec) {
        card = candidate;
      }
    }
  }

  if (!card) {
    return <AbsoluteFill style={{ pointerEvents: "none" }}>{scrim}</AbsoluteFill>;
  }

  const activeIndex = card.words.findIndex(
    (word) => time >= word.start && time < word.end,
  );

  const baseSize = hasCard ? cap.fontSizePaper : cap.fontSize;
  const size =
    tpl.fontSizeRel != null
      ? Math.round(tpl.fontSizeRel * Math.min(layout.width, layout.height))
      : baseSize;
  const bottom =
    tpl.bottomRel != null ? Math.round(tpl.bottomRel * layout.height) : cap.bottom;
  const maxWidth =
    tpl.maxWidthRel != null ? Math.round(tpl.maxWidthRel * layout.width) : cap.maxWidth;

  const textColor = resolveColor(tpl.textColor ?? "fg", colors);
  const highlightColor = tpl.highlight.color
    ? resolveColor(tpl.highlight.color, colors)
    : textColor;
  const underline = tpl.highlight.underline
    ? withAlpha(resolveColor(tpl.highlight.underline, colors), 0.3)
    : null;
  const stroke = tpl.stroke && tpl.stroke.px > 0 ? tpl.stroke : null;

  const text = (
    <div
      style={{
        maxWidth,
        fontFamily: fontDisplay,
        fontSize: size,
        fontWeight: tpl.fontWeight,
        lineHeight: 1.22,
        letterSpacing: tpl.letterSpacing,
        textAlign: "center",
        textTransform: tpl.uppercase ? "uppercase" : undefined,
        color: textColor,
        // Viền chữ vẽ phía ngoài nét chữ để không làm mỏng chữ.
        WebkitTextStroke: stroke
          ? `${stroke.px * 2}px ${resolveColor(stroke.color, colors)}`
          : undefined,
        paintOrder: stroke ? "stroke fill" : undefined,
        textShadow: tpl.textShadow
          ? `0 2px 10px ${withAlpha("#000000", 0.8)}, 0 12px 36px ${withAlpha(
              "#000000",
              0.5,
            )}`
          : undefined,
      }}
    >
      {card.words.map((word, index) => (
        <span
          key={index}
          style={{
            color: index === activeIndex ? highlightColor : textColor,
            boxShadow:
              underline && index === activeIndex
                ? `inset 0 -6px 0 ${underline}`
                : undefined,
          }}
        >
          {word.w}
          {index < card.words.length - 1 ? " " : ""}
        </span>
      ))}
    </div>
  );

  const frameStyle = tpl.card
    ? {
        width: "100%",
        height: "100%",
        boxSizing: "border-box" as const,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "18px 26px",
        borderRadius: tpl.card.radius ?? 12,
        border: `2px solid ${withAlpha(
          resolveColor(tpl.card.border ?? "fg", colors),
          tpl.card.borderAlpha ?? 0.68,
        )}`,
        backgroundColor: withAlpha(
          resolveColor(tpl.card.background ?? "surface", colors),
          tpl.card.backgroundAlpha ?? 0.96,
        ),
        boxShadow: `6px 6px 0 ${withAlpha(colors.fg, 0.06)}`,
      }
    : null;

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {scrim}
      <div
        style={{
          position: "absolute",
          left: cap.sideMargin,
          right: cap.sideMargin,
          bottom,
          height: cap.boxHeight,
          display: "flex",
          alignItems: hasCard ? "center" : "flex-end",
          justifyContent: "center",
        }}
      >
        {frameStyle ? <div style={frameStyle}>{text}</div> : text}
      </div>
    </AbsoluteFill>
  );
};
