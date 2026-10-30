import React from "react";
import type { ScriptScene } from "./api";
import { SceneId, cardStyle } from "./SceneCard";

/** Bước 3: mô tả chuyển động của cảnh + ô ghi chú yêu cầu chỉnh animation. */
export const AnimationCard: React.FC<{
  scene: ScriptScene;
  motion: string[];
  note: string;
  durationSec: number | null;
  active: boolean;
  onNote: (value: string) => void;
  onSeek: () => void;
}> = ({ scene, motion, note, durationSec, active, onNote, onSeek }) => (
  <section style={cardStyle(active ? "var(--primary)" : note ? "var(--warn)" : "var(--line)")}>
    <SceneId id={scene.id}>
      {durationSec !== null ? (
        <span style={{ fontSize: 12, color: "var(--muted)" }}>~{durationSec.toFixed(1)}s</span>
      ) : null}
      <span style={{ flex: 1 }} />
      <button onClick={onSeek} disabled={durationSec === null} title="Phát animation từ cảnh này">
        ▶ Xem cảnh
      </button>
    </SceneId>
    <p style={{ margin: "0 0 10px", color: "var(--muted)", fontSize: 13 }}>“{scene.narration}”</p>

    <label style={{ marginTop: 0 }}>Chuyển động</label>
    <ol style={{ margin: 0, paddingLeft: 20, fontSize: 13, lineHeight: 1.7 }}>
      {motion.map((line) => (
        <li key={line}>{line}</li>
      ))}
    </ol>

    <label>Ghi chú / yêu cầu chỉnh animation</label>
    <textarea
      value={note}
      rows={2}
      placeholder="Ví dụ: số đếm chậm hơn, thêm tiếng tick khi số chốt, đổi chuyển cảnh sang fade…"
      onChange={(event) => onNote(event.target.value)}
    />
  </section>
);
