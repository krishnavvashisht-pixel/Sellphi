# What's In This Project (Plain-Language Guide)

This document explains what every folder and file does, in plain English — no
coding background needed. It gets updated every time something new is built.

Think of the whole app like an office building. Each folder below is a
department in that building.

---

## The building's departments (top-level folders inside `app/`)

- **`main.py`** — The building's front door. This is the file that "starts"
  the whole app, and also where the two webpages (below) get connected to
  it.

- **`core/`** — Building management: security rules, settings, and the
  system that catches errors and turns them into sensible messages instead
  of crashing.
  - `config.py` — The settings panel. Where do we log in to reach the
    database? What secret code do we use to sign someone in? All of that
    lives here, and it's read from a `.env` file (a private settings file
    that's never shared or uploaded anywhere).
  - `security.py` — The lock-and-key department. Turns a password into
    something safe to store, checks passwords at login, and creates the
    two "wristbands" (explained below under Auth) that prove someone is
    logged in.
  - `exceptions.py` — The complaints desk. When something goes wrong (wrong
    password, missing data), this decides what error message and error
    code to send back.
  - `logging.py` / `middleware.py` — The building's security cameras and
    intercom — record what's happening and pass messages between
    departments.

- **`db/`** — The filing room. Manages the connection to Postgres (our
  database — the permanent filing cabinet where everything real gets
  stored) and to Redis (a fast, short-term notice board used later for
  background jobs).

- **`models/`** — The blueprints for what a "filing cabinet drawer" looks
  like. Each file describes one type of thing we keep records of:
  - `user.py` — describes a person who can log in. Now includes whether
    they're an admin.
  - `mission.py` — describes a **mission**: one business goal, like "find
    Series A SaaS companies that just raised money and need X." Every
    later stage (finding companies, researching them, writing outreach)
    runs against one of these. Nothing outside the app can create one yet
    — no webpage or button for it — it's set up directly as a record for
    now, while the "finding and contacting companies" part of the system
    gets built first.
  - `company.py` — describes a company Sellphi knows about. Starts out
    almost empty (often just a name pulled from a headline) and gets
    filled in properly later.
  - `buying_signal.py` — describes one detected signal: what happened,
    to which company, how strong a reason it is to reach out, and why.
  - `event.py` — describes one entry in the permanent history log (see
    "Events" below).
  - `workspace.py`, `product.py` — earlier building blocks, already
    working, not part of what we're actively changing right now.

- **`schemas/`** — The forms people fill out. When you send data to the
  app (like "sign me up with this email and password"), a schema checks
  the form was filled in correctly before anything happens.

- **`repositories/`** — The filing clerks. The only part of the app allowed
  to directly read from or write to the filing cabinets (the database
  tables). Everyone else asks a clerk instead of digging through the
  cabinet themselves — keeps things consistent and easy to check.

- **`services/`** — The department managers. They make the actual
  decisions ("is this password correct?", "does this email already have an
  account?", "is this the last admin — can't remove that one") and tell the
  filing clerks what to do. This is where the real logic lives.

- **`api/`** — The reception desk and phone lines. Defines every web
  address (like `/auth/token`) someone can contact from outside, and
  which department manager handles that request.

- **`web/static/`** — The two actual webpages a person opens in a browser
  (see "The webpages" below) — plain web pages, no separate app to
  install.

- **`events/`** — The building's permanent logbook system. `store.py`
  contains the one function every department uses to write an entry:
  "on this date, this thing happened to this record." This means we can
  always look back and answer "why did the system do that?"

- **`agents/`, `memory/`, `workers/`** — Reserved space for future
  departments (the AI "brain" calls, longer-term memory, and background
  workers). They currently just hold placeholder blueprints — nothing
  real lives there yet.

- **`alembic/`** — The construction crew's instructions. Every time we add
  or change a filing cabinet (a database table), we write down the exact
  steps here so the real database can be updated to match, in order,
  without losing anything already stored.

- **`tests/`** — The building inspectors. Automated checks that run
  without needing a real database — they use pretend, disposable data to
  confirm each department behaves correctly. Every piece of real logic
  gets an inspector; if an inspector ever fails, something is broken.

---

## The webpages

Two actual pages you open in a normal browser — no terminal needed for
either:

### 1. Login / Sign up — `http://localhost:8000/login`
Open to anyone. Has two tabs:
- **Sign up** — type an email and password, get an account immediately.
  **The very first person to ever sign up automatically becomes an
  admin** — there's no one else yet to hand that out, so it defaults to
  whoever gets there first. Everyone who signs up after that is a regular
  (non-admin) user.
- **Log in** — for anyone who already has an account.

Either way, once it works you're taken straight to the admin page.

### 2. Admin (user management) — `http://localhost:8000/admin`
Only admins can actually see anything useful here. If a regular
(non-admin) user opens this page, they see "Access denied" — and this
isn't just hidden by the webpage, the actual data is refused by the app
itself even if someone tried to sneak around the webpage.

If you *are* an admin, you see a table of every person who's signed up,
with buttons to:
- **Activate / Deactivate** an account (a deactivated person can't log in
  anymore)
- **Make admin / Remove admin**

One safety rule is built in: **you can never remove the last remaining
admin** — the app refuses that change — so nobody can ever accidentally
lock everyone out of the admin page for good.

---

## Concepts explained

### The two "wristbands" (access token & refresh token)
When you log in or sign up, the app hands you two things:
- An **access token** — like a wristband that gets you into the venue for
  a short while (30 minutes). Every request you make shows this
  wristband.
- A **refresh token** — like a claim ticket that lasts much longer (2
  weeks) and can be traded in for a brand new access wristband once the
  old one expires, without having to type your password again.

The webpages handle this automatically in the background — if your
wristband expires while you're using the admin page, it quietly trades
in the claim ticket for a new one without kicking you out.

They're deliberately not interchangeable — a refresh ticket can't be used
as an access wristband and vice versa. That's a security fix from the
original code, where the two were dangerously not separated.

### Events (the permanent logbook)
Every time something meaningful happens in the app (a signal is detected,
a message is sent, a mission is created), one line gets written to a
permanent logbook and never erased. That's how we can always answer "what
happened, and when, for this exact company?" later.

---

## The AI ("the Brain") behind all of this

Any time the system needs to actually think — "does this article suggest
we should reach out?", "what should we say to this person?" — it asks
Gemini (Google's AI) one specific question through one shared piece of
code (`app/llm_client.py`), and always gets back an answer in a fixed,
predictable shape rather than free-flowing text. Every future AI-driven
stage (signal detection, research, strategy, writing the actual message)
goes through this same single doorway, which is what makes it possible to
swap in a different AI later by changing one file instead of hunting
through the whole codebase.

## What a "mission" is

Everything the system does — finding companies, researching them, writing
a message — happens *for* a mission. A mission is just: "who are we
looking for?" (the ICP — Ideal Customer Profile: industry, company size,
location, the job titles of people to contact, and the real-world signs
that now's a good time to reach out) plus "what are we selling them?"
(the product info).

There are now two ways a mission gets its ICP filled in, and both produce
the exact same kind of record — nothing downstream can tell which one was
used:

1. **By hand** — someone writes the ICP directly (used for testing the
   rest of the pipeline while it's being built).
2. **By AI** — you describe the goal in one plain sentence, like *"Find
   Series A SaaS companies that just raised funding and need a data
   pipeline,"* and Gemini (the AI) reads that and fills in the ICP fields
   itself: which industries, which countries, roughly what size company,
   which job titles to target, what real-world signs to watch for, and
   anything to explicitly rule out.

There's still no webpage for either of these yet — both are set up
directly for now, while the finding-and-researching machinery gets built.

**One honest limitation worth knowing:** I can't actually call the real
Gemini AI from where I do this work — there's no path out to Google's
servers set up for me here. So the automated checks for the AI path use
realistic pretend answers I wrote by hand, which proves the *code* is
wired up correctly (it asks the right question, checks the answer has
every field it needs, saves it properly) — but it does **not** prove
Gemini's real answers will actually be good ones. To see the real thing,
run `scripts/try_mission_parser.py` yourself once you've added a real
Gemini key to `.env` — type in an objective, and it'll print exactly what
the live AI comes back with, so you can judge for yourself whether it's
sensible.

---

## How the system finds companies worth contacting (Signal Detection)

This is the first piece of the "go find business" machinery. Here's how
it actually works, step by step:

1. **Watching the news.** The system searches Google News for headlines
   relevant to your mission (funding announcements, hiring news, and so
   on). This happens in the background — nothing waits around for it.
2. **The AI reads each headline and decides if it matters.** For every
   news item, Gemini is asked: *is this genuinely a reason to reach out to
   this company, given who we're looking for?* It answers with a score
   from 0 to 1, and — critically — it has to explain itself in plain
   language: what exactly happened (the **evidence**), and why that
   matters for what we're selling (the **sales implication**). It also
   says what kind of event this is (funding, hiring, a leadership change,
   etc.) and how urgent it is.
3. **Only genuinely good signals get kept.** Anything scoring 0.5 or
   higher gets saved as a real signal, attached to the company it's
   about. Anything below that is thrown away — but the fact that it was
   *considered and rejected* still gets a line in the permanent logbook,
   so nothing disappears without a trace.
4. **A bare-bones company record gets created the first time a company is
   mentioned.** At this stage the system usually only knows a company's
   name from a headline — nothing else yet. So it creates a minimal
   placeholder record (just the name) the first time it sees that
   company, and reuses that same record for every future signal about
   them. The next stage (not built yet) will fill in the rest — industry,
   size, contact people — by looking the company up properly.

**One honest limitation, same as before:** I can't reach either Google
News or the real Gemini AI from where I do this work. The automated
checks use realistic, hand-written pretend news headlines and pretend AI
answers to prove the code itself is correct — they can't prove the real
AI's judgment on real, live headlines will be good. To see the real
thing, run:

```bash
python scripts/try_signal_detection.py "series A funding SaaS"
```

with a real Gemini key in `.env` and normal internet access, and it will
print exactly what the live system finds and decides — real headlines,
real AI reasoning, right in your terminal.

---

## Status as of this update

**Working and tested:** the building's front desk starts up; workspace and
product records (from earlier work); public sign-up and login, with the
first person to sign up becoming an admin; an admin-only page for
activating/deactivating people and granting/removing admin, with a
safeguard against removing the last admin; the permanent logbook; two
real webpages for all of the above; the "mission" record, settable both
by hand and by describing the goal in plain English; the single doorway
(`app/llm_client.py`) every AI step goes through; signal detection
end-to-end (watch the news, score each item with AI, keep the good ones
with a real evidence/sales-implication explanation, create a bare-bones
company record the first time a company shows up).

**Not built yet:** prospect discovery (filling in the rest of a
company's details and finding real contact people), research,
decision-maker discovery, strategy, communication style profiles,
outreach, reply classification, and meeting booking — these come next,
one at a time.
