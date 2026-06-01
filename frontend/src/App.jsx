import { useEffect, useState } from "react";
import { getHealth, API_BASE } from "./api";
import "./App.css";

function App() {
  const [status, setStatus] = useState("checking…");
  const [error, setError] = useState(null);

  useEffect(() => {
    getHealth()
      .then((data) => setStatus(data.status))
      .catch((err) => setError(err.message));
  }, []);

  return (
    <main className="app">
      <h1>CrimeGPT</h1>
      <p className="tagline">Investigation case management — Week 1 skeleton</p>

      <section className="card">
        <h2>Backend connection</h2>
        {error ? (
          <p className="bad">
            ✗ Could not reach API at <code>{API_BASE}</code>
            <br />
            <small>{error}</small>
          </p>
        ) : (
          <p className={status === "ok" ? "good" : ""}>
            API status: <strong>{status}</strong> <small>({API_BASE})</small>
          </p>
        )}
      </section>

      <section className="card">
        <h2>Coming next (Day 2–5)</h2>
        <ul>
          <li>Create / edit a case</li>
          <li>Add parties and seized items</li>
          <li>Generate &amp; download a Seizure Receipt</li>
        </ul>
      </section>
    </main>
  );
}

export default App;
