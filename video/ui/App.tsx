import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Player, type PlayerRef } from "@remotion/player";
import { ExplainerVideo } from "../src/compositions/ExplainerVideo";
import type { Props } from "../src/lib/types";
import { api, type Job, type ProjectInfo, type ReviewState, type Script, type ScriptScene } from "./api";
import { SceneCard, sceneIssues } from "./SceneCard";
import { SourcesPanel } from "./SourcesPanel";
import { AnimationCard } from "./AnimationCard";

type Selection = { project: string; format: string };
type Notice = { kind: "ok" | "error"; text: string } | null;

const PREVIEW_DELAY_MS = 600;

type OutputChoice = "video" | "capcut" | "both";

// Video MP4 và dự án CapCut là hai lần render khác nhau (CapCut cần clip chưa
// có phụ đề/chuyển cảnh), nên "cả hai" mất khoảng gấp đôi thời gian.
const OUTPUT_CHOICES: { id: OutputChoice; label: string; hint: string }[] = [
  { id: "video", label: "Video MP4", hint: "Video hoàn chỉnh + thumbnail" },
  { id: "capcut", label: "Dự án CapCut", hint: "Clip từng cảnh để chỉnh trong CapCut + thumbnail" },
  { id: "both", label: "Cả hai", hint: "Render 2 lần, lâu gấp khoảng đôi" },
];

const STEPS = ["Đọc kịch bản & nguồn", "Duyệt", "Animation & tạo video"];

/** Luồng bắt buộc: nội dung phải được duyệt trước khi dựng animation. */
const Steps: React.FC<{ current: number }> = ({ current }) => (
  <div style={{ display: "flex", gap: 6, marginTop: 10, fontSize: 12, flexWrap: "wrap" }}>
    {STEPS.map((label, index) => {
      const step = index + 1;
      const done = step < current;
      const active = step === current || (current === 3 && step === 2);
      return (
        <span
          key={label}
          style={{
            padding: "3px 10px",
            borderRadius: 999,
            border: `1px solid ${active || done ? "var(--primary)" : "var(--line)"}`,
            color: active || done ? "var(--primary)" : "var(--muted)",
          }}
        >
          {done || (current === 3 && step === 2) ? "✓" : step}. {label}
        </span>
      );
    })}
  </div>
);

const Badge: React.FC<{ ok: boolean; children: React.ReactNode }> = ({ ok, children }) => (
  <span
    style={{
      fontSize: 12,
      fontWeight: 600,
      padding: "3px 10px",
      borderRadius: 999,
      color: ok ? "var(--ok)" : "var(--warn)",
      border: `1px solid ${ok ? "var(--ok)" : "var(--warn)"}`,
      whiteSpace: "nowrap",
    }}
  >
    {children}
  </span>
);

export const App: React.FC = () => {
  const [projects, setProjects] = useState<ProjectInfo[]>([]);
  const [selection, setSelection] = useState<Selection | null>(null);
  const [review, setReview] = useState<ReviewState | null>(null);
  const [draft, setDraft] = useState<Script | null>(null);
  const [dirty, setDirty] = useState(false);
  const [aspect, setAspect] = useState<string>("");
  const [preview, setPreview] = useState<{ props: Props | null; errors: string[] } | null>(null);
  const [notice, setNotice] = useState<Notice>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [panel, setPanel] = useState<"approve" | "reject" | null>(null);
  const [note, setNote] = useState("");
  const [skipFactcheck, setSkipFactcheck] = useState(false);
  const [force, setForce] = useState(false);
  const [output, setOutput] = useState<OutputChoice>("video");
  const [activeScene, setActiveScene] = useState<string | null>(null);
  const [liveErrors, setLiveErrors] = useState<string[] | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [notesDirty, setNotesDirty] = useState(false);
  const [research, setResearch] = useState<string | null>(null);
  const player = useRef<PlayerRef>(null);

  const fail = (error: unknown) =>
    setNotice({ kind: "error", text: error instanceof Error ? error.message : String(error) });

  const loadProjects = useCallback(async () => {
    const list = await api.projects();
    setProjects(list);
    return list;
  }, []);

  // Lần đầu: chọn dự án đầu tiên có kịch bản.
  useEffect(() => {
    loadProjects()
      .then((list) => {
        const first = list.find((item) => item.formats.length);
        if (first) setSelection({ project: first.id, format: first.formats[0].format });
      })
      .catch(fail);
  }, [loadProjects]);

  const applyReview = (state: ReviewState) => {
    setReview(state);
    setDraft(state.script);
    setDirty(false);
    setNotes(state.notes);
    setNotesDirty(false);
  };

  useEffect(() => {
    if (!selection) return;
    setPreview(null);
    setActiveScene(null);
    api
      .review(selection.project, selection.format)
      .then((state) => {
        applyReview(state);
        setAspect(state.aspect);
      })
      .catch(fail);
  }, [selection]);

  const approved = review ? review.approvalProblem === null : false;

  // Lỗi của bản đang sửa, kiểm lại sau mỗi lần gõ (chưa cần lưu).
  useEffect(() => {
    if (!selection || !draft || !dirty) {
      setLiveErrors(null);
      return;
    }
    const timer = setTimeout(() => {
      api.check(selection.project, selection.format, draft).then((r) => setLiveErrors(r.errors)).catch(fail);
    }, PREVIEW_DELAY_MS);
    return () => clearTimeout(timer);
  }, [selection, draft, dirty]);

  // Animation chỉ dựng cho kịch bản đã duyệt và không có thay đổi chưa lưu.
  useEffect(() => {
    if (!selection || !aspect || !approved || dirty) {
      setPreview(null);
      return;
    }
    api.preview(selection.project, selection.format, aspect).then(setPreview).catch(fail);
  }, [selection, aspect, approved, dirty, review]);

  // Theo dõi tác vụ nền (tạo video / fact-check).
  useEffect(() => {
    if (!job || job.status !== "running") return;
    const timer = setInterval(() => {
      api
        .job(job.id)
        .then((next) => {
          setJob(next);
          if (next.status !== "running") {
            loadProjects().catch(fail);
            if (selection) api.review(selection.project, selection.format).then(applyReview).catch(fail);
            setNotice(
              next.status === "done"
                ? { kind: "ok", text: `${next.title}: xong` }
                : { kind: "error", text: `${next.title}: lỗi (mã ${next.code}), xem log` },
            );
          }
        })
        .catch(fail);
    }, 1000);
    return () => clearInterval(timer);
  }, [job, selection, loadProjects]);

  const props = preview?.props ?? null;
  const errors = (dirty ? liveErrors : null) ?? review?.errors ?? [];
  const sceneTimes = useMemo(() => {
    const map = new Map<string, { start: number; duration: number }>();
    props?.scenes.forEach((scene) => map.set(scene.id, { start: scene.startSec, duration: scene.durationSec }));
    return map;
  }, [props]);
  const generalErrors = useMemo(
    () =>
      draft
        ? errors.filter(
            (error) => !draft.scenes.some((scene, index) => sceneIssues([error], scene, index).length),
          )
        : errors,
    [errors, draft],
  );
  const facts = review?.factcheck?.items ?? [];
  const running = job?.status === "running";
  const unlocked = approved && !dirty;

  const showResearch = () => {
    if (!selection) return;
    api.research(selection.project, selection.format).then((r) => setResearch(r.text)).catch(fail);
  };

  const updateScene = (index: number, scene: ScriptScene) => {
    if (!draft) return;
    setDraft({ ...draft, scenes: draft.scenes.map((item, i) => (i === index ? scene : item)) });
    setDirty(true);
  };

  const seek = (sceneId: string) => {
    const time = sceneTimes.get(sceneId);
    if (!time || !props || !player.current) return;
    setActiveScene(sceneId);
    player.current.seekTo(Math.round(time.start * props.fps));
    player.current.play();
  };

  const save = async () => {
    if (!selection || !draft) return;
    try {
      const state = await api.save(selection.project, selection.format, draft);
      applyReview(state);
      await loadProjects();
      setNotice({
        kind: state.errors.length ? "error" : "ok",
        text: state.errors.length
          ? `Đã lưu, còn ${state.errors.length} lỗi cần sửa trước khi duyệt`
          : "Đã lưu kịch bản. Cần duyệt lại trước khi tạo video.",
      });
    } catch (error) {
      fail(error);
    }
  };

  const saveNotes = async () => {
    if (!selection || !review) return;
    try {
      const saved = await api.saveNotes(selection.project, selection.format, notes);
      setReview({ ...review, notes: saved });
      setNotes(saved);
      setNotesDirty(false);
      setNotice({ kind: "ok", text: `Đã lưu ghi chú animation (${Object.keys(saved).length} cảnh).` });
    } catch (error) {
      fail(error);
    }
  };

  const decide = async () => {
    if (!selection) return;
    try {
      const result =
        panel === "approve"
          ? await api.approve({ ...selection, note, skipFactcheck, force })
          : await api.reject(selection.project, selection.format, note);
      applyReview(result.state);
      await loadProjects();
      setNotice({ kind: result.ok ? "ok" : "error", text: result.message || (result.ok ? "Xong" : "Không thành công") });
      if (result.ok) {
        setPanel(null);
        setNote("");
      }
    } catch (error) {
      fail(error);
    }
  };

  const startJob = async (kind: "make" | "factcheck") => {
    if (!selection) return;
    try {
      setJob(await api.startJob({ kind, ...selection, aspect, output }));
      setNotice(null);
    } catch (error) {
      fail(error);
    }
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "240px 1fr 420px", height: "100vh" }}>
      {/* Danh sách dự án */}
      <aside style={{ borderRight: "1px solid var(--line)", padding: 16, overflowY: "auto" }}>
        <div style={{ fontWeight: 800, fontSize: 16, marginBottom: 16 }}>Duyệt kịch bản</div>
        {projects.map((project) => (
          <div key={project.id} style={{ marginBottom: 14 }}>
            <div style={{ fontWeight: 600 }}>{project.title}</div>
            <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 6 }}>{project.id}</div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {project.formats.map((item) => {
                const selected =
                  selection?.project === project.id && selection.format === item.format;
                return (
                  <button
                    key={item.format}
                    onClick={() => {
                      if ((dirty || notesDirty) && !window.confirm("Bỏ các thay đổi chưa lưu?")) return;
                      setSelection({ project: project.id, format: item.format });
                    }}
                    style={{
                      padding: "3px 10px",
                      fontSize: 12,
                      borderColor: selected ? "var(--primary)" : undefined,
                      color: item.approved ? "var(--ok)" : undefined,
                    }}
                    title={item.problem ?? "Đã duyệt"}
                  >
                    {item.approved ? "✓ " : ""}
                    {item.format}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </aside>

      {/* Kịch bản */}
      <main style={{ overflowY: "auto", padding: "0 20px 40px" }}>
        {review && draft ? (
          <>
            <div
              style={{
                position: "sticky",
                top: 0,
                zIndex: 2,
                background: "var(--bg)",
                padding: "16px 0 12px",
                borderBottom: "1px solid var(--line)",
                marginBottom: 16,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                <h1 style={{ fontSize: 20, margin: 0 }}>{draft.meta.title}</h1>
                <Badge ok={approved}>{approved ? "Đã duyệt" : review.approvalProblem}</Badge>
                {dirty ? <Badge ok={false}>Chưa lưu</Badge> : null}
              </div>
              <Steps current={unlocked ? 3 : 1} />

              {unlocked ? (
                <div style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" }}>
                  <button className="primary" onClick={saveNotes} disabled={!notesDirty}>
                    Lưu ghi chú animation
                  </button>
                  <button
                    onClick={() => {
                      setNotes(review.notes);
                      setNotesDirty(false);
                    }}
                    disabled={!notesDirty}
                  >
                    Bỏ thay đổi
                  </button>
                  <span style={{ width: 12 }} />
                  <button className="danger" onClick={() => setPanel("reject")} disabled={notesDirty}>
                    Từ chối kịch bản…
                  </button>
                </div>
              ) : (
              <div style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" }}>
                <button className="primary" onClick={save} disabled={!dirty}>
                  Lưu
                </button>
                <button onClick={() => applyReview(review)} disabled={!dirty}>
                  Bỏ thay đổi
                </button>
                <span style={{ width: 12 }} />
                <button onClick={() => startJob("factcheck")} disabled={dirty || running}>
                  Fact-check ({review.llm})
                </button>
                <button onClick={() => setPanel("approve")} disabled={dirty}>
                  Duyệt…
                </button>
                <button className="danger" onClick={() => setPanel("reject")} disabled={dirty}>
                  Từ chối…
                </button>
              </div>
              )}
              {notice ? (
                <div
                  style={{
                    marginTop: 10,
                    whiteSpace: "pre-wrap",
                    fontSize: 13,
                    color: notice.kind === "ok" ? "var(--ok)" : "var(--bad)",
                  }}
                >
                  {notice.text}
                </div>
              ) : null}
            </div>

            {panel ? (
              <div
                style={{
                  background: "var(--panel)",
                  border: "1px solid var(--primary)",
                  borderRadius: 12,
                  padding: 16,
                  marginBottom: 16,
                }}
              >
                <strong>{panel === "approve" ? "Duyệt kịch bản" : "Từ chối kịch bản"}</strong>
                <label>{panel === "approve" ? "Ghi chú (tuỳ chọn)" : "Lý do từ chối"}</label>
                <input value={note} onChange={(event) => setNote(event.target.value)} />
                {panel === "approve" ? (
                  <div style={{ display: "flex", gap: 18, marginTop: 10, fontSize: 13 }}>
                    <label style={{ display: "flex", gap: 6, margin: 0, color: "var(--fg)" }}>
                      <input
                        type="checkbox"
                        style={{ width: "auto" }}
                        checked={skipFactcheck}
                        onChange={(event) => setSkipFactcheck(event.target.checked)}
                      />
                      Duyệt không cần fact-check
                    </label>
                    <label style={{ display: "flex", gap: 6, margin: 0, color: "var(--fg)" }}>
                      <input
                        type="checkbox"
                        style={{ width: "auto" }}
                        checked={force}
                        onChange={(event) => setForce(event.target.checked)}
                      />
                      Bỏ qua khẳng định "Sai" (đã kiểm tay)
                    </label>
                  </div>
                ) : null}
                <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                  <button className={panel === "approve" ? "primary" : "danger"} onClick={decide}>
                    {panel === "approve" ? "Duyệt" : "Từ chối"}
                  </button>
                  <button onClick={() => setPanel(null)}>Huỷ</button>
                </div>
              </div>
            ) : null}

            {review.factcheckStale ? (
              <p style={{ color: "var(--warn)", fontSize: 13 }}>
                Kết quả fact-check là của phiên bản kịch bản cũ, nên chạy lại.
              </p>
            ) : null}
            {review.claimIssues.length ? (
              <p style={{ color: "var(--warn)", fontSize: 13 }}>
                ⚠ {review.claimIssues.length} cảnh có số liệu nhưng chưa ghi rõ lấy từ nguồn nào
                (xem dòng vàng dưới từng cảnh).
              </p>
            ) : null}
            {generalErrors.length ? (
              <ul style={{ color: "var(--bad)", fontSize: 13, paddingLeft: 18 }}>
                {generalErrors.map((error) => (
                  <li key={error}>{error}</li>
                ))}
              </ul>
            ) : null}

            {draft.scenes.map((scene, index) =>
              unlocked ? (
                <AnimationCard
                  key={scene.id}
                  scene={scene}
                  motion={review.motion[scene.id] ?? []}
                  note={notes[scene.id] ?? ""}
                  durationSec={sceneTimes.get(scene.id)?.duration ?? null}
                  active={activeScene === scene.id}
                  onNote={(value) => {
                    setNotes({ ...notes, [scene.id]: value });
                    setNotesDirty(true);
                  }}
                  onSeek={() => seek(scene.id)}
                />
              ) : (
                <SceneCard
                  key={scene.id}
                  scene={scene}
                  issues={sceneIssues(errors, scene, index)}
                  warnings={sceneIssues(review.claimIssues, scene, index)}
                  facts={facts.filter((fact) => fact.sceneId === scene.id)}
                  sources={review.sources}
                  onChange={(next) => updateScene(index, next)}
                />
              ),
            )}
          </>
        ) : (
          <p style={{ color: "var(--muted)", padding: 20 }}>Chọn một dự án bên trái.</p>
        )}
      </main>

      {/* Bước 1: nguồn tham khảo. Bước 3 (sau khi duyệt): animation + tạo video. */}
      <aside style={{ borderLeft: "1px solid var(--line)", padding: 16, overflowY: "auto" }}>
        {review && !unlocked ? (
          <>
            <div
              style={{
                padding: 12,
                marginBottom: 16,
                borderRadius: 10,
                border: "1px dashed var(--line)",
                color: "var(--muted)",
                fontSize: 13,
              }}
            >
              🔒 Animation và tạo video mở sau khi kịch bản được duyệt
              {dirty ? " (lưu thay đổi rồi duyệt lại)" : ""}.
            </div>
            <SourcesPanel review={review} onShowResearch={showResearch} />
          </>
        ) : null}
        {review && unlocked ? (
          <>
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 12 }}>
          <strong style={{ flex: 1 }}>Xem trước animation</strong>
          {review ? (
            <select value={aspect} onChange={(event) => setAspect(event.target.value)} style={{ width: "auto" }}>
              {review.aspects.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          ) : null}
        </div>
        {props ? (
          <>
            <Player
              ref={player}
              component={ExplainerVideo}
              inputProps={props}
              durationInFrames={Math.max(1, Math.round(props.totalSec * props.fps))}
              fps={props.fps}
              compositionWidth={props.width}
              compositionHeight={props.height}
              controls
              loop
              style={{
                width: "100%",
                borderRadius: 12,
                overflow: "hidden",
                border: "1px solid var(--line)",
              }}
            />
            <p style={{ fontSize: 12, color: "var(--muted)" }}>
              Không có giọng đọc; thời lượng ước tính ~{props.totalSec.toFixed(0)}s. Phụ đề trải đều
              theo chữ. Bản thật dùng thời gian của giọng đọc.
            </p>
          </>
        ) : (
          <p style={{ color: "var(--muted)" }}>
            {preview ? "Không dựng được bản xem trước (xem lỗi ở cột kịch bản)." : "Đang dựng bản xem trước…"}
          </p>
        )}

        <div style={{ borderTop: "1px solid var(--line)", marginTop: 16, paddingTop: 16 }}>
          <strong>Tạo video</strong>
          {OUTPUT_CHOICES.map((choice) => (
            <label
              key={choice.id}
              style={{ display: "flex", gap: 8, color: "var(--fg)", margin: "8px 0 0", cursor: "pointer" }}
            >
              <input
                type="radio"
                name="output"
                style={{ width: "auto", marginTop: 3 }}
                checked={output === choice.id}
                onChange={() => setOutput(choice.id)}
              />
              <span>
                {choice.label}
                <span style={{ display: "block", fontSize: 12, color: "var(--muted)" }}>{choice.hint}</span>
              </span>
            </label>
          ))}
          <button
            className="primary"
            style={{ width: "100%", marginTop: 12 }}
            disabled={running}
            onClick={() => startJob("make")}
          >
            {running ? "Đang chạy…" : `Bắt đầu (${aspect || "mặc định"})`}
          </button>
        </div>

        <details style={{ marginTop: 16 }}>
          <summary style={{ cursor: "pointer", color: "var(--muted)" }}>Nguồn tham khảo</summary>
          <div style={{ marginTop: 10 }}>
            <SourcesPanel review={review} onShowResearch={showResearch} />
          </div>
        </details>
          </>
        ) : null}

        {job ? (
          <div style={{ marginTop: 16 }}>
            <div style={{ fontSize: 13, marginBottom: 6 }}>
              <strong>{job.title}</strong> ·{" "}
              {job.status === "running" ? "đang chạy" : job.status === "done" ? "xong" : "lỗi"}
            </div>
            <pre
              style={{
                margin: 0,
                padding: 10,
                maxHeight: 320,
                overflow: "auto",
                fontSize: 11,
                lineHeight: 1.45,
                background: "#05080d",
                border: "1px solid var(--line)",
                borderRadius: 8,
                whiteSpace: "pre-wrap",
              }}
            >
              {[...job.log.slice(-120), job.current ?? ""].join("\n")}
            </pre>
          </div>
        ) : null}
      </aside>

      {research !== null ? (
        <div
          onClick={() => setResearch(null)}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 10,
            background: "rgba(0,0,0,0.6)",
            display: "flex",
            justifyContent: "center",
            padding: 40,
          }}
        >
          <div
            onClick={(event) => event.stopPropagation()}
            style={{
              width: "min(900px, 100%)",
              background: "var(--panel)",
              border: "1px solid var(--line)",
              borderRadius: 12,
              display: "flex",
              flexDirection: "column",
            }}
          >
            <div style={{ display: "flex", padding: "12px 16px", borderBottom: "1px solid var(--line)" }}>
              <strong style={{ flex: 1 }}>research.md</strong>
              <button onClick={() => setResearch(null)}>Đóng</button>
            </div>
            <pre
              style={{
                margin: 0,
                padding: 16,
                overflow: "auto",
                whiteSpace: "pre-wrap",
                fontFamily: "inherit",
                fontSize: 13,
                lineHeight: 1.6,
              }}
            >
              {research}
            </pre>
          </div>
        </div>
      ) : null}
    </div>
  );
};
