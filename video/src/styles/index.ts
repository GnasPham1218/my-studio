import { techExplainer } from "./tech-explainer";
import { whiteboard } from "./whiteboard";
import type { VideoStyle } from "./tech-explainer";

/**
 * Registry style. Thêm style mới:
 * 1. Tạo file trong thư mục này.
 * 2. Import + thêm vào `styles`.
 * 3. Đặt "style": "<id>" trong projects/<id>/project.json.
 */
export const styles: Record<string, VideoStyle> = {
  [techExplainer.id]: techExplainer,
  [whiteboard.id]: whiteboard,
};

export const defaultStyle = techExplainer;

export const getStyle = (id?: string): VideoStyle =>
  (id && styles[id]) || defaultStyle;

export { techExplainer, whiteboard };
export type {
  BackgroundKind,
  BackgroundVariant,
  CaptionTheme,
  VideoStyle,
} from "./tech-explainer";
