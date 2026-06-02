import { useCallback, useEffect, useState } from "react";
import { getDiary, addDiaryEvent, ApiError } from "./api";

// Friendly labels + icons for known auto-logged event types.
const EVENT_META = {
  FIR_REGISTERED: { label: "FIR Registered", icon: "📝" },
  INVESTIGATION: { label: "Investigation", icon: "🔎" },
  SEIZURE: { label: "Seizure", icon: "📦" },
  DOCUMENT_GENERATED: { label: "Document Generated", icon: "📄" },
  ARREST: { label: "Arrest", icon: "🚓" },
  STATEMENT_RECORDED: { label: "Statement Recorded", icon: "🗣️" },
  MANUAL: { label: "Note", icon: "✏️" },
};

function metaFor(type) {
  return EVENT_META[type] || { label: type.replaceAll("_", " "), icon: "•" };
}

function fmt(ts) {
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return ts;
  }
}

export default function Diary({ caseId, user, refreshSignal }) {
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
        setAddError("Your role can view the diary but not add entries (IO/SHO only).");
      } else {
        setAddError(err.message || "Could not add the entry.");
      }
    } finally {
      setAdding(false);
    }
  }

  return (
    <section className="card">
      <h2>Case diary</h2>

      {loading && <p className="muted">Loading…</p>}
      {error && <p className="bad">✗ {error}</p>}

      {!loading && !error && events.length === 0 && (
        <p className="muted">No events yet.</p>
      )}

      {events.length > 0 && (
        <ol className="timeline">
          {events.map((ev) => {
            const m = metaFor(ev.event_type);
            return (
              <li key={ev.id} className="timeline-item">
                <span className="timeline-dot" aria-hidden="true">{m.icon}</span>
                <div className="timeline-body">
                  <div className="timeline-head">
                    <span className="tag">{m.label}</span>
                    <span className="muted">{fmt(ev.timestamp)}</span>
                  </div>
                  <p className="timeline-desc">{ev.description}</p>
                  {ev.actor && <p className="muted">by {ev.actor}</p>}
                </div>
              </li>
            );
          })}
        </ol>
      )}

      {user.can_generate_documents ? (
        <form className="diary-add" onSubmit={submit}>
          <h3>Add a step</h3>
          <div className="subrow">
            <input
              placeholder="Type (optional, e.g. WITNESS_INTERVIEWED)"
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
            />
            <input
              placeholder="What happened? (e.g. Interviewed the shopkeeper)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
              style={{ flex: "2 1 220px" }}
            />
            <button type="submit" disabled={adding}>
              {adding ? "Adding…" : "Add"}
            </button>
          </div>
          {addError && <p className="bad">✗ {addError}</p>}
        </form>
      ) : (
        <p className="hint">Your role ({user.role_display}) can view the diary but not add entries.</p>
      )}
    </section>
  );
}
