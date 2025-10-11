Project Battleship — Sentence Normalizer Overhaul
===============================================

Purpose
-------
This document delegates the "Battleship" action plan across parallel agents and defines branching/PR conventions for the Project Overhaul that creates a "bulletproof" Sentence Normalizer.

High-level phases
------------------
- Phase 1: Architect the "Bulletproof" Sentence Normalizer (the Brain)
  - 1.1 Pre-Processing (Perfect Chunks)
  - 1.2 Prompt Engineering (Perfect Instructions)
  - 1.3 Post-Processing & Validation (Quality Gate)
- Phase 2: System Hardening & Reliability (the Armor)
  - 2.1 Centralized Error Logging
  - 2.2 User-Facing Error Messages

Branching strategy
------------------
- Base branch: `battleship` (created from `master`) — parent branch for the overhaul
- Feature/task branches (forked from `battleship`):
  - `battleship/phase1-preprocessing`
  - `battleship/phase1-prompt-engineering`
  - `battleship/phase1-quality-gate`
  - `battleship/phase2-logging`
  - `battleship/phase2-user-errors`

Delegation & Parallel Agents
----------------------------
Each feature branch is intended for a dedicated agent or small team. The agent should:

1. Create the feature branch locally from `battleship`.
2. Implement changes and tests.
3. Push branch and open a PR targeting `battleship`.

Acceptance criteria (for each task)
----------------------------------
- Code compiles / lints and unit tests pass for modified areas.
- New behavior covered by unit tests (happy path + 1-2 edge cases).
- Clear, concise commit history and PR description referencing this doc.

PR naming and templates
-----------------------
- PR title format: [battleship][phase#][short-task] e.g. "[battleship][1.1] spaCy chunker: context-aware chunks"
- PR description must contain:
  - Short summary
  - Files changed (major components)
  - How to test locally
  - Any migration / config changes

Quality gates
-------------
- Run backend unit tests with `pytest`.
- Lint: `black .` (python) and `npm run lint` for frontend changes.

Initial tasks for agents
------------------------
- Phase 1.1 agent: Implement spaCy sentencizer, create context-aware chunks (2-3 sentences per chunk). Add tests and fixtures.
- Phase 1.2 agent: Implement prompt templates, LLM integration hooks, and unit tests mocking LLM responses.
- Phase 1.3 agent: Implement `quality_gate` service in `backend/app/services/quality_gate.py`. Validate verb presence and 4-8 token length using spaCy POS/tokenization. Add unit tests.
- Phase 2.1 agent: Implement structured logging and integrate with Sentry (optional). Ensure all services use the logger.
- Phase 2.2 agent: Add mapping of internal errors to friendly messages and update frontend components to display them.

Testing & verification
----------------------
- Use `pytest` for backend tests and the existing frontend test harness for UI checks.
- Provide examples (sample PDF, sample chunk inputs) in `tests/fixtures` where relevant.

Branch workflow example
-----------------------
1. Create `battleship` from `master`.
2. Checkout `battleship/phase1-preprocessing` from `battleship`.
3. Implement changes and tests.
4. Push `battleship/phase1-preprocessing` to origin.
5. Open PR into `battleship` following naming conventions.

Notes
-----
- Keep changes small and test-focused. Aim for iterative merges into `battleship`.
- If a task grows beyond scope, create sub-branches under the feature branch.

Contact
-------
Primary maintainer: repo owner. For urgent merge coordination, comment on the parent `battleship` branch's PR thread.

-- End of document
