import React from "react";
import type { FactItem, ScriptScene, Source } from "./api";

const VERDICT: Record<FactItem["verdict"], { label: string; color: string }> = {
  ok: { label: "Đúng", color: "var(--ok)" },
  doubtful: { label: "Chưa chắc", color: "var(--warn)" },
  unsupported: { label: "Thiếu nguồn", color: "var(--warn)" },
  wrong: { label: "Sai", color: "var(--bad)" },
};

/** Lỗi validate thuộc cảnh này: "[s03] …" hoặc "[schema] scenes/2/…". */
export const sceneIssues = (errors: string[], scene: ScriptScene, index: number) =>
  errors.filter(
    (error) =>
      error.startsWith(`[${scene.id}]`) || error.includes(`scenes/${index}/`) ||
      error.endsWith(`scenes/${index}`),
  );

export const cardStyle = (highlight: string): React.CSSProperties => ({
  background: "var(--panel)",
  border: `1px solid ${highlight}`,
  borderRadius: 12,
  padding: 16,
  marginBottom: 12,
});

export const SceneId: React.FC<{ id: string; children?: React.ReactNode }> = ({ id, children }) => (
  <header style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
    <strong style={{ fontFamily: "JetBrains Mono, monospace", color: "var(--primary)" }}>{id}</strong>
    {children}
  </header>
);

/** Bước 1: chỉ nội dung kịch bản (lời đọc) cùng nguồn và lỗi của cảnh. */
export const SceneCard: React.FC<{
  scene: ScriptScene;
  issues: string[];
  /** Cảnh báo không chặn duyệt, vd. số liệu chưa gắn nguồn. */
  warnings: string[];
  facts: FactItem[];
  sources: Source[];
  onChange: (scene: ScriptScene) => void;
}> = ({ scene, issues, warnings, facts, sources, onChange }) => {
  const segments = scene.segments ?? [];

  return (
    <section style={cardStyle(issues.length ? "#5b2a2a" : "var(--line)")}>
      <SceneId id={scene.id} />
      {segments.length ? (
        segments.map((segment, segmentIndex) => (
          <div key={segmentIndex}>
            <label>Đoạn {segmentIndex + 1} ({segment.language ?? "mặc định"})</label>
            <textarea
              value={segment.text}
              rows={2}
              onChange={(event) => {
                const next = segments.map((item, i) =>
                  i === segmentIndex ? { ...item, text: event.target.value } : item,
                );
                onChange({ ...scene, segments: next, narration: next.map((item) => item.text).join(" ") });
              }}
            />
          </div>
        ))
      ) : (
        <textarea
          value={scene.narration}
          rows={2}
          onChange={(event) => onChange({ ...scene, narration: event.target.value })}
        />
      )}

      {scene.claims?.length ? (
        <div style={{ marginTop: 12 }}>
          <label style={{ marginTop: 0 }}>Khẳng định & nguồn</label>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13 }}>
            {scene.claims.map((claim, claimIndex) => {
              const source = sources.find((item) => item.index === claim.source);
              return (
                <li key={claimIndex}>
                  {claim.text}{" "}
                  <a
                    href={`#source-${claim.source}`}
                    style={{ color: source ? "var(--primary)" : "var(--bad)" }}
                    title={source?.title ?? "Không có nguồn này trong danh sách"}
                  >
                    [{claim.source}]
                  </a>
                  {source ? (
                    <span style={{ color: "var(--muted)" }}> {source.title}</span>
                  ) : (
                    <span style={{ color: "var(--bad)" }}> nguồn không tồn tại</span>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}

      {issues.length || warnings.length || facts.length ? (
        <ul style={{ margin: "12px 0 0", paddingLeft: 18, fontSize: 13 }}>
          {issues.map((issue) => (
            <li key={issue} style={{ color: "var(--bad)" }}>
              {issue}
            </li>
          ))}
          {warnings.map((warning) => (
            <li key={warning} style={{ color: "var(--warn)" }}>
              {warning}
            </li>
          ))}
          {facts.map((fact, factIndex) => (
            <li key={factIndex}>
              <span style={{ color: VERDICT[fact.verdict]?.color, fontWeight: 700 }}>
                {VERDICT[fact.verdict]?.label ?? fact.verdict}
              </span>
              {": "}
              {fact.claim}
              {fact.note ? <span style={{ color: "var(--muted)" }}> — {fact.note}</span> : null}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
};
