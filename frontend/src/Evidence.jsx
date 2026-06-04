import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { listEvidence, uploadEvidence, deleteEvidence, ApiError } from "./api";

export default function Evidence({ caseId, user }) {
  const { t } = useTranslation();
  const [items, setItems] = useState(null);
  const [error, setError] = useState(null);
  const [tagFilter, setTagFilter] = useState("");

  const [description, setDescription] = useState("");
  const [tags, setTags] = useState("");
  const [busy, setBusy] = useState(false);
  const fileRef = useRef(null);

  const canManage = user.can_generate_documents; // IO/SHO

  const load = useCallback(() => {
    listEvidence(caseId, tagFilter.trim())
      .then((data) => setItems(data.results))
      .catch((err) => setError(err.message));
  }, [caseId, tagFilter]);

  // Debounce the tag filter; also the initial load.
  useEffect(() => {
    const h = setTimeout(load, 250);
    return () => clearTimeout(h);
  }, [load]);

  async function submit(e) {
    e.preventDefault();
    setError(null);
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setError(t("evidence.pickFile"));
      return;
    }
    setBusy(true);
    try {
      await uploadEvidence(caseId, { file, description: description.trim(), tags: tags.trim() });
      setDescription(""); setTags("");
      if (fileRef.current) fileRef.current.value = "";
      load();
    } catch (err) {
      setError(err instanceof ApiError ? (err.data?.image?.[0] || err.message) : err.message);
    } finally {
      setBusy(false);
    }
  }

  async function remove(id) {
    setError(null);
    try {
      await deleteEvidence(id);
      load();
    } catch (err) {
      setError(err instanceof ApiError && err.status === 403 ? t("evidence.onlyOfficer") : err.message);
    }
  }

  return (
    <section className="card">
      <h2>{t("evidence.title")}</h2>
      <p className="hint">{t("evidence.hint")}</p>

      {canManage && (
        <form className="evidence-add" onSubmit={submit}>
          <div className="subrow">
            <input type="file" accept="image/*" ref={fileRef} />
            <input placeholder={t("evidence.description")} value={description} onChange={(e) => setDescription(e.target.value)} />
            <input placeholder={t("evidence.tags")} value={tags} onChange={(e) => setTags(e.target.value)} />
            <button type="submit" disabled={busy}>{busy ? t("evidence.uploading") : t("evidence.upload")}</button>
          </div>
        </form>
      )}

      <input
        className="search-input"
        type="search"
        value={tagFilter}
        onChange={(e) => setTagFilter(e.target.value)}
        placeholder={t("evidence.tagFilter")}
      />

      {error && <p className="bad">✗ {error}</p>}
      {items === null && !error && <p className="muted">{t("common.loading")}</p>}
      {items && items.length === 0 && <p className="muted">{t("evidence.none")}</p>}

      {items && items.length > 0 && (
        <div className="evidence-grid">
          {items.map((e) => (
            <figure key={e.id} className="evidence-card">
              <a href={e.image} target="_blank" rel="noopener">
                <img src={e.image} alt={e.description || "evidence"} className="evidence-thumb" />
              </a>
              <figcaption>
                <div className="evidence-desc">{e.description || "—"}</div>
                {e.tag_list?.length > 0 && (
                  <div className="evidence-tags">
                    {e.tag_list.map((tg) => <span key={tg} className="tag">{tg}</span>)}
                  </div>
                )}
                <div className="muted evidence-meta">
                  {e.uploaded_by ? t("diary.by", { actor: e.uploaded_by }) : ""}
                  {canManage && (
                    <button type="button" className="link-btn evidence-del" onClick={() => remove(e.id)}>
                      {t("evidence.delete")}
                    </button>
                  )}
                </div>
              </figcaption>
            </figure>
          ))}
        </div>
      )}

      {!canManage && <p className="hint">{t("evidence.cantManage", { role: user.role_display })}</p>}
    </section>
  );
}
