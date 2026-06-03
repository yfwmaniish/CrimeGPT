import { useEffect, useState } from "react";
import { listCases } from "./api";

function fmtDate(ts) {
  try {
    return new Date(ts).toLocaleDateString();
  } catch {
    return ts;
  }
}

export default function CaseList({ onOpen, onNew }) {
  const [cases, setCases] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    listCases()
      .then((data) => setCases(data.results))
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div className="stack">
      <div className="row-head">
        <h2>My cases</h2>
        <button className="add" onClick={onNew}>+ New case</button>
      </div>

      {error && <p className="bad">✗ {error}</p>}
      {!error && cases === null && <p className="muted">Loading…</p>}

      {cases && cases.length === 0 && (
        <section className="card">
          <p className="muted">No cases yet.</p>
          <button onClick={onNew}>Create your first case</button>
        </section>
      )}

      {cases && cases.length > 0 && (
        <section className="card">
          <table className="case-table">
            <thead>
              <tr>
                <th>Case no.</th>
                <th>FIR no.</th>
                <th>Police station</th>
                <th>Status</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => (
                <tr key={c.id} className="case-row" onClick={() => onOpen(c)} tabIndex={0}
                    onKeyDown={(e) => { if (e.key === "Enter") onOpen(c); }}>
                  <td><strong>{c.case_number}</strong></td>
                  <td>{c.fir_number}</td>
                  <td>{c.police_station}</td>
                  <td><span className="tag">{c.status}</span></td>
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
