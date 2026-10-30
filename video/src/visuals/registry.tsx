import React from "react";
import catalog from "../../../config/visuals.json";
import type { Brand, Scene } from "../lib/types";
import { useLayout } from "../lib/context";
import { PhoneMock } from "./tech/PhoneMock";
import { AwardCard, type AwardData } from "./tech/AwardCard";
import { LoopDiagram, type LoopData } from "./tech/LoopDiagram";
import { ShrinkDiagram, type ShrinkData } from "./tech/ShrinkDiagram";
import { DeclineChart, type DeclineData } from "./tech/DeclineChart";
import { StorageBar, type StorageData } from "./tech/StorageBar";
import { LimitsMeters, type LimitsData } from "./tech/LimitsMeters";
import { QuestionDiagram, type QuestionData } from "./tech/QuestionDiagram";
import { StickFigure } from "./stick/StickFigure";

/**
 * Registry visual: nguồn duy nhất cho `Visual` và `hasVisual`.
 *
 * `Kind` lấy từ config/visuals.json nên `renderers` thiếu một kind trong catalog
 * (hoặc thừa kind không có trong catalog) sẽ làm `tsc` báo lỗi. Dữ liệu của mỗi
 * kind đã được pipeline.build gộp default vào `scene.visual.data`; component
 * không chứa nội dung nào.
 */
type Kind = keyof typeof catalog.kinds;
type Renderer = React.FC<{ scene: Scene; brand: Brand }>;

const dataOf = <T,>(scene: Scene): T => {
  const data = scene.visual?.data;
  if (!data) {
    throw new Error(
      `Scene ${scene.id}: visual "${scene.visual?.kind}" thiếu data. ` +
        "Chạy lại pipeline.build (nó gộp default từ config/visuals.json).",
    );
  }
  return data as T;
};

const renderers: Record<Kind, Renderer> = {
  phone: ({ scene, brand }) => (
    <PhoneMock
      brand={brand}
      label={scene.visual?.label ?? "2018"}
      sub={scene.visual?.sub}
      badge={dataOf<{ badge: string }>(scene).badge}
    />
  ),
  award: ({ scene, brand }) => (
    <AwardCard
      brand={brand}
      year={scene.visual?.label ?? "2025"}
      data={dataOf<AwardData>(scene)}
    />
  ),
  loop: ({ scene, brand }) => (
    <LoopDiagram brand={brand} data={dataOf<LoopData>(scene)} />
  ),
  shrink: ({ scene, brand }) => (
    <ShrinkDiagram brand={brand} data={dataOf<ShrinkData>(scene)} />
  ),
  decline: ({ scene, brand }) => (
    <DeclineChart brand={brand} data={dataOf<DeclineData>(scene)} />
  ),
  storage: ({ scene, brand }) => (
    <StorageBar brand={brand} data={dataOf<StorageData>(scene)} />
  ),
  limits: ({ scene, brand }) => (
    <LimitsMeters brand={brand} data={dataOf<LimitsData>(scene)} />
  ),
  question: ({ scene, brand }) => (
    <QuestionDiagram brand={brand} data={dataOf<QuestionData>(scene)} />
  ),
  stick: ({ scene, brand }) => <StickFigure scene={scene} brand={brand} />,
};

export const hasVisual = (scene: Scene): boolean =>
  Boolean(scene.visual && scene.visual.kind in renderers);

export const Visual: React.FC<{ scene: Scene; brand: Brand }> = ({
  scene,
  brand,
}) => {
  const { visualScale } = useLayout();
  const kind = scene.visual?.kind;
  if (!kind || !(kind in renderers)) {
    return null;
  }
  const Render = renderers[kind as Kind];
  if (visualScale === 1) {
    // Không bọc div: một wrapper làm flex co visual rộng hơn khung chứa.
    return <Render scene={scene} brand={brand} />;
  }
  // zoom (không phải transform) để vùng chiếm chỗ cũng co lại theo.
  return (
    <div style={{ zoom: visualScale }}>
      <Render scene={scene} brand={brand} />
    </div>
  );
};
