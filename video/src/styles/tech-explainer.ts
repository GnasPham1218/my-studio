/**
 * Một "style" quyết định lớp trình bày, không quyết định nội dung.
 * Nội dung nằm trong projects/<id>/; style chỉ chọn cách dựng hình.
 *
 * Muốn thêm style mới:
 * 1. Tạo file trong thư mục này, export một VideoStyle.
 * 2. Đăng ký trong `styles/index.ts`.
 * 3. Đặt "style": "<id>" trong projects/<id>/project.json.
 */

export type BackgroundVariant = "hero" | "data" | "calm" | "glitch";
export type BackgroundKind = "tech" | "paper";
export type CaptionTheme = "tech" | "paper";

export type VideoStyle = {
  id: string;
  label: string;
  description: string;
  /** Chọn nền theo loại scene. */
  backgroundVariant: (sceneType: string) => BackgroundVariant;
  /** Loại nền: tech tối hoặc giấy sáng. */
  backgroundKind: BackgroundKind;
  /** Theme cho caption và scrim. */
  captionTheme: CaptionTheme;
  /** Có hiện số scene + thanh tiến độ ở góc trên trái không. */
  showSceneIndex: boolean;
  /** Thanh tiến độ riêng khi đã ẩn số scene. */
  showProgress: boolean;
  /** Có hiện watermark kênh không. */
  showWatermark: boolean;
};

export const techExplainer: VideoStyle = {
  id: "tech-explainer",
  label: "Tech Explainer",
  description:
    "Giải thích công nghệ bằng visual metaphor, chữ lớn, nhịp nhanh, phù hợp short 9:16.",
  backgroundVariant: (sceneType) => {
    if (sceneType === "hook" || sceneType === "outro") {
      return "hero";
    }
    if (sceneType === "stat" || sceneType === "chart" || sceneType === "compare") {
      return "data";
    }
    return "calm";
  },
  backgroundKind: "tech",
  captionTheme: "tech",
  showSceneIndex: true,
  showProgress: false,
  showWatermark: true,
};

