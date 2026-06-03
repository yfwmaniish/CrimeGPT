import { useState } from "react";
import Sections from "./Sections";
import Documents from "./Documents";
import Diary from "./Diary";

// The working view for a single case — used both right after creating a case and
// when reopening one from the case list. `caseData` needs at least { id,
// case_number, fir_number, police_station, status }.
export default function CaseView({ caseData, user, justCreated = false, onBack }) {
  const [diaryRefresh, setDiaryRefresh] = useState(0);

  return (
    <div className="stack">
      <section className={justCreated ? "card good-card" : "card"}>
        <h2>
          {justCreated && "✓ "}
          {caseData.case_number}
        </h2>
        <p className="muted">
          FIR {caseData.fir_number}
          {caseData.police_station ? ` · ${caseData.police_station}` : ""}
          {caseData.status ? ` · ${caseData.status}` : ""}
        </p>
      </section>

      <Sections caseId={caseData.id} user={user} />

      <Documents
        caseId={caseData.id}
        user={user}
        onGenerated={() => setDiaryRefresh((n) => n + 1)}
      />

      <Diary caseId={caseData.id} user={user} refreshSignal={diaryRefresh} />

      <button className="link-btn" onClick={onBack}>
        ← Back to my cases
      </button>
    </div>
  );
}
