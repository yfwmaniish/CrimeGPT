# Sample FIR Narratives (for testing & demos)

> **These are anonymized fictional narratives for testing and demonstration. No
> real persons or cases.** All names, parentage, ages, addresses, and phone
> numbers below are invented and intentionally generic (e.g. "Test Nagar",
> 90000-0xxxx numbers). Paste a narrative into a case's *incident narrative*, add
> the listed parties and seized items, then run **Suggest BNS Sections** to
> exercise retrieval across BNS / BNSS / BSA.

Each entry lists: a short title, the kind of incident, the codes it should
exercise, a paste-ready narrative, suggested party fields, and seized items where
relevant.

---

## 1. Shop break-in and theft
**Incident:** Burglary / theft from a commercial premises (night) · **Codes:** BNS (theft, house-breaking, stolen property)

**Narrative:**
> On the night of 27 May 2026, the accused broke open the shutter lock of the
> complainant's electronics shop on Relief Road and stole four mobile phones and
> cash from inside the shop. Two passers-by saw the accused fleeing with a bag of
> stolen goods. The stolen articles were later recovered from the accused.

**Parties:**
- **Victim/Complainant** — Rajesh Patel, s/o Manilal Patel, 45, Male, 22 Test Nagar, Sample City, 90000-01111
- **Accused** — Imran Shaikh, s/o Yusuf Shaikh, 26, Male, 5 Example Colony, Sample City
- **Witness** — Kiran Mehta, s/o Dinesh Mehta, 34, Male, 8 Relief Road, Sample City
- **Witness** — Suresh Rana, s/o Govind Rana, 29, Male, 11 Relief Road, Sample City

**Seized items** (seized from the accused, 28 May 2026, Relief Road):
1. Four mobile phones (assorted) — qty 4
2. Cash (Indian currency) — Rs. 18,000
3. Iron rod used to break the lock — qty 1

*Expect:* theft-in-dwelling / house-breaking / stolen-property BNS sections.

---

## 2. Assault causing hurt
**Incident:** Voluntarily causing hurt in a public quarrel · **Codes:** BNS (hurt / grievous hurt, criminal force)

**Narrative:**
> On 2 June 2026 at about 8:30 p.m., following an argument over a parking space
> outside a tea stall in Test Nagar, the accused struck the complainant on the
> head and arm with a wooden stick, causing bleeding injuries. The complainant
> was taken to the local hospital for treatment. Bystanders intervened and
> separated the two.

**Parties:**
- **Victim/Complainant** — Anil Verma, s/o Ramesh Verma, 38, Male, 14 Sample Street, Test Nagar, 90000-02222
- **Accused** — Mahesh Solanki, s/o Bharat Solanki, 41, Male, 3 Mock Lane, Test Nagar
- **Witness** — Farida Begum, w/o Salim Khan, 50, Female, 14 Sample Street, Test Nagar

**Seized items** (seized from the accused, 2 June 2026, outside the tea stall):
1. Wooden stick with bloodstains — qty 1

*Expect:* hurt / grievous-hurt / assault BNS sections. Good case to also generate
a **Medical Treatment Letter** (victim-centred).

---

## 3. Online cheating / financial fraud
**Incident:** Cheating by impersonation over the phone/UPI; digital-evidence angle · **Codes:** BNS (cheating, fraud) + BSA (electronic/digital records as evidence)

**Narrative:**
> Between 10 and 12 June 2026, the accused, posing as a bank official over the
> telephone, induced the complainant to share a one-time password and then
> transferred Rs. 1,45,000 from the complainant's account through several UPI
> transactions. The complainant has preserved screenshots of the messages, the
> transaction history, and the caller's number. The fraudulent number and the
> recipient account details are on record.

**Parties:**
- **Victim/Complainant** — Sunita Iyer, w/o Arvind Iyer, 52, Female, 9 Placeholder Road, Sample City, 90000-03333
- **Accused** — Unknown caller (mobile no. 90000-09999), to be identified

**Seized items / evidence** (produced by complainant, 12 June 2026):
1. Mobile phone containing the fraudulent call log and messages — qty 1
2. Printout of bank/UPI transaction statement — qty 1 set

*Expect:* cheating/fraud BNS sections; the digital-record details should pull
**BSA** electronic-evidence sections in the suggestions. Good case to show
suggestions spanning two codes.

---

## 4. Custody and remand procedure question
**Incident:** Post-arrest procedure — production before magistrate, police custody · **Codes:** BNSS (arrest, custody, remand procedure)

**Narrative:**
> The accused was arrested on 1 June 2026 at 7:15 a.m. in connection with the
> above case. The investigating officer seeks to produce the accused before the
> jurisdictional magistrate and requests police custody for interrogation and
> recovery. Question for the system: what is the procedure and time limit for
> producing an arrested person before a magistrate, and the rules governing
> police custody and remand?

**Parties:**
- **Accused** — Imran Shaikh, s/o Yusuf Shaikh, 26, Male, 5 Example Colony, Sample City

**Arrest details** (set Status = ARREST when creating the case):
- Arrest date: 1 June 2026
- Place of arrest: near the bus stand, Sample City

*Expect:* **BNSS** sections on arrest, production before magistrate, detention
limits, and remand to appear at the top. Use this case to generate a **Remand
Request** (pulls confirmed sections + the arrest diary event).

---

## 5. Domestic incident with multiple witnesses
**Incident:** Domestic dispute / cruelty with several family and neighbour witnesses · **Codes:** BNS (cruelty / criminal intimidation) — multi-party & diary demo

**Narrative:**
> On 5 June 2026, the complainant reported that over the preceding weeks she had
> been subjected to repeated harassment and threats at her matrimonial home in
> Test Nagar by her husband and a relative, including demands for money. On the
> day of the complaint, the dispute escalated and several family members and two
> neighbours were present and witnessed the events.

**Parties:**
- **Victim/Complainant** — Pooja Chauhan, w/o Vikram Chauhan, 28, Female, 7 Demo Apartments, Test Nagar, 90000-04444
- **Accused** — Vikram Chauhan, s/o Devendra Chauhan, 33, Male, 7 Demo Apartments, Test Nagar
- **Accused** — Kamla Chauhan, w/o Devendra Chauhan, 58, Female, 7 Demo Apartments, Test Nagar
- **Witness** — Neha Sharma, d/o Om Sharma, 24, Female, 7 Demo Apartments, Test Nagar
- **Witness** — Ramlal Yadav, s/o Shyam Yadav, 60, Male, 6 Demo Apartments, Test Nagar
- **Witness** — Asha Pillai, w/o Joseph Pillai, 45, Female, 8 Demo Apartments, Test Nagar

**Seized items:** none (statement-driven case).

*Expect:* cruelty / intimidation BNS sections. Best case for the **diary
timeline** and **Accused Panchanama** demos — multiple parties and witnesses,
manual diary steps (e.g. "witness interviewed").
