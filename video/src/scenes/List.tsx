import React from "react";
import type { Brand } from "../lib/types";
import type { SceneProps } from "./shared";
import { COLUMN, Headline, Kicker, Layout } from "./shared";
import { fontDisplay, fontMono, withAlpha } from "../lib/theme";
import { useEnter } from "../lib/motion";
import { ChipIcon, DiskIcon, MemoryIcon } from "../visuals";
import { Punch } from "./Punch";

const specIcon = (text: string, brand: Brand) => {
  const color = brand.colors.primary;
  if (/npu|neural/i.test(text)) {
    return <ChipIcon size={40} color={color} />;
  }
  if (/ram|bộ nhớ trong/i.test(text)) {
    return <MemoryIcon size={40} color={color} />;
  }
  if (/ssd|ổ cứng|lưu trữ/i.test(text)) {
    return <DiskIcon size={40} color={color} />;
  }
  return null;
};

const ListRow: React.FC<{
  index: number;
  text: string;
  brand: Brand;
  format: "short" | "long";
  delay: number;
}> = ({ index, text, brand, format, delay }) => {
  const enter = useEnter(delay);
  const icon = specIcon(text, brand);
  return (
    <div
      style={{
        ...enter,
        display: "flex",
        alignItems: "center",
        gap: 24,
        padding: format === "short" ? "32px 0" : "20px 0",
        borderTop: `1px solid ${withAlpha(brand.colors.fg, 0.1)}`,
      }}
    >
      <span
        style={{
          width: 44,
          display: "flex",
          alignItems: "center",
          fontFamily: fontMono,
          fontSize: 25,
          fontWeight: 700,
          letterSpacing: 1,
          color: brand.colors.primary,
        }}
      >
        {icon ?? String(index + 1).padStart(2, "0")}
      </span>
      <span
        style={{
          fontFamily: fontDisplay,
          fontSize: format === "short" ? 48 : 34,
          fontWeight: 600,
          lineHeight: 1.25,
          color: withAlpha(brand.colors.fg, 0.94),
        }}
      >
        {text}
      </span>
    </div>
  );
};

export const List: React.FC<SceneProps> = (props) => {
  const { scene, brand, format } = props;
  const rows = scene.bullets ?? [];
  if (rows.length === 0) {
    return <Punch {...props} />;
  }
  return (
    <Layout format={format} align="left" vertical="center">
      {scene.kicker ? (
        <Kicker brand={brand} delay={0}>
          {scene.kicker}
        </Kicker>
      ) : null}
      <Headline
        text={scene.onScreenText ?? scene.narration}
        emphasis={scene.emphasis}
        brand={brand}
        size={format === "short" ? 54 : 46}
        maxWidth={format === "short" ? 860 : 1400}
        delay={2}
        weight={700}
      />
      <div style={{ width: format === "short" ? COLUMN : 1400, marginTop: 40 }}>
        {rows.map((row, index) => (
          <ListRow
            key={index}
            index={index}
            text={row}
            brand={brand}
            format={format}
            delay={7 + index * 4}
          />
        ))}
      </div>
    </Layout>
  );
};
