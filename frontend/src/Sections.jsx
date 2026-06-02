import { useState } from "react";
import { suggestSections, confirmSection, ApiError } from "./api";

export default function Sections({ caseId, user }) {
  const [results, setResults] = useState(null); // null = not suggested yet
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [pending, setPending] = useState({}); // case_section_id -> bool (in-flight)

  const canConfirm = user.can_generate_documents; // IO/SHO

  async function suggest() {
    setError(null);
    setLoading(true);
    try {
      const data = await suggestSections(caseId, 6);
      setResults(data.results);
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setError("Add an incident narrative to the case first — that's what the AI matches against.");
      } else {
        setError(err.message || "Could not get suggestions.");
      }
    } finally {
      setLoading(false);
    }
  }

  async function toggle(row, checked) {
    setError(null);
    setPending((p) => ({ ...p, [row.case_section_id]: true }));
    try {
      const updated = await confirmSection(caseId, row.case_section_id, checked);
      setResults((rs) =>
        rs.map((r) =>
          r.case_section_id === row.case_section_id ? { ...r, confirmed: updated.confirmed } : r
        )
      );
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError("Only an IO or SHO can confirm sections.");
      } else {
        setError(err.message || "Could not update the section.");
      }
    } finally {
      setPending((p) => ({ ...p, [row.case_section_id]: false }));
    }
  }

  return (
    <section className="card">
      <h2>Applicable BNS sections</h2>
      <p className="hint">
        The AI suggests sections from the incident narrative (ranked by match).
        You confirm the ones that apply — only confirmed sections go into documents.
      </p>

      <button onClick={suggest} disabled={loading}>
        {loading ? "Analysing…" : results ? "Re-suggest" : "Suggest BNS Sections"}
      </button>
      {error && <p className="bad">✗ {error}</p>}

      {results && results.length === 0 && (
        <p className="muted">No suggestions found.</p>
      )}

      {results && results.length > 0 && (
        <ul className="section-list">
          {results.map((r) => (
            <li key={r.case_section_id} className={r.confirmed ? "section-row confirmed" : "section-row"}>
              <label className="section-confirm">
                <input
                  type="checkbox"
                  checked={r.confirmed}
                  disabled={!canConfirm || pending[r.case_section_id]}
                  onChange={(e) => toggle(r, e.target.checked)}
                />
              </label>
              <div className="section-main">
                <div className="section-head">
                  <span className="tag">{r.code} {r.section_number}</span>
                  <strong>{r.title}</strong>
                  {r.confirmed && <span className="good"> ✓ confirmed</span>}
                </div>
                <div className="section-meta muted">
                  match {Math.round(r.similarity * 100)}%
                  {r.ipc_equivalent ? ` · IPC ${r.ipc_equivalent}` : ""}
                </div>
              </div>
              <div className="section-bar" aria-hidden="true">
                <span style={{ width: `${Math.max(5, Math.round(r.similarity * 100))}%` }} />
              </div>
            </li>
          ))}
        </ul>
      )}

      {results && !canConfirm && (
        <p className="hint">Your role ({user.role_display}) can view suggestions but not confirm them.</p>
      )}
    </section>
  );
}
