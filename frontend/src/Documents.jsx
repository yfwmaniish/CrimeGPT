import { useState } from "react";
import { generateDocument, ApiError } from "./api";

const DOC_TYPES = [
  ["seizure", "Seizure Receipt"],
  ["remand", "Remand Request"],
  ["custody", "Court Custody Letter"],
  ["medical", "Medical Treatment Letter"],
  ["panchanama", "Accused Panchanama"],
  ["faceid", "Face Identification Form"],
  ["chargesheet", "Purvani Chargesheet"],
];

function triggerDownload(url) {
  const a = document.createElement("a");
  a.href = url;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

export default function Documents({ caseId, user, onGenerated }) {
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
      const data = await generateDocument(caseId, key, asPdf);
      setResult((r) => ({ ...r, [key]: data }));
      triggerDownload(data.download_url);
      if (onGenerated) onGenerated(); // generation logged a diary event
    } catch (err) {
      const msg =
        err instanceof ApiError && err.status === 403
          ? "Only an IO or SHO can generate documents."
          : err.message || "Could not generate the document.";
      setError((e) => ({ ...e, [key]: msg }));
    } finally {
      setBusy((b) => ({ ...b, [key]: false }));
    }
  }

  return (
    <section className="card">
      <h2>Generate documents</h2>
      {!canGenerate && (
        <p className="warn">
          Your role ({user.role_display}) cannot generate documents — these
          actions will be refused by the server.
        </p>
      )}
      <p className="hint">
        Every document is filled from this case. Regenerating keeps earlier
        versions. Documents that use legal sections include only confirmed ones.
      </p>

      <ul className="doc-list">
        {DOC_TYPES.map(([key, label]) => {
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
                  <option value="docx">DOCX</option>
                  <option value="pdf">PDF</option>
                </select>
                <button onClick={() => generate(key)} disabled={busy[key]}>
                  {busy[key] ? "Generating…" : "Generate"}
                </button>
                {r && (
                  <a href={r.download_url} rel="noopener" className="doc-dl">
                    Download
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
