import { useState } from "react";
import { createCase, addDiaryEvent, ApiError } from "./api";

const STATUSES = ["COMPLAINT", "INVESTIGATION", "ARREST", "CHARGESHEET"];
const ROLES = [
  ["VICTIM", "Victim / Complainant"],
  ["ACCUSED", "Accused"],
  ["WITNESS", "Witness"],
];
const GENDERS = ["Male", "Female", "Other"];

const emptyParty = () => ({
  role: "ACCUSED",
  name: "",
  parent_name: "",
  age: "",
  gender: "",
  phone: "",
  address: "",
});
const emptyItem = () => ({ description: "", quantity: "", seized_from_index: "", seizure_date: "", seizure_place: "" });

// Flatten DRF error objects into readable lines.
function flattenErrors(data, prefix = "") {
  if (data == null) return [];
  if (typeof data === "string") return [prefix ? `${prefix}: ${data}` : data];
  if (Array.isArray(data)) return data.flatMap((d) => flattenErrors(d, prefix));
  return Object.entries(data).flatMap(([k, v]) =>
    flattenErrors(v, prefix ? `${prefix} → ${k}` : k)
  );
}

export default function CaseForm({ user, onCreated, onCancel }) {
  const [form, setForm] = useState({
    case_number: "",
    fir_number: "",
    fir_date: "",
    police_station: user.police_station || "",
    status: "INVESTIGATION",
    incident_place: "",
    incident_narrative: "",
  });
  const [parties, setParties] = useState([emptyParty()]);
  const [items, setItems] = useState([emptyItem()]);

  const [errors, setErrors] = useState([]);
  const [busy, setBusy] = useState(false);
  const [arrest, setArrest] = useState({ date: "", place: "" });

  const setField = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const updateParty = (i, k, v) =>
    setParties((ps) => ps.map((p, idx) => (idx === i ? { ...p, [k]: v } : p)));
  const updateItem = (i, k, v) =>
    setItems((its) => its.map((it, idx) => (idx === i ? { ...it, [k]: v } : it)));

  async function submitCase(e) {
    e.preventDefault();
    setErrors([]);
    setBusy(true);
    try {
      const payload = {
        ...form,
        parties: parties.map((p) => ({
          role: p.role,
          name: p.name,
          parent_name: p.parent_name,
          age: p.age === "" ? null : Number(p.age),
          gender: p.gender,
          phone: p.phone,
          address: p.address,
        })),
        seized_items: items.map((it) => {
          const o = {
            description: it.description,
            quantity: it.quantity,
            seizure_place: it.seizure_place,
          };
          if (it.seizure_date) o.seizure_date = it.seizure_date;
          if (it.seized_from_index !== "") o.seized_from_index = Number(it.seized_from_index);
          return o;
        }),
      };
      const created = await createCase(payload);

      // If the case is being filed as an arrest, log an ARREST diary event so the
      // Remand Request builder (which reads the latest ARREST event) is populated.
      if (form.status === "ARREST" && (arrest.date || arrest.place)) {
        const where = arrest.place ? ` at ${arrest.place}` : "";
        try {
          await addDiaryEvent(created.id, {
            event_type: "ARREST",
            description: `Accused arrested${where}.`,
            timestamp: arrest.date ? `${arrest.date}T09:00:00` : undefined,
          });
        } catch {
          /* non-fatal: the case is created; arrest detail can be added via the diary */
        }
      }

      onCreated(created);
    } catch (err) {
      setErrors(err instanceof ApiError ? flattenErrors(err.data) : [err.message]);
    } finally {
      setBusy(false);
    }
  }

  // ---- The case creation form ----
  return (
    <form className="stack" onSubmit={submitCase}>
      <button type="button" className="link-btn" onClick={onCancel}>
        ← Back to my cases
      </button>
      <section className="card">
        <h2>Case details</h2>
        <div className="grid2">
          <label>
            Case number*
            <input value={form.case_number} onChange={(e) => setField("case_number", e.target.value)} required />
          </label>
          <label>
            FIR number*
            <input value={form.fir_number} onChange={(e) => setField("fir_number", e.target.value)} required />
          </label>
          <label>
            FIR date*
            <input type="date" value={form.fir_date} onChange={(e) => setField("fir_date", e.target.value)} required />
          </label>
          <label>
            Police station*
            <input value={form.police_station} onChange={(e) => setField("police_station", e.target.value)} required />
          </label>
          <label>
            Status
            <select value={form.status} onChange={(e) => setField("status", e.target.value)}>
              {STATUSES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </label>
          <label>
            Place of incident
            <input value={form.incident_place} onChange={(e) => setField("incident_place", e.target.value)} />
          </label>
        </div>

        {form.status === "ARREST" && (
          <div className="grid2 arrest-fields">
            <label>
              Arrest date
              <input type="date" value={arrest.date} onChange={(e) => setArrest((a) => ({ ...a, date: e.target.value }))} />
            </label>
            <label>
              Place of arrest
              <input value={arrest.place} onChange={(e) => setArrest((a) => ({ ...a, place: e.target.value }))} placeholder="e.g. near Kalupur bus stand" />
            </label>
            <p className="hint" style={{ gridColumn: "1 / -1", margin: 0 }}>
              Recorded as an arrest entry in the case diary, and used by the Remand Request.
            </p>
          </div>
        )}

        <label>
          What happened (narrative)
          <textarea
            rows={3}
            value={form.incident_narrative}
            onChange={(e) => setField("incident_narrative", e.target.value)}
          />
        </label>
      </section>

      <section className="card">
        <div className="row-head">
          <h2>People involved</h2>
          <button type="button" className="add" onClick={() => setParties((p) => [...p, emptyParty()])}>
            + Add person
          </button>
        </div>
        {parties.map((p, i) => (
          <div className="person" key={i}>
            {parties.length > 1 && (
              <button
                type="button"
                className="del person-del"
                title="Remove person"
                onClick={() => setParties((ps) => ps.filter((_, idx) => idx !== i))}
              >
                ✕
              </button>
            )}
            <div className="person-grid">
              <select value={p.role} onChange={(e) => updateParty(i, "role", e.target.value)}>
                {ROLES.map(([v, label]) => (
                  <option key={v} value={v}>{label}</option>
                ))}
              </select>
              <input placeholder="Name" value={p.name} onChange={(e) => updateParty(i, "name", e.target.value)} />
              <input placeholder="Father's/Husband's name" value={p.parent_name} onChange={(e) => updateParty(i, "parent_name", e.target.value)} />
              <input
                type="number"
                min="0"
                placeholder="Age"
                value={p.age}
                onChange={(e) => updateParty(i, "age", e.target.value)}
              />
              <select value={p.gender} onChange={(e) => updateParty(i, "gender", e.target.value)}>
                <option value="">Gender…</option>
                {GENDERS.map((g) => (
                  <option key={g} value={g}>{g}</option>
                ))}
              </select>
              <input placeholder="Phone" value={p.phone} onChange={(e) => updateParty(i, "phone", e.target.value)} />
              <input
                className="person-address"
                placeholder="Address"
                value={p.address}
                onChange={(e) => updateParty(i, "address", e.target.value)}
              />
            </div>
          </div>
        ))}
      </section>

      <section className="card">
        <div className="row-head">
          <h2>Seized items</h2>
          <button type="button" className="add" onClick={() => setItems((it) => [...it, emptyItem()])}>
            + Add item
          </button>
        </div>
        {items.map((it, i) => (
          <div className="subrow" key={i}>
            <input placeholder="Description" value={it.description} onChange={(e) => updateItem(i, "description", e.target.value)} />
            <input placeholder="Quantity" value={it.quantity} onChange={(e) => updateItem(i, "quantity", e.target.value)} />
            <select
              value={it.seized_from_index}
              onChange={(e) => updateItem(i, "seized_from_index", e.target.value)}
              title="Seized from"
            >
              <option value="">Seized from… (none)</option>
              {parties.map((p, idx) => (
                <option key={idx} value={idx}>
                  {p.name || `Person ${idx + 1}`} ({p.role})
                </option>
              ))}
            </select>
            <input type="date" title="Seizure date" value={it.seizure_date} onChange={(e) => updateItem(i, "seizure_date", e.target.value)} />
            <input placeholder="Place of seizure" value={it.seizure_place} onChange={(e) => updateItem(i, "seizure_place", e.target.value)} />
            {items.length > 1 && (
              <button type="button" className="del" onClick={() => setItems((its) => its.filter((_, idx) => idx !== i))}>
                ✕
              </button>
            )}
          </div>
        ))}
      </section>

      {errors.length > 0 && (
        <section className="card bad-card">
          <strong>Please fix the following:</strong>
          <ul>
            {errors.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </section>
      )}

      <button type="submit" className="primary" disabled={busy}>
        {busy ? "Saving…" : "Save case"}
      </button>
    </form>
  );
}
