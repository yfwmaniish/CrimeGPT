import { useState } from "react";
import { useTranslation } from "react-i18next";
import { login } from "./api";

export default function Login({ onLoggedIn }) {
  const { t } = useTranslation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const user = await login(username.trim(), password);
      onLoggedIn(user);
    } catch (err) {
      setError(err.message || t("login.failed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="app narrow">
      <h1>{t("brand")}</h1>
      <p className="tagline">{t("login.subtitle")}</p>

      <form className="card" onSubmit={submit}>
        <label>
          {t("login.username")}
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            required
          />
        </label>
        <label>
          {t("login.password")}
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>

        {error && <p className="bad">✗ {error}</p>}

        <button type="submit" disabled={busy}>
          {busy ? t("login.signingIn") : t("login.signIn")}
        </button>
        <p className="hint">{t("login.hint")}</p>
      </form>
    </main>
  );
}
