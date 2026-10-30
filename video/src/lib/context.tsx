import React, { createContext, useContext } from "react";
import type { Layout, Template } from "./types";

type VideoContextValue = { layout: Layout; template: Template };

const VideoContext = createContext<VideoContextValue | null>(null);

/**
 * Cấp layout (theo khung hình) và template (giao diện) cho cả cây component.
 * Nhờ đó scene/visual không cần nhận `format` hay truyền props qua nhiều tầng.
 */
export const VideoProvider: React.FC<
  VideoContextValue & { children: React.ReactNode }
> = ({ layout, template, children }) => (
  <VideoContext.Provider value={{ layout, template }}>
    {children}
  </VideoContext.Provider>
);

const useVideoContext = (): VideoContextValue => {
  const value = useContext(VideoContext);
  if (!value) {
    throw new Error("useLayout/useTemplate phải nằm trong <VideoProvider>");
  }
  return value;
};

export const useLayout = (): Layout => useVideoContext().layout;
export const useTemplate = (): Template => useVideoContext().template;
