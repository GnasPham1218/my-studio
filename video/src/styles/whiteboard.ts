import type { VideoStyle } from "./tech-explainer";

/**
 * Whiteboard lesson: nền giấy sáng, chữ marker, caption như thẻ giấy.
 * Phù hợp kênh dạy tiếng Anh; nhân vật que do visual "stick" đảm nhiệm.
 */
export const whiteboard: VideoStyle = {
  id: "whiteboard",
  label: "Whiteboard Lesson",
  description:
    "Nền giấy sáng, chữ marker, caption thẻ giấy; dùng visual người que cho bài giảng.",
  backgroundVariant: () => "calm",
  backgroundKind: "paper",
  captionTheme: "paper",
  showSceneIndex: false,
  showProgress: true,
  showWatermark: true,
};
