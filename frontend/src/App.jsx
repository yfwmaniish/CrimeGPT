import { useEffect, useState } from "react";
import { getToken, logout as apiLogout, me } from "./api";
import Login from "./Login";
import CaseForm from "./CaseForm";
import "./App.css";

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // On load, if we have a stored token, restore the session.
  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    me()
      .then(setUser)
      .catch(() => apiLogout())
      .finally(() => setLoading(false));
  }, []);

  function handleLogout() {
    apiLogout();
    setUser(null);
  }

  if (loading) {
    return (
      <main className="app narrow">
        <p>Loading…</p>
      </main>
    );
  }

  if (!user) {
    return <Login onLoggedIn={setUser} />;
  }

  return (
    <main className="app">
      <header className="topbar">
        <div>
          <h1>CrimeGPT</h1>
          <p className="tagline">New case → Seizure Receipt</p>
        </div>
        <div className="userbox">
          <span>
            {user.username} · <strong>{user.role_display || "no role"}</strong>
          </span>
          <button className="link-btn" onClick={handleLogout}>
            Sign out
          </button>
        </div>
      </header>

      <CaseForm user={user} />
    </main>
  );
}

export default App;
