### **Project Battleship — Sentence Normalizer Overhaul (Version 2.0)**

**Purpose:**
This document delegates the "Battleship" action plan and defines the development process for a "bulletproof" Sentence Normalizer. The goal is to produce linguistically perfect, audio-ready sentences to fuel the client's learning system.

---

**High-Level Phases:**

*   **Phase 1: Architect the "Bulletproof" Sentence Normalizer (The Brain)**
    *   1.1 Pre-Processing (Perfect Chunks)
    *   1.2 Prompt Engineering (Perfect Instructions)
    *   1.3 Post-Processing & Validation (The Quality Gate)
*   **Phase 2: System Hardening & Reliability (The Armor)**
    *   2.1 Centralized Error Logging
    *   2.2 User-Facing Error Messages

---

**[UPDATE] New Core Acceptance Criteria for the Entire Project:**

Before any individual task is considered complete, the final output of the entire pipeline must adhere to these "Stan-Ready" criteria:

*   **Audio-Ready:** Every sentence must be grammatically and structurally sound, suitable for direct use in a Text-to-Speech (TTS) engine like `Natural Reader`. This means no fragments, hanging punctuation, or awkward phrasing.
*   **High Semantic Density:** Sentences must be rich in meaningful vocabulary, prioritizing content words over filler.
*   **Batch Integrity:** The system must be able to process a large batch of source files (e.g., 500 PDFs) in a single run without crashing or producing inconsistent results.

---

**Delegation & Task Breakdown:**

**Phase 1.1: Pre-Processing (Agent: NLP Specialist)**
*   **Branch:** `battleship/phase1-preprocessing`
*   **Task:** Refactor the `chunking_service`. Use `spaCy` to segment the raw text from PDFs into clean, individual sentences first. Then, create overlapping "context-aware chunks" of 2-3 sentences to provide richer context for the LLM.
*   **Acceptance:** Unit tests confirm that given a block of raw text, the service outputs clean, structured sentence chunks.

**Phase 1.2: Prompt Engineering (Agent: AI Specialist)**
*   **Branch:** `battleship/phase1-prompt-engineering`
*   **Task:** Design and implement a new, sophisticated "Chain of Thought" prompt for the LLM. The prompt must explicitly instruct the model to identify core ideas, rewrite them as complete sentences, and strictly adhere to all constraints (4-8 words, verb presence, etc.). The output must be a clean JSON array.
*   **[UPDATE] Acceptance:** Unit tests will mock the LLM response. A key test will be to feed the prompt a fragment (e.g., "Dans la rue.") and verify that the LLM, following the prompt's instructions, either completes it into a full sentence or returns an empty array because it cannot meet the criteria.

**Phase 1.3: Post-Processing & Validation (Agent: Backend Developer)**
*   **Branch:** `battleship/phase1-quality-gate`
*   **Task:** Build the `quality_gate` service. This service receives the JSON array from the LLM and iterates through each sentence.
*   **[UPDATE] Acceptance:** This "Quality Gate" is our most critical defense. It must have unit tests for the following checks:
    1.  **Verb Check:** Use `spaCy` POS tagging to confirm the presence of at least one `VERB`.
    2.  **Length Check:** Confirm token count is between 4 and 8.
    3.  **Fragment Check:** Add a heuristic to detect and discard likely fragments (e.g., sentences that don't start with a capital letter or end with proper punctuation).
    *   **Only sentences that pass ALL checks are saved to the database.**

**Phase 2.1: Centralized Error Logging (Agent: DevOps/Backend)**
*   **Branch:** `battleship/phase2-logging`
*   **Task:** Implement a robust, centralized logging system (e.g., Python's `logging` module, potentially integrated with Sentry). Ensure all services, especially the new Normalizer pipeline, log errors with clear context (e.g., which PDF, which chunk failed).
*   **Acceptance:** A test that intentionally causes an LLM API failure is correctly logged with a full stack trace and contextual info.

**Phase 2.2: User-Facing Error Messages (Agent: Frontend/UX)**
*   **Branch:** `battleship/phase2-user-errors`
*   **Task:** Create a mapping of common backend error codes to user-friendly, helpful messages. Update the frontend components to display these messages instead of generic "Error" alerts.
*   **[UPDATE] Acceptance:** A specific test where a user uploads a corrupted PDF should result in the frontend displaying a clear, helpful message like: "This PDF appears to be corrupted or in an unsupported format. Please try another file."

---

**Testing & Verification:**
*   A new end-to-end test script will be created: `test_battleship_pipeline.py`. This script will take a sample PDF (`tests/fixtures/stan_test_novel.pdf`), run it through the entire new Normalization pipeline, and assert that the number of sentences saved to the database is greater than zero and that every saved sentence passes all Quality Gate checks.

---
*End of Updated Document*