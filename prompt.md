Okay, let's solve our main bottleneck: the sentence normalization pipeline. The `Coverage Tool` is perfect, but it needs better input to help us achieve our ultimate goal of 100% vocabulary coverage with the smallest possible learning set.

**Your task:** Analyze my existing services (`gemini`, `job`, `pdf`, `chunking`) and design a comprehensive plan to improve them.

**The "Definition of Success" for each output sentence remains the same:**
*   4-8 words long.
*   Grammatically complete, meaningful on its own, and **must contain a verb.**
*   Preserves the maximum amount of original vocabulary and meaning.

Your plan should be a holistic blueprint. You have full context on the project. Think hard about every stage:

1.  **Preprocessing:** How can we improve the `chunking_service` *before* calling the AI? Should we be using `spaCy` to send cleaner, more structured text to the LLM?
2.  **AI Strategy:** What is the most effective way to use a model like Gemini for this specific rewriting task? Design a new, more intelligent prompt.
3.  **Post-processing & Validation:** How do we build a reliable quality-gate to automatically verify the AI's output (e.g., check for a verb, check length) and discard any failures?

I'm looking for a robust, end-to-end plan that I can use to build a world-class sentence normalization engine.

ps: you can find a sample novel pdf in `/sample/test.pdf`