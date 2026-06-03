import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { getToken, logout as apiLogout, me } from "./api";
import { LANGUAGES } from "./i18n";
import Login from "./Login";
import CaseList from "./CaseList";
import CaseForm from "./CaseForm";
import CaseView from "./CaseView";
import "./App.css";

function LanguageSwitcher() {
  const { i18n, t } = useTranslation();
  return (
    <select
      className="lang-select"
      aria-label={t("lang.label")}
      value={i18n.language}
      onChange={(e) => i18n.changeLanguage(e.target.value)}
    >
      {LANGUAGES.map(([code, label]) => (
        <option key={code} value={code}>{label}</option>
      ))}
    </select>
  );
}

function App() {
  const { t } = useTranslation();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  // view: {mode:"list"} | {mode:"new"} | {mode:"case", caseData, justCreated}
  const [view, setView] = useState({ mode: "list" });

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
    setView({ mode: "list" });
  }

  if (loading) {
    return (
      <main className="app narrow">
        <p>{t("common.loading")}</p>
      </main>
    );
  }

  if (!user) {
    return <Login onLoggedIn={setUser} />;
  }

  return (
    <main className="app">
      <header className="topbar">
        <div
          onClick={() => setView({ mode: "list" })}
          style={{ cursor: "pointer" }}
          title={t("list.title")}
        >
          <h1>{t("brand")}</h1>
          <p className="tagline">{t("tagline")}</p>
        </div>
        <div className="userbox">
          <LanguageSwitcher />
          <span>
            {user.username} · <strong>{user.role_display || t("common.noRole")}</strong>
          </span>
          <button className="link-btn" onClick={handleLogout}>
            {t("common.signOut")}
          </button>
        </div>
      </header>

      {view.mode === "list" && (
        <CaseList
          onNew={() => setView({ mode: "new" })}
          onOpen={(caseData) => setView({ mode: "case", caseData, justCreated: false })}
        />
      )}

      {view.mode === "new" && (
        <CaseForm
          user={user}
          onCreated={(caseData) => setView({ mode: "case", caseData, justCreated: true })}
          onCancel={() => setView({ mode: "list" })}
        />
      )}

      {view.mode === "case" && (
        <CaseView
          caseData={view.caseData}
          user={user}
          justCreated={view.justCreated}
          onBack={() => setView({ mode: "list" })}
        />
      )}
    </main>
  );
}

export default App;
