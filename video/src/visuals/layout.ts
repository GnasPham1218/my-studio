import type { Brand, Scene } from "../lib/types";

export const WIDE = 860;

export type VisualProps = {
  scene: Scene;
  brand: Brand;
  format: "short" | "long";
};
