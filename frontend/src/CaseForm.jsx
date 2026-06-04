import { useState } from "react";
import { useTranslation } from "react-i18next";
import { createCase, addDiaryEvent, uploadPartyPhoto, ApiError } from "./api";

const STATUSES = ["COMPLAINT", "INVESTIGATION", "ARREST", "CHARGESHEET"];
const ROLES = ["VICTIM", "ACCUSED", "WITNESS"];
// Gender values are stored canonically (English); only the labels are translated.
const GENDERS = [["Male", "male"], ["Female", "female"], ["Other", "other"]];

const emptyParty = () => ({
  role: "ACCUSED",
  name: "",
  parent_name: "",
  age: "",
  gender: "",
  phone: "",
  address: "",
  photoFile: null, // transient — uploaded after the case is created
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
  const { t } = useTranslation();
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

      // Upload accused photos (Face ID). Matched to the saved party by name+role.
      for (const p of parties) {
        if (p.role === "ACCUSED" && p.photoFile && created.parties) {
          const match = created.parties.find((cp) => cp.role === "ACCUSED" && cp.name === p.name);
          if (match) {
            try {
              await uploadPartyPhoto(created.id, match.id, p.photoFile);
            } catch {
              /* non-fatal: photo can be added later */
            }
          }
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
        {t("common.back")}
      </button>
      <section className="card">
        <h2>{t("form.details")}</h2>
        <div className="grid2">
          <label>
            {t("form.caseNumber")}
            <input value={form.case_number} onChange={(e) => setField("case_number", e.target.value)} required />
          </label>
          <label>
            {t("form.firNumber")}
            <input value={form.fir_number} onChange={(e) => setField("fir_number", e.target.value)} required />
          </label>
          <label>
            {t("form.firDate")}
            <input type="date" value={form.fir_date} onChange={(e) => setField("fir_date", e.target.value)} required />
          </label>
          <label>
            {t("form.policeStation")}
            <input value={form.police_station} onChange={(e) => setField("police_station", e.target.value)} required />
          </label>
          <label>
            {t("form.status")}
            <select value={form.status} onChange={(e) => setField("status", e.target.value)}>
              {STATUSES.map((s) => (
                <option key={s} value={s}>{t(`statuses.${s}`)}</option>
              ))}
            </select>
          </label>
          <label>
            {t("form.placeOfIncident")}
            <input value={form.incident_place} onChange={(e) => setField("incident_place", e.target.value)} />
          </label>
        </div>

        {form.status === "ARREST" && (
          <div className="grid2 arrest-fields">
            <label>
              {t("form.arrestDate")}
              <input type="date" value={arrest.date} onChange={(e) => setArrest((a) => ({ ...a, date: e.target.value }))} />
            </label>
            <label>
              {t("form.placeOfArrest")}
              <input value={arrest.place} onChange={(e) => setArrest((a) => ({ ...a, place: e.target.value }))} placeholder={t("form.arrestPlacePlaceholder")} />
            </label>
            <p className="hint" style={{ gridColumn: "1 / -1", margin: 0 }}>
              {t("form.arrestNote")}
            </p>
          </div>
        )}

        <label>
          {t("form.narrative")}
          <textarea
            rows={3}
            value={form.incident_narrative}
            onChange={(e) => setField("incident_narrative", e.target.value)}
          />
        </label>
      </section>

      <section className="card">
        <div className="row-head">
          <h2>{t("form.people")}</h2>
          <button type="button" className="add" onClick={() => setParties((p) => [...p, emptyParty()])}>
            {t("form.addPerson")}
          </button>
        </div>
        {parties.map((p, i) => (
          <div className="person" key={i}>
            {parties.length > 1 && (
              <button
                type="button"
                className="del person-del"
                title={t("form.removePerson")}
                onClick={() => setParties((ps) => ps.filter((_, idx) => idx !== i))}
              >
                ✕
              </button>
            )}
            <div className="person-grid">
              <select value={p.role} onChange={(e) => updateParty(i, "role", e.target.value)}>
                {ROLES.map((v) => (
                  <option key={v} value={v}>{t(`roles.${v}`)}</option>
                ))}
              </select>
              <input placeholder={t("form.name")} value={p.name} onChange={(e) => updateParty(i, "name", e.target.value)} />
              <input placeholder={t("form.parentName")} value={p.parent_name} onChange={(e) => updateParty(i, "parent_name", e.target.value)} />
              <input
                type="number"
                min="0"
                placeholder={t("form.age")}
                value={p.age}
                onChange={(e) => updateParty(i, "age", e.target.value)}
              />
              <select value={p.gender} onChange={(e) => updateParty(i, "gender", e.target.value)}>
                <option value="">{t("form.genderPlaceholder")}</option>
                {GENDERS.map(([value, key]) => (
                  <option key={value} value={value}>{t(`genders.${key}`)}</option>
                ))}
              </select>
              <input placeholder={t("form.phone")} value={p.phone} onChange={(e) => updateParty(i, "phone", e.target.value)} />
              <input
                className="person-address"
                placeholder={t("form.address")}
                value={p.address}
                onChange={(e) => updateParty(i, "address", e.target.value)}
              />
              {p.role === "ACCUSED" && (
                <label className="person-photo">
                  {t("form.photo")}
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(e) => updateParty(i, "photoFile", e.target.files?.[0] || null)}
                  />
                </label>
              )}
            </div>
          </div>
        ))}
      </section>

      <section className="card">
        <div className="row-head">
          <h2>{t("form.items")}</h2>
          <button type="button" className="add" onClick={() => setItems((it) => [...it, emptyItem()])}>
            {t("form.addItem")}
          </button>
        </div>
        {items.map((it, i) => (
          <div className="subrow" key={i}>
            <input placeholder={t("form.description")} value={it.description} onChange={(e) => updateItem(i, "description", e.target.value)} />
            <input placeholder={t("form.quantity")} value={it.quantity} onChange={(e) => updateItem(i, "quantity", e.target.value)} />
            <select
              value={it.seized_from_index}
              onChange={(e) => updateItem(i, "seized_from_index", e.target.value)}
              title={t("form.seizedFromNone")}
            >
              <option value="">{t("form.seizedFromNone")}</option>
              {parties.map((p, idx) => (
                <option key={idx} value={idx}>
                  {p.name || t("form.personN", { n: idx + 1 })} ({t(`roles.${p.role}`)})
                </option>
              ))}
            </select>
            <input type="date" title={t("form.seizureDate")} value={it.seizure_date} onChange={(e) => updateItem(i, "seizure_date", e.target.value)} />
            <input placeholder={t("form.placeOfSeizure")} value={it.seizure_place} onChange={(e) => updateItem(i, "seizure_place", e.target.value)} />
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
          <strong>{t("form.fixErrors")}</strong>
          <ul>
            {errors.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </section>
      )}

      <button type="submit" className="primary" disabled={busy}>
        {busy ? t("form.saving") : t("form.save")}
      </button>
    </form>
  );
}
