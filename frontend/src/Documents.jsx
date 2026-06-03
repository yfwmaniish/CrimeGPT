import { useState } from "react";
import { useTranslation } from "react-i18next";
import { generateDocument, ApiError } from "./api";

const DOC_TYPES = ["seizure", "remand", "custody", "medical", "panchanama", "faceid", "chargesheet"];

function triggerDownload(url) {
  const a = document.createElement("a");
  a.href = url;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

export default function Documents({ caseId, user, onGenerated }) {
  const { t, i18n } = useTranslation();
  // per-doc UI state, keyed by doc type
  const [fmt, setFmt] = useState({}); // key -> "docx" | "pdf"
  const [busy, setBusy] = useState({});
  const [result, setResult] = useState({}); // key -> { version, download_url }
  const [error, setError] = useState({});

  const canGenerate = user.can_generate_documents;

  async function generate(key) {
    setError((e) => ({ ...e, [key]: null }));
    setBusy((b) => ({ ...b, [key]: true }));
    try {
      const asPdf = (fmt[key] || "docx") === "pdf";
      // Pass the current UI language; only the Seizure Receipt has translated
      // templates so far — the others fall back to English server-side.
      const data = await generateDocument(caseId, key, asPdf, i18n.language);
      setResult((r) => ({ ...r, [key]: data }));
      triggerDownload(data.download_url);
      if (onGenerated) onGenerated(); // generation logged a diary event
    } catch (err) {
      const msg =
        err instanceof ApiError && err.status === 403
          ? t("documents.onlyOfficer")
          : err.message || t("documents.failed");
      setError((e) => ({ ...e, [key]: msg }));
    } finally {
      setBusy((b) => ({ ...b, [key]: false }));
    }
  }

  return (
    <section className="card">
      <h2>{t("documents.title")}</h2>
      {!canGenerate && (
        <p className="warn">{t("documents.warn", { role: user.role_display })}</p>
      )}
      <p className="hint">{t("documents.hint")}</p>

      <ul className="doc-list">
        {DOC_TYPES.map((key) => {
          const label = t(`docTypes.${key}`);
          const r = result[key];
          const format = fmt[key] || "docx";
          return (
            <li key={key} className="doc-row">
              <div className="doc-name">
                {label}
                {r && <span className="good"> · v{r.version}</span>}
              </div>
              <div className="doc-actions">
                <select
                  value={format}
                  onChange={(e) => setFmt((f) => ({ ...f, [key]: e.target.value }))}
                  aria-label={`${label} format`}
                >
                  <option value="docx">{t("documents.formatDocx")}</option>
                  <option value="pdf">{t("documents.formatPdf")}</option>
                </select>
                <button onClick={() => generate(key)} disabled={busy[key]}>
                  {busy[key] ? t("documents.generating") : t("documents.generate")}
                </button>
                {r && (
                  <a href={r.download_url} rel="noopener" className="doc-dl">
                    {t("documents.download")}
                  </a>
                )}
              </div>
              {error[key] && <p className="bad doc-error">✗ {error[key]}</p>}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
