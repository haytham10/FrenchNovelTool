# Using the Fast PDF Cost Estimation Endpoint

The `/api/v1/estimate-pdf` endpoint provides a fast, lightweight way to estimate the cost of processing a PDF without performing full text extraction or calling the Gemini API.

## Backend Usage

### Endpoint Details

- **URL**: `POST /api/v1/estimate-pdf`
- **Rate Limit**: 30 requests per minute
- **Authentication**: JWT Bearer token required
- **Content-Type**: `multipart/form-data`

### Request Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `pdf_file` | File | Yes | The PDF file to estimate (max 50MB) |
| `model_preference` | String | No | AI model preference: 'balanced' (default), 'quality', or 'speed' |

### Response

```json
{
  "page_count": 45,
  "file_size": 2457600,
  "image_count": 3,
  "estimated_tokens": 22550,
  "estimated_credits": 23,
  "model": "gemini-2.5-flash",
  "model_preference": "balanced",
  "pricing_rate": 1.0,
  "capped": false,
  "warning": null
}
```

### Example cURL Request

```bash
curl -X POST \
  http://localhost:5000/api/v1/estimate-pdf \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "pdf_file=@document.pdf" \
  -F "model_preference=balanced"
```

## Frontend Usage

### Using the React Query Hook

```typescript
import { useEstimatePdfCost } from '@/lib/queries';

function MyComponent() {
  const estimateMutation = useEstimatePdfCost();

  const handleFileSelect = async (file: File) => {
    try {
      const result = await estimateMutation.mutateAsync({
        file,
        model_preference: 'balanced',
      });
      
      console.log(`Pages: ${result.page_count}`);
      console.log(`Estimated tokens: ${result.estimated_tokens}`);
      console.log(`Estimated credits: ${result.estimated_credits}`);
      
      if (result.warning) {
        console.warn(result.warning);
      }
    } catch (error) {
      console.error('Estimation failed:', error);
    }
  };

  return (
    <div>
      <input
        type="file"
        accept=".pdf"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFileSelect(file);
        }}
      />
      {estimateMutation.isPending && <p>Estimating...</p>}
    </div>
  );
}
```

### Using the API Client Directly

```typescript
import { estimatePdfCost } from '@/lib/api';

async function estimateCost(file: File) {
  const result = await estimatePdfCost({
    file,
    model_preference: 'balanced',
  });
  
  return result;
}
```

## Key Benefits

1. **Fast**: No text extraction, no Gemini API calls - returns in milliseconds
2. **Lightweight**: Only reads PDF metadata (page count, file size, images)
3. **No History**: Does not create processing history entries
4. **Cost Effective**: Does not consume credits or tokens
5. **User-Friendly**: Provides upfront cost estimates before committing to processing

## Estimation Algorithm

The endpoint uses a heuristic-based approach:

- **Base tokens**: `page_count × 500` (average tokens per page)
- **Image tokens**: `image_count × 50` (additional tokens per image)
- **Total**: `base_tokens + image_tokens`
- **Credits**: Calculated based on model pricing (e.g., 1 credit per 1,000 tokens for balanced)

### Constants (configurable in backend/app/constants.py)

- `MAX_PAGES_FOR_ESTIMATE`: 1000 (maximum pages for estimation)
- `PAGES_TO_TOKENS_HEURISTIC`: 500 (average tokens per page)
- `ESTIMATE_IMAGE_WEIGHT`: 50 (tokens per image)

## Error Handling

### Common Errors

1. **422 Unprocessable Entity**: PDF is corrupted or invalid
2. **400 Bad Request**: Invalid file type or missing file
3. **429 Too Many Requests**: Rate limit exceeded
4. **401 Unauthorized**: Missing or invalid authentication token

### Frontend Error Handling

```typescript
const estimateMutation = useEstimatePdfCost();

try {
  const result = await estimateMutation.mutateAsync({ file });
  // Handle success
} catch (error) {
  if (axios.isAxiosError(error)) {
    if (error.response?.status === 422) {
      alert('Invalid or corrupted PDF file');
    } else if (error.response?.status === 429) {
      alert('Too many requests. Please try again later.');
    }
  }
}
```

## When to Use

### Use estimate-pdf when:
- User uploads a new PDF file for the first time
- Showing a cost summary before processing
- Building a UI that displays page count immediately
- Need to validate PDF before committing resources

### Use extract-pdf-text when:
- Need actual text content for preview
- Performing detailed text analysis
- Generating more accurate token counts
- Willing to wait longer for results

## Integration Example

```typescript
// Example: Show cost estimate on file upload
function FileUploadWithEstimate() {
  const [estimate, setEstimate] = useState(null);
  const estimateMutation = useEstimatePdfCost();

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const result = await estimateMutation.mutateAsync({
        file,
        model_preference: 'balanced',
      });
      setEstimate(result);
    } catch (error) {
      console.error('Failed to estimate:', error);
    }
  };

  return (
    <div>
      <input type="file" accept=".pdf" onChange={handleFileChange} />
      
      {estimateMutation.isPending && <CircularProgress />}
      
      {estimate && (
        <Box>
          <Typography>Pages: {estimate.page_count}</Typography>
          <Typography>File Size: {(estimate.file_size / 1024 / 1024).toFixed(2)} MB</Typography>
          <Typography>Estimated Credits: {estimate.estimated_credits}</Typography>
          {estimate.warning && (
            <Alert severity="warning">{estimate.warning}</Alert>
          )}
        </Box>
      )}
    </div>
  );
}
```

## Performance Characteristics

- **Latency**: Typically < 100ms (compared to 5-30+ seconds for full extraction)
- **Memory**: Minimal (only reads PDF metadata, no full file in memory)
- **CPU**: Negligible (no text rendering or tokenization)
- **Network**: No external API calls (unlike full processing with Gemini)

## Limitations

1. **Heuristic-based**: Estimates may vary from actual costs (typically within ±20%)
2. **Page count capping**: PDFs with >1000 pages are capped for estimation purposes
3. **No text analysis**: Cannot detect actual content complexity
4. **Image counting**: May not detect all embedded images accurately

Despite these limitations, the endpoint provides good enough estimates for most use cases while being orders of magnitude faster than full text extraction.
