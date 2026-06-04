import { useState } from "react";
import { useTranslation } from "react-i18next";
import { suggestSections, confirmSection, ApiError } from "./api";
import { qualityKey } from "./quality";

export default function Sections({ caseId, user }) {
  const { t } = useTranslation();
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
        setError(t("sections.needNarrative"));
      } else {
        setError(err.message || t("sections.getFailed"));
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
        setError(t("sections.onlyOfficer"));
      } else {
        setError(err.message || t("sections.updateFailed"));
      }
    } finally {
      setPending((p) => ({ ...p, [row.case_section_id]: false }));
    }
  }

  return (
    <section className="card">
      <h2>{t("sections.title")}</h2>
      <p className="hint">{t("sections.hint")}</p>

      <button onClick={suggest} disabled={loading}>
        {loading ? t("sections.analysing") : results ? t("sections.resuggest") : t("sections.suggest")}
      </button>
      {error && <p className="bad">✗ {error}</p>}

      {results && results.length === 0 && (
        <p className="muted">{t("sections.none")}</p>
      )}

      {results && results.length > 0 && (
        <ul className="section-list">
          {results.map((r, idx) => {
            const quality = qualityKey(idx, results.length);
            return (
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
                  <span className={`quality quality-${quality}`}>{t(`quality.${quality}`)}</span>
                  <strong>{r.title}</strong>
                  {r.confirmed && <span className="good"> {t("sections.confirmed")}</span>}
                </div>
                <div className="section-meta muted">
                  {t("sections.match", { pct: Math.round(r.similarity * 100) })}
                  {r.ipc_equivalent ? ` · ${t("sections.ipc", { ipc: r.ipc_equivalent })}` : ""}
                </div>
              </div>
              <div className="section-bar" aria-hidden="true">
                <span style={{ width: `${Math.max(5, Math.round(r.similarity * 100))}%` }} />
              </div>
            </li>
            );
          })}
        </ul>
      )}

      {results && !canConfirm && (
        <p className="hint">{t("sections.cantConfirm", { role: user.role_display })}</p>
      )}
    </section>
  );
}
