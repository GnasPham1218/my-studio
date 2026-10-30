import React from "react";
import { AbsoluteFill } from "remotion";
import type { Brand, Scene } from "../lib/types";
import { useTemplate } from "../lib/context";
import { Background } from "./Background";
import { PaperBackground } from "./PaperBackground";

/**
 * Chọn nền theo `template.background.kind`:
 * - tech: nền tối có quầng sáng "thở", biến thể theo loại scene,
 * - paper: giấy kẻ dòng (whiteboard),
 * - solid: một màu `brand.colors.bg`,
 * - gradient: gradient tuyến tính (mặc định bg → surface).
 *
 * Hai kind sau cho phép tái tạo nền của video mẫu mà không cần viết component.
 */
export const SceneBackground: React.FC<{ brand: Brand; scene: Scene }> = ({
  brand,
  scene,
}) => {
  const { background } = useTemplate();
  const seed = `${scene.id}-${scene.type}`;

  switch (background.kind) {
    case "paper":
      return <PaperBackground brand={brand} seed={seed} />;
    case "solid":
      return <AbsoluteFill style={{ backgroundColor: brand.colors.bg }} />;
    case "gradient": {
      const stops =
        background.gradient.stops.length >= 2
          ? background.gradient.stops
          : [brand.colors.bg, brand.colors.surface];
      return (
        <AbsoluteFill
          style={{
            background: `linear-gradient(${background.gradient.angle}deg, ${stops.join(", ")})`,
          }}
        />
      );
    }
    case "tech":
    default:
      return (
        <Background
          brand={brand}
          seed={seed}
          variant={background.variants[scene.type] ?? background.defaultVariant}
        />
      );
  }
};
