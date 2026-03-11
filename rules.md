# 🔒 PARALLEL DEVELOPMENT RULEBOOK

**Project:** Automated Auditorium Lighting  
**Status:** ARCHITECTURE LOCKED

---

## 0️⃣ THE PRIME DIRECTIVE (READ FIRST)

> **No one "fixes" another phase.
> If something looks wrong, you report it — you do NOT change it.**

---

## 1️⃣ PHASE OWNERSHIP (NON-NEGOTIABLE)

Each person owns **only** their assigned phases.

| Person   | Owned Phases           |
| -------- | ---------------------- |
| You      | Phase 0, Phase 4       |
| Friend A | Phase 5                |
| Friend B | Phase 7                |
| Person 2 | Phase 3                |
| Person 3 | Support / Phase 8 only |

### RULE

* You may **edit only your owned phases**
* You may **read** other phases
* You may **NOT commit changes** outside your ownership

---

## 2️⃣ CONTRACT LOCK (ABSOLUTE)

### `/contracts/`

* Read-only for everyone **except you**
* After lock:

  * No new fields
  * No renames
  * No deletions
* Any request to change contracts:

  * Must be discussed
  * Must be versioned
  * Must be approved by you

---

## 3️⃣ NO CROSS-PHASE LOGIC (ZERO TOLERANCE)

### Forbidden examples:

* Phase 5 inferring emotion ❌
* Phase 7 calling LLM ❌
* Phase 3 deciding lighting ❌
* Phase 4 generating DMX ❌

### RULE

> **Each phase answers exactly one question.**

---

## 4️⃣ DMX / HARDWARE QUARANTINE

* DMX, OSC, MIDI code exists **ONLY** in `phase_8/`
* No exceptions
* No stubs elsewhere
* No imports of hardware code outside Phase 8

---

## 5️⃣ RAG DISCIPLINE (PHASE 3 ONLY)

* Two RAGs stay separate:

  * Auditorium
  * Lighting semantics
* No RAG rebuilding during parallel work
* RAG indexes are **read-only**
* If knowledge needs update:

  * Open an issue
  * Do NOT patch manually

---

## 6️⃣ FILE MOVEMENT RULE

* You may move files **only within your phase**
* Moving a file across phases requires:

  * Owner approval
  * Written confirmation
* Never "temporarily" move files

---

## 7️⃣ MERGE RULES (CRITICAL)

### Branch discipline:

* One branch per phase
* No direct commits to `main`

### Merge order:

1. Phase 0 (contracts)
2. Phase 3 (RAG)
3. Phase 4 (decision engine)
4. Phase 5 (visualization)
5. Phase 7 (evaluation)
6. Phase 8 (hardware)

---

## 8️⃣ DUPLICATION RULE (ZERO TOLERANCE)

* No duplicate schemas
* No duplicate adapters
* No duplicate decision engines
* If duplication occurs:

  * New copy is deleted
  * Original owner decides

---

## 9️⃣ CHANGE REPORTING RULE

Any change must answer **one sentence**:

> "Which phase did this change affect?"

If the answer is more than one phase → **change is invalid**.

---

## 🔟 DEMO SAFETY RULE

While parallel work is ongoing:

* Phase 4 output format is frozen
* Phase 5 consumes intent exactly as-is
* Phase 7 observes only

No last-minute "fixes".

---

## 1️⃣1️⃣ COMMUNICATION PROTOCOL

* Use issues or messages to report:

  * Contract mismatches
  * Missing fields
  * Unexpected behavior
* Do NOT hotfix other phases

---

## 1️⃣2️⃣ VIOLATION CONSEQUENCE (AGREED RULE)

If a rule is violated:

1. Change is reverted
2. Owner explains intent
3. Architecture takes priority over speed

No blame, but **no exceptions**.

---

## 1️⃣3️⃣ FINAL CHECK BEFORE COMMIT

Before committing, ask:

* Did I touch only my phase?
* Did I add logic to a forbidden phase?
* Did I duplicate any schema?
* Did I change contracts unintentionally?

If any answer is "maybe" → do NOT commit.

---

## 1️⃣4️⃣ IMPORT DISCIPLINE

* Each phase may only import from:
  * `contracts/` (schemas and interfaces)
  * `utils/` (shared utilities)
  * Its own phase directory
* Cross-phase imports are **FORBIDDEN**
* If you need data from another phase, it must flow through contracts

---

## 1️⃣5️⃣ TESTING ISOLATION

* Each phase has its own test directory
* Tests must not depend on other phases being functional
* Mock external phase dependencies using contract schemas
* Integration tests are owned by Phase 0 (architecture owner)

---

## 1️⃣6️⃣ ENVIRONMENT VARIABLES

* Phase-specific env vars must be prefixed with phase number (e.g., `PHASE_4_LLM_MODEL`)
* Shared env vars go in `.env.shared`
* Do NOT modify another phase's environment configuration

---

## 1️⃣7️⃣ CONFLICT RESOLUTION PROTOCOL

When conflicts arise:

1. **Stop** — Do not force-push or override
2. **Document** — Write down what happened
3. **Notify** — Contact the phase owner
4. **Wait** — Let the owner resolve their own phase
5. **Merge** — Only after explicit approval

---

## 🧭 ONE-LINE MEMORY RULE (PIN THIS)

> **Architecture first.
> Speed second.
> Demo third.**

---

## 🟢 WHY THIS WILL WORK

* Clear ownership removes conflict
* Locked contracts prevent drift
* Phase isolation ensures safety
* Demo remains stable
* Paper remains defensible

You've now reached the point where **real systems succeed or fail**.
This rulebook is what keeps it from failing.

---

## 📋 QUICK REFERENCE CARD

| Rule | Summary |
|------|---------|
| Prime Directive | Report, don't fix other phases |
| Ownership | Edit only your phases |
| Contracts | Read-only after lock |
| Cross-Phase | Zero tolerance |
| Hardware | Phase 8 only |
| RAG | Phase 3 only, read-only indexes |
| File Movement | Within phase only |
| Merging | Sequential, by phase order |
| Duplication | Delete new, keep original |
| Demo | Frozen formats during parallel work |

---

*Last updated: 2026-02-04*
