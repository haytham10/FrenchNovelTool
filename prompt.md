**Objective:**
Your sole focus is to architect a new, superior "Sentence Normalization Pipeline" by improving my existing services. Do **not** discuss the `Coverage Tool`; assume it is perfect. Your plan must address the bottleneck in our data preparation phase.

**Project Context & Files:**
You have full context on my "French Novel Tool" project for my client, Stan. The files relevant to this specific task are:
*   `gemini_service.py` (handles the LLM rewriting)
*   `pdf_service.py` (handles text extraction)
*   `chunking_service.py` (prepares text for the LLM)
*   `sample/test.pdf` (a representative sample of the input novels)

**The Ultimate Goal:**
To generate the highest possible quality sentences that will allow the `Coverage Tool` to achieve its objective: 100% vocabulary coverage with the smallest possible learning set.

**Definition of a "Perfect" Output Sentence:**
1.  **Length:** 4-8 words.
2.  **Completeness:** Grammatically correct, meaningful on its own, and **must contain a verb.**
3.  **Fidelity:** Preserves the maximum amount of the original novel's meaningful vocabulary.

**Your Task: Create a Strategic Plan**
Analyze the provided services (`gemini_service`, `pdf_service`, `chunking_service`) and the `test.pdf` sample. Based on this analysis, create a detailed, actionable plan to refactor and improve the entire pipeline from PDF to normalized sentence.

Your plan must address these three stages:

1.  **Preprocessing (The Input):** How can we improve `chunking_service.py`? Analyze `test.pdf` and propose a better method than simple chunking. Should we use `spaCy` to pre-segment the text into sentences *before* sending it to the LLM?
2.  **AI Strategy (The "Brain"):** Design a new, more intelligent prompt for `gemini_service.py`. It must be engineered to produce sentences that meet all the "Definition of Success" criteria.
3.  **Post-processing (The "Quality Gate"):** Design a new validation service. After receiving output from Gemini, this service must automatically verify each sentence for length and the presence of a verb (using `spaCy` POS tagging) and discard any that fail.

Deliver a clear, technical blueprint you can use to build a world-class sentence normalization engine.