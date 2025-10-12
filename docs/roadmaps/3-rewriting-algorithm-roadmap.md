# AI Algorithm Improvement Roadmap

**Last Updated:** October 2, 2025

Focus: Robust JSON parsing, output quality, and reliability improvements.

---

## 📊 Current State

### ✅ Recent Improvements (Oct 2025)
- Enhanced JSON parsing with multi-level fallbacks
- Brace-matching algorithm for extraction
- Regex-based sentence extraction as fallback
- Better error logging for debugging
- PDF metadata collection (size, pages)
- Improved prompt with style preservation rules

### ⚠️ Ongoing Issues
- Still occasional JSON parsing failures in production
- No response validation before parsing
- No caching (duplicate requests cost $$$)
- Entire document processed in one call (not scalable)
- No quality metrics or feedback loop

---

## 🔴 P0 - Critical (Weeks 1-2)

### Week 1: Response Validation & Recovery
**Prevent parsing errors before they happen**

- [ ] **Add pre-parse validation**
  ```python
  def validate_response_structure(text: str) -> bool:
      \"\"\"Check if response looks like valid JSON\"\"\"
      text = text.strip()
      if not text.startswith('{'):
          return False
      if not text.endswith('}'):
          return False
      if text.count('{') != text.count('}'):
          return False
      return True
  ```

- [ ] **Implement streaming response parsing**
  - Parse JSON as it arrives
  - Detect issues earlier
  - Allow partial recovery

- [ ] **Add response checksum/validation**
  ```python
  def validate_gemini_response(data: dict) -> tuple[bool, str]:
      \"\"\"Validate structure and content\"\"\"
      if not isinstance(data, dict):
          return False, \"Not a dictionary\"
      if 'sentences' not in data:
          return False, \"Missing 'sentences' key\"
      if not isinstance(data['sentences'], list):
          return False, \"'sentences' is not a list\"
      if len(data['sentences']) == 0:
          return False, \"Empty sentences list\"
      return True, \"Valid\"
  ```

### Week 2: Caching & Deduplication
**Save costs and improve response times**

- [ ] **Implement response caching**
  ```python
  import hashlib
  
  def get_cache_key(pdf_bytes: bytes, prompt: str) -> str:
      \"\"\"Create deterministic cache key\"\"\"
      content_hash = hashlib.sha256(pdf_bytes).hexdigest()
      prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
      return f\"gemini:{content_hash}:{prompt_hash}\"
  
  # Cache in Redis with 24h TTL
  cache_key = get_cache_key(pdf_bytes, prompt)
  cached = redis.get(cache_key)
  if cached:
      return json.loads(cached)
  
  result = call_gemini_api(...)
  redis.setex(cache_key, 86400, json.dumps(result))
  ```

- [ ] **Add request deduplication**
  - Detect concurrent identical requests
  - Share single API call result
  - Reduce API quota usage

---

## 🟠 P1 - High Priority (Weeks 3-6)

### Week 3-4: Prompt Engineering V2
**Improve output quality and consistency**

- [ ] **Add few-shot examples to prompt**
  ```python
  EXAMPLES = \"\"\"
  Example 1:
  Input: \"Elle marchait lentement dans la rue et elle pensait à son avenir.\"
  Output: {\"sentences\": [\"Elle marchait lentement dans la rue.\", \"Elle pensait à son avenir.\"]}
  
  Example 2:
  Input: \"C'était une belle journée.\"
  Output: {\"sentences\": [\"C'était une belle journée.\"]}
  \"\"\"
  ```

- [ ] **Add output format validation in prompt**
  ```
  CRITICAL: Your response MUST be valid JSON.
  - Use double quotes for strings
  - Escape special characters (\\n, \\", \\\\)
  - Do not include any text before or after the JSON
  - Validate JSON before responding
  ```

- [ ] **Test different models**
  - Compare gemini-1.5-flash vs gemini-1.5-pro
  - Test with temperature variations
  - Measure quality vs cost tradeoff

### Week 5-6: Quality Monitoring
**Measure and improve output quality**

- [ ] **Add quality metrics**
  ```python
  class QualityMetrics:
      def __init__(self, original: str, processed: List[str]):
          self.total_sentences = len(processed)
          self.avg_length = sum(len(s.split()) for s in processed) / len(processed)
          self.max_length = max(len(s.split()) for s in processed)
          self.preserved_words = self.calculate_preservation(original, processed)
      
      def calculate_preservation(self, original: str, processed: List[str]) -> float:
          \"\"\"Percentage of original words preserved\"\"\"
          original_words = set(original.lower().split())
          processed_words = set(' '.join(processed).lower().split())
          return len(original_words & processed_words) / len(original_words)
  ```

- [ ] **Log quality metrics per request**
  - Track sentence length distribution
  - Monitor parsing success rate
  - Detect quality regressions
  - Create dashboard for monitoring

- [ ] **Implement user feedback loop**
  - "Was this helpful?" button
  - Allow reporting bad outputs
  - Track user satisfaction
  - Use feedback to improve prompts

---

## 🟡 P2 - Medium Priority (Weeks 7-10)

### Advanced Processing

- [ ] **Chunked processing for large PDFs**
  - Split document into sections (chapters, pages)
  - Process each chunk separately
  - Reassemble with context preservation
  - Benefits: Better error recovery, progress tracking

- [ ] **Type-specific prompts**
  ```python
  NARRATIVE_PROMPT = \"...instructions for narrative text...\"
  DIALOGUE_PROMPT = \"...special handling for dialogue...\"
  DESCRIPTION_PROMPT = \"...preserve descriptive language...\"
  ```

- [ ] **Pre-processing step**
  - Analyze document structure first
  - Identify dialogue vs narrative
  - Detect chapter breaks
  - Flag special formatting (poetry, lists)

### Model Optimization

- [ ] **A/B testing framework**
  - Test different prompts
  - Compare model versions
  - Measure success rates
  - Automatic prompt optimization

- [ ] **Fine-tuning exploration**
  - Collect high-quality examples
  - Consider fine-tuning custom model
  - Balance cost vs quality improvement

---

## 🟢 P3 - Low Priority (Future)

### Advanced Features

- [ ] **Multi-language support**
  - Adapt prompts for English, Spanish, etc.
  - Language detection
  - Language-specific rules

- [ ] **Custom rewriting rules**
  - User-defined splitting patterns
  - Preserve specific phrases
  - Custom style guidelines
  - Template-based processing

- [ ] **AI model selection**
  - Allow users to choose model
  - Different models for different document types
  - Cost vs quality tradeoff UI

---

## 📊 Success Metrics

### Reliability
- ✅ 99% successful JSON parsing rate
- ✅ < 1% API timeout rate
- ✅ Zero data loss incidents

### Quality
- ✅ 95%+ word preservation rate
- ✅ 90%+ user satisfaction
- ✅ Average sentence length within target ±2 words

### Performance
- ✅ < 30s processing time for 20-page PDF
- ✅ 50% cache hit rate
- ✅ 30% reduction in API costs (via caching)
