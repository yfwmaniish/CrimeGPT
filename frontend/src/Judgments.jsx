import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { getJudgments, suggestJudgments, applyJudgment, ApiError } from "./api";
import { qualityKey } from "./quality";

export default function Judgments({ caseId, user }) {
  const { t } = useTranslation();
  // judgments keyed by id, so by-section and by-narrative results merge cleanly.
  const [byId, setById] = useState({});
  const [error, setError] = useState(null);
  const [suggesting, setSuggesting] = useState(false);
  const [pending, setPending] = useState({});

  const canApply = user.can_generate_documents; // IO/SHO

  const merge = useCallback((list) => {
    setById((prev) => {
      const next = { ...prev };
      for (const j of list) next[j.id] = { ...next[j.id], ...j };
      return next;
    });
  }, []);

  // On load, show judgments relevant to the case's confirmed sections.
  useEffect(() => {
    getJudgments(caseId)
      .then((data) => merge(data.results))
      .catch((err) => setError(err.message));
  }, [caseId, merge]);

  async function suggest() {
    setError(null);
    setSuggesting(true);
    try {
      const data = await suggestJudgments(caseId, 5);
      // Relative quality badge from rank in this query's returned list.
      merge(data.results.map((r, idx) => ({ ...r, quality: qualityKey(idx, data.results.length) })));
    } catch (err) {
      setError(err instanceof ApiError && err.status === 400
        ? t("sections.needNarrative")
        : err.message || t("judgments.getFailed"));
    } finally {
      setSuggesting(false);
    }
  }

  async function toggle(j, applied) {
    setError(null);
    setPending((p) => ({ ...p, [j.id]: true }));
    try {
      const updated = await applyJudgment(caseId, j.id, applied);
      merge([{ id: j.id, applied: updated.applied }]);
    } catch (err) {
      setError(err instanceof ApiError && err.status === 403
        ? t("judgments.onlyOfficer")
        : err.message || t("judgments.updateFailed"));
    } finally {
      setPending((p) => ({ ...p, [j.id]: false }));
    }
  }

  // Applied first, then by similarity (if present), then title.
  const rows = Object.values(byId).sort((a, b) => {
    if (a.applied !== b.applied) return a.applied ? -1 : 1;
    if ((b.similarity || 0) !== (a.similarity || 0)) return (b.similarity || 0) - (a.similarity || 0);
    return (a.title || "").localeCompare(b.title || "");
  });

  return (
    <section className="card">
      <h2>{t("judgments.title")}</h2>
      <p className="hint">{t("judgments.hint")}</p>

      <button onClick={suggest} disabled={suggesting}>
        {suggesting ? t("judgments.suggesting") : t("judgments.suggest")}
      </button>
      {error && <p className="bad">✗ {error}</p>}

      {rows.length === 0 && <p className="muted">{t("judgments.none")}</p>}

      {rows.length > 0 && (
        <ul className="judgment-list">
          {rows.map((j) => (
            <li key={j.id} className={j.applied ? "judgment-row applied" : "judgment-row"}>
              <label className="section-confirm">
                <input
                  type="checkbox"
                  checked={!!j.applied}
                  disabled={!canApply || pending[j.id]}
                  onChange={(e) => toggle(j, e.target.checked)}
                />
              </label>
              <div className="judgment-main">
                <div className="judgment-head">
                  {j.quality && (
                    <span className={`quality quality-${j.quality}`}>{t(`quality.${j.quality}`)}</span>
                  )}
                  <strong>{j.title}</strong>
                  <span className="tag">{j.citation}</span>
                  {typeof j.similarity === "number" && (
                    <span className="muted">{t("sections.match", { pct: Math.round(j.similarity * 100) })}</span>
                  )}
                  {j.applied && <span className="good"> {t("judgments.applied")}</span>}
                </div>
                <p className="judgment-principle">{j.principle}</p>
              </div>
            </li>
          ))}
        </ul>
      )}

      {!canApply && (
        <p className="hint">{t("judgments.cantApply", { role: user.role_display })}</p>
      )}
    </section>
  );
}
