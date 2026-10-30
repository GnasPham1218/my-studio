import React from "react";
import { AbsoluteFill } from "remotion";
import { SceneBackground } from "../components/SceneBackground";
import { Watermark } from "../components/Watermark";
import { Headline } from "../scenes/shared";
import { Visual, hasVisual } from "../visuals";
import { VideoProvider } from "../lib/context";
import { fontMono, withAlpha } from "../lib/theme";
import type { Props } from "../lib/types";

/** Frame chụp thumbnail: lúc mọi hiệu ứng vào cảnh đã xong. */
export const THUMBNAIL_FRAME = 59;

/**
 * Ảnh bìa cùng khung hình với video: nền hero, tiêu đề lớn có từ nhấn màu,
 * visual của cảnh hook và tên kênh. Chữ lấy từ `props.thumbnail`, thiếu thì
 * dùng title + emphasis của cảnh đầu.
 */
export const Thumbnail: React.FC<Props> = (props) => {
  const { brand, layout, template } = props;
  const hook = props.scenes[0];
  const text = props.thumbnail?.text ?? props.title;
  const emphasis = props.thumbnail?.emphasis ?? hook?.emphasis ?? [];
  const kicker = props.thumbnail?.kicker ?? hook?.kicker ?? brand.channel.handle;
  const vertical = layout.height > layout.width;
  // Chữ thumbnail to hơn headline trong video để đọc được ở cỡ ảnh nhỏ.
  const size = Math.round(layout.scenes.hook.headline * (vertical ? 1.2 : 1.1));

  const fontVars = {
    "--font-display": `"${brand.fonts.display}", "Be Vietnam Pro", "Segoe UI", system-ui, sans-serif`,
    "--font-mono": `"${brand.fonts.mono}", "JetBrains Mono", "Consolas", monospace`,
  } as React.CSSProperties;

  return (
    <VideoProvider layout={layout} template={template}>
      <AbsoluteFill style={{ backgroundColor: brand.colors.bg, ...fontVars }}>
        {hook ? <SceneBackground brand={brand} scene={hook} /> : null}
        <AbsoluteFill
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            textAlign: "center",
            paddingTop: layout.padding.top,
            paddingBottom: layout.padding.bottom,
            paddingLeft: layout.padding.left,
            paddingRight: layout.padding.right,
            gap: vertical ? 56 : 32,
          }}
        >
          <div
            style={{
              padding: "12px 28px",
              borderRadius: 999,
              border: `2px solid ${withAlpha(brand.colors.primary, 0.6)}`,
              backgroundColor: withAlpha(brand.colors.primary, 0.12),
              fontFamily: fontMono,
              fontSize: vertical ? 34 : 28,
              fontWeight: 700,
              letterSpacing: 4,
              textTransform: "uppercase",
              color: brand.colors.primary,
            }}
          >
            {kicker}
          </div>
          <div style={{ textShadow: `0 6px 30px ${withAlpha("#000000", 0.6)}` }}>
            <Headline
              text={text}
              emphasis={emphasis}
              brand={brand}
              size={size}
              align="center"
              maxWidth={layout.width - layout.padding.left - layout.padding.right}
              weight={900}
            />
          </div>
          {hook && hasVisual(hook) ? (
            <div
              style={{
                width: layout.scenes.hook.visualWidth,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Visual scene={hook} brand={brand} />
            </div>
          ) : null}
        </AbsoluteFill>
        <Watermark brand={brand} />
      </AbsoluteFill>
    </VideoProvider>
  );
};
