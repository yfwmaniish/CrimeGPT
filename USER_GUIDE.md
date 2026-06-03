# CrimeGPT — User Guide for Officers

This guide is for police officers using CrimeGPT to handle a case from the first
complaint to arrest and chargesheet. It explains, step by step, what to click and
what each part does. You do not need any technical knowledge to use the system.

Keep one idea in mind throughout: **you enter the facts once, and the system
prepares every document from them.** You never retype the same details.

---

## 1. Signing in

Open the CrimeGPT web address given to you in your browser. You will see a
sign-in screen.

- Type your **username** and **password** and click **Sign in**.
- Your name and role appear at the top of the screen.

There are three kinds of accounts, and each can do different things:

- **Investigating Officer (IO)** — can create cases, get suggested sections,
  confirm sections, generate documents, and add diary entries. This is the main
  working account.
- **Station House Officer (SHO)** — can do everything an IO can do. Use this for
  supervising and generating documents on station cases.
- **Legal Advisor** — can **view** cases, suggestions, and the diary, but cannot
  confirm sections, generate documents, or add diary entries. This is a
  read-and-advise account.

If you try to do something your account is not allowed to do, the system shows a
short message explaining who can do it. Nothing breaks.

**Changing the language:** at the top of the screen there is a small language box.
Choose **English**, **हिन्दी** (Hindi), or **ગુજરાતી** (Gujarati). The screen
changes immediately, and the system remembers your choice the next time you sign
in.

---

## 2. The "My cases" page

After signing in you land on **My cases**. This shows the cases you are handling,
newest first. You only see your own cases.

- **Search:** the box at the top searches your cases by case number, FIR number,
  police station, or words in the narrative. Type a few letters and the list
  updates on its own. Clear the box to see all your cases again.
- **Open a case:** click any row to open it. You return to exactly where you left
  off — suggestions, documents, and diary all as you saved them.
- **Start a new case:** click **+ New case**.

You can return to this page any time by clicking the **CrimeGPT** title at the top.

---

## 3. Creating a case

Click **+ New case** and fill in the details.

**Case details**
- Case number, FIR number, FIR date, and police station are required.
- Choose a **Status**: Complaint, Investigation, Arrest, or Chargesheet Filed.
- Add the **place of incident** and write **what happened** in the narrative box.
  Write this in plain language, as much detail as you have. The system reads this
  narrative later to suggest sections, so a fuller narrative gives better
  suggestions.

**People involved**
- Click **+ Add person** for each person.
- For each person choose a role — **Victim/Complainant**, **Accused**, or
  **Witness** — and fill in the name, father's or husband's name, **age**,
  **gender**, phone, and address. Fill in what you know; you can leave fields
  blank.

**Seized items**
- Click **+ Add item** for each item seized.
- Enter a description and quantity, choose **who it was seized from** (one of the
  people you added), and the date and place of seizure.

**If the status is Arrest**
- When you set the status to **Arrest**, two extra boxes appear: **arrest date**
  and **place of arrest**. Fill them in.
- The system records the arrest in the case diary automatically, and uses these
  details when you generate a Remand Request.

When everything is entered, click **Save case**. You move to the case's working
screen.

---

## 4. Getting suggested legal sections

On the case screen, find the **Applicable BNS sections** panel and click
**Suggest BNS Sections**.

The system reads your narrative and lists the sections that most closely match it,
ordered from closest to least close. The suggestions cover all three new criminal
codes: **BNS** (the offence), **BNSS** (procedure, such as arrest and custody),
and **BSA** (evidence). So an arrest-procedure narrative will surface BNSS
sections, and a narrative about digital records will surface BSA sections,
alongside the BNS offence sections.

Each suggestion shows a **match percentage**. This simply means *how closely the
section matches the words of your narrative — a higher number is closer.* It is a
guide to help you look, not a decision. A high percentage does not mean the
section applies, and a low one does not mean it doesn't.

**You must confirm the sections that actually apply.** Tick the checkbox next to
each section you decide is correct. Confirmed sections turn green. Leave the
others unticked. **Only the sections you confirm are used in documents** — the
system never adds a section to a document on its own.

Take this step seriously. The suggestions are a starting point; the legal judgment
is yours.

---

## 5. Generating documents

In the **Generate documents** panel you will see all seven documents. Each is
prepared from the case details and your confirmed sections.

- **Seizure Receipt** — the record of articles seized, and from whom.
- **Remand Request** — the request to the magistrate for police custody of an
  arrested accused (uses the arrest details and confirmed sections).
- **Court Custody Letter** — the request for judicial custody.
- **Medical Treatment Letter** — the request for medical examination or treatment
  of the victim or accused.
- **Accused Panchanama** — the memorandum of proceedings before panch witnesses.
- **Face Identification Form** — the accused's particulars with a space to affix a
  photograph.
- **Purvani Chargesheet** — the full report that pulls everything together:
  people, confirmed sections, seized items, statements, and the diary summary.

For each document:
- Choose **DOCX** (an editable Word file) or **PDF** (ready to print), then click
  **Generate**. The file downloads, and a **Download** link stays on the row.

**Version numbers.** The first time you generate a document it is **version 1**.
If you change the case and generate it again, you get **version 2**, then 3, and so
on. Earlier versions are always kept and never overwritten, so there is a complete
record of what was produced and when. This protects you: you can always show the
exact document issued at any point.

Only IO and SHO accounts can generate documents.

---

## 6. The Case Diary

Every case has a **Case diary** — a timeline of what happened, in order.

Some entries are added **automatically**: when an arrest is recorded, and each
time a document is generated. You do not have to do anything for these.

You should also add the **investigative steps you take by hand**, so the diary is
a complete record. Under **Add a step**, write what happened — for example
"Witness interviewed", "Evidence collected", "Site visited" — and click **Add**.
It appears in the timeline straight away, with the time and your name.

The diary is add-only: entries are recorded, not edited or deleted. A Legal
Advisor can read the diary but cannot add to it.

---

## 7. Working in Hindi and Gujarati

CrimeGPT works in three languages.

- **The screen:** use the language box at the top to switch between English,
  Hindi, and Gujarati at any time. Your choice is remembered.
- **What you type:** you can enter names, addresses, and narratives in Hindi
  (Devanagari) or Gujarati script. They are saved exactly as you type them and
  shown back exactly the same — nothing is converted or changed.
- **Documents:** the **Seizure Receipt** can be produced in Gujarati and Hindi as
  well as English — the labels and wording change to the chosen language while
  your case details stay as you entered them. The other documents are in English
  for now; the case details inside them are always shown as entered.

---

## 8. A worked example (burglary case)

Follow this end to end. (It uses the first sample in `backend/data/sample_firs.md`.)

1. **Sign in** as your IO account. Choose your language if you wish.
2. On **My cases**, click **+ New case**.
3. **Case details:** Case number `CR-118/2026`, FIR number `0145/2026`, FIR date
   28 May 2026, police station as appropriate. Status **Investigation**. Place:
   the shop on Relief Road. Narrative: *"On the night of 27 May 2026, the accused
   broke open the shutter lock of the shop and stole four mobile phones and cash.
   Two passers-by saw him flee with a bag of stolen goods."*
4. **People involved:** add the complainant (shop owner), the accused, and the two
   witnesses, with their ages and genders.
5. **Seized items:** four mobile phones, cash, and the iron rod used to break the
   lock — all seized from the accused.
6. Click **Save case**.
7. Click **Suggest BNS Sections.** Review the list. Tick the ones that apply to a
   break-in and theft (for example, theft in a dwelling/shop, house-breaking, and
   stolen property). Leave the rest unticked.
8. In **Generate documents**, generate the **Seizure Receipt** as a PDF. It
   downloads, filled with the case details. (Generate it again later and it
   becomes version 2.)
9. Open the **Case diary.** You will see the document generation logged. Add a
   manual step, such as "Recorded statements of both witnesses."
10. When the accused is arrested, edit the case, set the status to **Arrest**,
    enter the arrest date and place, save, then generate the **Remand Request.**

That is the full path from complaint toward arrest, with every document built from
the one case.

---

## 9. What CrimeGPT does not do

Please read this section.

- **The system suggests; you decide.** Suggested sections are only a starting
  point to help you look. Nothing is applied until you confirm it, and no
  unconfirmed section ever goes into a document. The legal decision is always
  yours.
- **The legal text is official, not invented.** The wording of every section
  comes, word for word, from the official published source. The system does not
  write or paraphrase the law.
- **It is not legal advice.** CrimeGPT is a tool to help you organise a case and
  prepare paperwork faster. It does not replace your judgment, your supervisor, or
  the legal advisor.
- **It does not file or send anything on its own.** It prepares documents for you
  to review, print, and use. You remain in control of every step.

If anything on the screen is unclear, the system shows short messages to guide
you, and you can always return to **My cases** by clicking the title at the top.
