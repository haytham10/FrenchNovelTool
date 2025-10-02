# Rewriting Algorithm Improvement Roadmap

This document outlines a phased approach to enhance the sentence rewriting algorithm used in the French Novel Tool. The goal is to move from a simple, length-based mechanical process to a more sophisticated, context-aware, and stylistically appropriate transformation.

## Current State Analysis

The current algorithm uses a single prompt to the Gemini model with the following core logic:
- **Role:** Assistant for processing French novels.
- **Task:** List sentences consecutively.
- **Rule:** If a sentence exceeds a specific word count, rewrite it into shorter sentences.
- **Constraints:** Preserve original meaning and words.
- **Output:** A JSON object with a `sentences` array.

This approach is a good starting point but has several weaknesses, including ambiguous rewriting instructions, lack of context preservation, and no handling of literary style or edge cases like dialogue.

---

## Phase 1: Foundational Prompt Engineering (Short-Term)

**Objective:** Immediately improve the quality and consistency of the rewriting logic with more specific instructions.

- [ ] **Define Specific Rewriting Rules:**
    -   **Action:** Modify the prompt to guide the AI on *how* to split sentences.
    -   **Suggestion:** Instruct the model to "Split long sentences at natural grammatical breaks, such as conjunctions (e.g., 'et', 'mais', 'donc'), subordinate clauses, or where a logical shift in thought occurs."

- [ ] **Introduce Context-Awareness:**
    -   **Action:** Add a constraint that forces the model to consider the surrounding text.
    -   **Suggestion:** Add: "Ensure the rewritten sentences maintain the logical flow and connection to the preceding text. The output must read as a continuous, coherent narrative."

- [ ] **Add Dialogue Handling:**
    -   **Action:** Provide a specific rule for handling quoted text.
    -   **Suggestion:** Add: "If a sentence is enclosed in quotation marks, treat it as dialogue. Do not split it unless absolutely necessary. If a split is unavoidable, do so in a way that maintains the natural cadence of speech."

- [ ] **Incorporate Style and Tone Preservation:**
    -   **Action:** Remind the model to act as a literary assistant, not just a text processor.
    -   **Suggestion:** Add: "Maintain the literary tone and style of the original text. Avoid using overly simplistic language or modern idioms that would feel out of place."

- [ ] **Strengthen JSON Output Reliability:**
    -   **Action:** Improve the prompt to reduce the chance of invalid JSON.
    -   **Suggestion:** Add an example to the prompt: `For example: {"sentences": ["Voici la première phrase.", "Et voici la deuxième."]}`.

---

## Phase 2: Advanced Logic & Multi-Step Processing (Mid-Term)

**Objective:** Implement a more robust, multi-step pipeline that separates text identification from the rewriting process for better control and accuracy.

- [ ] **Develop a "Pre-processing" Step:**
    -   **Action:** Create a first AI call that identifies and categorizes text, rather than rewriting it immediately.
    -   **Implementation:** The first prompt would ask the model to return a structured JSON object that tags each sentence with its type (e.g., `narrative`, `dialogue`, `title`) and a flag indicating if it needs rewriting (e.g., `is_long: true`).

- [ ] **Implement a "Conditional Rewriting" Step:**
    -   **Action:** Based on the output from the pre-processing step, loop through the sentences. Only send sentences flagged as `is_long: true` to a second, specialized AI prompt for rewriting.
    -   **Implementation:** This second prompt can be highly focused, as it only ever deals with long sentences. It can be further specialized based on the sentence `type` (e.g., a different prompt for rewriting long `narrative` vs. long `dialogue`).

- [ ] **Introduce "Chain-of-Thought" Prompting:**
    -   **Action:** For the rewriting prompt, instruct the model to "think step-by-step" before providing the final answer.
    -   **Suggestion:** Add: "First, identify the natural clauses in the sentence. Second, determine the best split points. Third, rewrite the sentence into shorter parts. Finally, present the rewritten sentences in the JSON output." This forces a more logical process.

---

## Phase 3: User-Driven Customization & Sophistication (Long-Term)

**Objective:** Empower users with control over the rewriting process and introduce advanced linguistic analysis.

- [ ] **Expose Algorithm Controls to the User:**
    -   **Action:** Allow users to select a "Rewriting Style" in their settings.
    -   **Implementation:** Create different prompt variations for different styles (e.g., "Literal: Splits sentences with minimal changes," "Balanced: A mix of preservation and flow," "Interpretive: Allows for more significant restructuring for readability"). The backend would select the prompt based on the user's setting.

- [ ] **Integrate Named Entity Recognition (NER):**
    -   **Action:** Add a step to identify and preserve important entities like character names, locations, and specific terms.
    -   **Implementation:** Before rewriting, use a prompt or a library to extract named entities. Add a constraint to the rewriting prompt: "Ensure the following key terms are preserved and not altered: [list of entities]."

- [ ] **Implement a Caching Layer:**
    -   **Action:** Cache results for previously processed sentences or paragraphs.
    -   **Implementation:** If the same text is processed again (e.g., by the same or a different user), the system can return the cached, high-quality result, saving on API costs and processing time.

- [ ] **Explore Fine-Tuning a Model:**
    -   **Action:** If usage is high and quality needs to be perfected, consider fine-tuning a smaller, specialized model.
    -   **Implementation:** Collect high-quality examples of "long sentence -> rewritten sentences" pairs generated through the improved prompts. Use this dataset to fine-tune a model specifically for this task, which could yield superior results and lower costs over time.
