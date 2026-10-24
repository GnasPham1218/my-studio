import React from "react";
import type { Scene } from "../lib/types";
import { PhoneMock } from "./tech/PhoneMock";
import { AwardCard } from "./tech/AwardCard";
import { LoopDiagram } from "./tech/LoopDiagram";
import { ShrinkDiagram } from "./tech/ShrinkDiagram";
import { DeclineChart } from "./tech/DeclineChart";
import { StorageBar } from "./tech/StorageBar";
import { LimitsMeters } from "./tech/LimitsMeters";
import { QuestionDiagram } from "./tech/QuestionDiagram";
import { StickFigure } from "./stick/StickFigure";
import type { VisualProps } from "./layout";

export { ChipIcon, CloudIcon, PhoneIcon, DiskIcon, MemoryIcon } from "./icons";
export { PhoneMock };
export type { VisualProps } from "./layout";

export const Visual: React.FC<VisualProps> = ({ scene, brand }) => {
  const visual = scene.visual;
  if (!visual) {
    return null;
  }
  switch (visual.kind) {
    case "phone":
      return (
        <PhoneMock
          brand={brand}
          label={visual.label ?? "2018"}
          sub={visual.sub}
        />
      );
    case "award":
      return <AwardCard brand={brand} year={visual.label ?? "2025"} />;
    case "loop":
      return <LoopDiagram brand={brand} />;
    case "shrink":
      return <ShrinkDiagram brand={brand} />;
    case "decline":
      return <DeclineChart brand={brand} />;
    case "storage":
      return <StorageBar brand={brand} />;
    case "limits":
      return <LimitsMeters brand={brand} />;
    case "question":
      return <QuestionDiagram brand={brand} />;
    case "stick":
      return <StickFigure scene={scene} brand={brand} />;
    default:
      return null;
  }
};

export const hasVisual = (scene: Scene) =>
  Boolean(
    scene.visual &&
      [
        "phone",
        "award",
        "loop",
        "shrink",
        "decline",
        "storage",
        "limits",
        "question",
        "stick",
      ].includes(scene.visual.kind),
  );
