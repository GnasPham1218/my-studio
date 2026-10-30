import React, { useState } from "react";
import { api, type LinkStatus, type ReviewState } from "./api";

const linkColor = (status?: LinkStatus) =>
  !status ? "var(--muted)" : status.ok ? "var(--ok)" : status.status.startsWith("bị chặn") ? "var(--warn)" : "var(--bad)";

/** Nguồn tham khảo của kịch bản: danh sách nguồn, kiểm tra link, giả định, research.md. */
export const SourcesPanel: React.FC<{
  review: ReviewState;
  onShowResearch: () => void;
}> = ({ review, onShowResearch }) => {
  const [links, setLinks] = useState<Map<number, LinkStatus> | null>(null);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Mỗi nguồn được cảnh nào dẫn tới (qua claims).
  const usedBy = new Map<number, string[]>();
  review.script.scenes.forEach((scene) =>
    (scene.claims ?? []).forEach((claim) =>
      usedBy.set(claim.source, [...(usedBy.get(claim.source) ?? []), scene.id]),
    ),
  );

  const check = async () => {
    setChecking(true);
    setError(null);
    try {
      const result = await api.links(review.project, review.format);
      setLinks(new Map(result.map((item) => [item.index, item])));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setChecking(false);
    }
  };

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
        <strong style={{ flex: 1 }}>Nguồn tham khảo ({review.sources.length})</strong>
        <button onClick={check} disabled={checking || !review.sources.some((s) => s.url)}>
          {checking ? "Đang kiểm…" : "Kiểm tra link"}
        </button>
      </div>
      {error ? <p style={{ color: "var(--bad)", fontSize: 13 }}>{error}</p> : null}
      {review.sources.length ? (
        <ol style={{ margin: 0, paddingLeft: 0, listStyle: "none" }}>
          {review.sources.map((source) => {
            const status = links?.get(source.index);
            const scenes = usedBy.get(source.index) ?? [];
            return (
              <li
                key={source.index}
                id={`source-${source.index}`}
                style={{
                  padding: "10px 12px",
                  marginBottom: 8,
                  background: "var(--panel)",
                  border: "1px solid var(--line)",
                  borderRadius: 10,
                  fontSize: 13,
                }}
              >
                <div style={{ display: "flex", gap: 8 }}>
                  <span style={{ color: "var(--primary)", fontWeight: 700 }}>[{source.index}]</span>
                  <span style={{ flex: 1 }}>
                    {source.url ? (
                      <a href={source.url} target="_blank" rel="noreferrer" style={{ color: "var(--fg)" }}>
                        {source.title}
                      </a>
                    ) : (
                      source.title
                    )}
                  </span>
                </div>
                <div style={{ color: "var(--muted)", fontSize: 12, marginTop: 4, wordBreak: "break-all" }}>
                  {source.url ?? "không có link"}
                  {source.accessedAt ? ` · truy cập ${source.accessedAt}` : ""}
                </div>
                <div style={{ fontSize: 12, marginTop: 4, display: "flex", gap: 10, flexWrap: "wrap" }}>
                  {status ? (
                    <span style={{ color: linkColor(status) }}>
                      {status.ok ? "✓ link mở được" : `! ${status.status}`}
                    </span>
                  ) : null}
                  <span style={{ color: scenes.length ? "var(--fg)" : "var(--muted)" }}>
                    {scenes.length ? `Dẫn chứng cho: ${scenes.join(", ")}` : "Chưa cảnh nào trích dẫn"}
                  </span>
                </div>
              </li>
            );
          })}
        </ol>
      ) : (
        <p style={{ color: "var(--warn)", fontSize: 13 }}>Kịch bản không khai báo nguồn nào.</p>
      )}

      {review.assumptions.length ? (
        <>
          <strong style={{ display: "block", margin: "16px 0 8px" }}>Giả định</strong>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, color: "var(--warn)" }}>
            {review.assumptions.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </>
      ) : null}

      {review.hasResearch ? (
        <button style={{ width: "100%", marginTop: 16 }} onClick={onShowResearch}>
          Xem research.md (ghi chép nghiên cứu)
        </button>
      ) : null}
    </div>
  );
};
