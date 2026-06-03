import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { listCases } from "./api";

function fmtDate(ts) {
  try {
    return new Date(ts).toLocaleDateString();
  } catch {
    return ts;
  }
}

export default function CaseList({ onOpen, onNew }) {
  const { t } = useTranslation();
  const [query, setQuery] = useState("");
  const [cases, setCases] = useState(null);
  const [error, setError] = useState(null);

  // Debounced search (~300ms). Empty query restores the full list.
  useEffect(() => {
    const term = query.trim();
    const handle = setTimeout(() => {
      setError(null);
      listCases(term)
        .then((data) => setCases(data.results))
        .catch((err) => setError(err.message));
    }, 300);
    return () => clearTimeout(handle);
  }, [query]);

  return (
    <div className="stack">
      <div className="row-head">
        <h2>{t("list.title")}</h2>
        <button className="add" onClick={onNew}>{t("list.newCase")}</button>
      </div>

      <input
        className="search-input"
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={t("list.searchPlaceholder")}
        aria-label={t("list.searchPlaceholder")}
      />

      {error && <p className="bad">✗ {error}</p>}
      {!error && cases === null && <p className="muted">{t("common.loading")}</p>}

      {cases && cases.length === 0 && (
        <section className="card">
          {query.trim() ? (
            <p className="muted">{t("list.noResults")}</p>
          ) : (
            <>
              <p className="muted">{t("list.empty")}</p>
              <button onClick={onNew}>{t("list.createFirst")}</button>
            </>
          )}
        </section>
      )}

      {cases && cases.length > 0 && (
        <section className="card">
          <table className="case-table">
            <thead>
              <tr>
                <th>{t("list.colCase")}</th>
                <th>{t("list.colFir")}</th>
                <th>{t("list.colStation")}</th>
                <th>{t("list.colStatus")}</th>
                <th>{t("list.colCreated")}</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => (
                <tr key={c.id} className="case-row" onClick={() => onOpen(c)} tabIndex={0}
                    onKeyDown={(e) => { if (e.key === "Enter") onOpen(c); }}>
                  <td><strong>{c.case_number}</strong></td>
                  <td>{c.fir_number}</td>
                  <td>{c.police_station}</td>
                  <td><span className="tag">{t(`statuses.${c.status}`)}</span></td>
                  <td className="muted">{fmtDate(c.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
