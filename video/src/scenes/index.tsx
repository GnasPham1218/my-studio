import React from "react";
import type { SceneProps } from "./shared";
import { Hook } from "./Hook";
import { Punch } from "./Punch";
import { Stat } from "./Stat";
import { List } from "./List";
import { Timeline } from "./Timeline";
import { Compare } from "./Compare";
import { Chart } from "./Chart";
import { Outro } from "./Outro";

export type { SceneProps } from "./shared";
export { Hook, Punch, Stat, List, Timeline, Compare, Chart, Outro };

export const SceneRenderer: React.FC<SceneProps> = (props) => {
  switch (props.scene.type) {
    case "hook":
      return <Hook {...props} />;
    case "stat":
      return <Stat {...props} />;
    case "list":
    case "bullets":
    case "captionStack":
    case "recap":
      return <List {...props} />;
    case "timeline":
      return <Timeline {...props} />;
    case "compare":
      return <Compare {...props} />;
    case "chart":
      return <Chart {...props} />;
    case "outro":
      return <Outro {...props} />;
    case "punch":
    case "quote":
    case "title":
    case "chapter":
    case "lowerThird":
    case "imageFull":
      return <Punch {...props} />;
    default:
      return <Punch {...props} />;
  }
};
