import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { getDiary, addDiaryEvent, ApiError } from "./api";

// Icons for known event types; labels come from i18n.
const EVENT_ICONS = {
  FIR_REGISTERED: "📝",
  INVESTIGATION: "🔎",
  SEIZURE: "📦",
  DOCUMENT_GENERATED: "📄",
  ARREST: "🚓",
  STATEMENT_RECORDED: "🗣️",
  MANUAL: "✏️",
};

function fmt(ts) {
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return ts;
  }
}

export default function Diary({ caseId, user, refreshSignal }) {
  const { t } = useTranslation();
  const eventLabel = (type) =>
    t(`diary.events.${type}`, { defaultValue: type.replaceAll("_", " ") });
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [eventType, setEventType] = useState("");
  const [description, setDescription] = useState("");
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    getDiary(caseId)
      .then((data) => setEvents(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [caseId]);

  useEffect(() => {
    load();
  }, [load, refreshSignal]);

  async function submit(e) {
    e.preventDefault();
    setAddError(null);
    setAdding(true);
    try {
      await addDiaryEvent(caseId, {
        event_type: eventType.trim(),
        description: description.trim(),
      });
      setEventType("");
      setDescription("");
      load();
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setAddError(t("diary.cantAdd", { role: user.role_display }));
      } else {
        setAddError(err.message || t("diary.failed"));
      }
    } finally {
      setAdding(false);
    }
  }

  return (
    <section className="card">
      <h2>{t("diary.title")}</h2>

      {loading && <p className="muted">{t("common.loading")}</p>}
      {error && <p className="bad">✗ {error}</p>}

      {!loading && !error && events.length === 0 && (
        <p className="muted">{t("diary.none")}</p>
      )}

      {events.length > 0 && (
        <ol className="timeline">
          {events.map((ev) => (
            <li key={ev.id} className="timeline-item">
              <span className="timeline-dot" aria-hidden="true">
                {EVENT_ICONS[ev.event_type] || "•"}
              </span>
              <div className="timeline-body">
                <div className="timeline-head">
                  <span className="tag">{eventLabel(ev.event_type)}</span>
                  <span className="muted">{fmt(ev.timestamp)}</span>
                </div>
                <p className="timeline-desc">{ev.description}</p>
                {ev.actor && <p className="muted">{t("diary.by", { actor: ev.actor })}</p>}
              </div>
            </li>
          ))}
        </ol>
      )}

      {user.can_generate_documents ? (
        <form className="diary-add" onSubmit={submit}>
          <h3>{t("diary.addStep")}</h3>
          <div className="subrow">
            <input
              placeholder={t("diary.typePlaceholder")}
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
            />
            <input
              placeholder={t("diary.descPlaceholder")}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
              style={{ flex: "2 1 220px" }}
            />
            <button type="submit" disabled={adding}>
              {adding ? t("diary.adding") : t("diary.add")}
            </button>
          </div>
          {addError && <p className="bad">✗ {addError}</p>}
        </form>
      ) : (
        <p className="hint">{t("diary.cantAdd", { role: user.role_display })}</p>
      )}
    </section>
  );
}
