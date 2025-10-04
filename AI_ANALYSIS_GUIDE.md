# AI Analysis Feature - FRA Recommendations & Development Insights

## Overview

The DSS Report API now includes **AI-powered analysis** using Google Vertex AI (Gemini 1.5 Flash) to generate:
- **FRA (Forest Rights Act) eligibility recommendations**
- **Key findings** from collected data
- **Development priorities** based on indicators
- **Risk factors** and **opportunities**
- **Executive summary** with confidence assessment

## Feature Status

✅ **Implemented**: AI analysis infrastructure  
⏸️ **Requires**: Vertex AI API configuration (GCP project + credentials)

## Data Model

### AIAnalysis Structure

```json
{
  "ai_analysis": {
    "fra_recommendation": "Highly Recommended for FRA recognition based on 73.68% forest cover and 64.85% ST worker participation",
    "key_findings": [
      "Forest cover is exceptionally high at 73.68% (7,726 sq km), indicating strong forest-dependent livelihoods",
      "Groundwater status is Safe with only 5.17% development stage and rising water levels (-1.17m trend)",
      "ST workers comprise 64.85% of MGNREGA workforce, showing significant tribal population",
      "Worker activation rate is 89.04%, indicating active engagement in government schemes"
    ],
    "development_priorities": [
      "Sustainable forest management programs to preserve 73.68% forest cover",
      "Community-based natural resource management training for ST populations",
      "Groundwater recharge structures to maintain Safe status",
      "Women empowerment programs (current 50.49% participation can be increased)"
    ],
    "risk_factors": [
      "High forest cover may face pressure from development projects",
      "Limited economic diversification beyond forest-based livelihoods"
    ],
    "opportunities": [
      "Eco-tourism potential with 73.68% forest cover",
      "NTFP (Non-Timber Forest Products) value chain development",
      "Groundwater security enables agricultural expansion",
      "High ST population qualifies for FRA community forest rights"
    ],
    "summary": "Dhalai district shows excellent conditions for FRA implementation with high forest cover (73.68%), significant ST population (64.85% in MGNREGA), and sustainable groundwater status (Safe category). The area has strong forest-dependent livelihoods and active community participation, making it highly suitable for community forest rights recognition.",
    "confidence": "High",
    "generated_at": "2025-10-04T10:30:00",
    "model_used": "gemini-1.5-flash"
  }
}
```

## Analysis Components

### 1. FRA Recommendation
**Purpose**: Assess eligibility for Forest Rights Act recognition

**Criteria Evaluated**:
- Forest cover percentage (>60% = strong indicator)
- ST population participation (from MGNREGA data)
- Traditional dependence indicators
- Community engagement metrics

**Possible Values**:
- `"Highly Recommended"` - Strong case for FRA
- `"Recommended"` - Good case with supporting evidence
- `"Conditionally Recommended"` - Requires additional verification
- `"Not Recommended"` - Insufficient indicators

### 2. Key Findings (4-6 items)
**Purpose**: Critical insights from collected data

**Characteristics**:
- Specific, quantitative insights
- Highlights both strengths and concerns
- References actual data values
- Contextualizes trends

**Example**:
```json
[
  "Forest cover is exceptionally high at 73.68% (7,726 sq km)",
  "Groundwater status is Safe with only 5.17% development stage",
  "ST workers comprise 64.85% of MGNREGA workforce",
  "Worker activation rate is 89.04%"
]
```

### 3. Development Priorities (3-5 items)
**Purpose**: Actionable intervention recommendations

**Based On**:
- Groundwater status → Recharge structures
- Forest cover → Conservation programs
- MGNREGA participation → Livelihood diversification
- Gender ratios → Women empowerment

**Example**:
```json
[
  "Sustainable forest management programs to preserve forest cover",
  "Community-based natural resource management training",
  "Women empowerment programs (current 50.49% can be increased)"
]
```

### 4. Risk Factors (2-4 items)
**Purpose**: Identify environmental/social vulnerabilities

**Considers**:
- Groundwater stress indicators
- Forest degradation risks
- Livelihood dependencies
- Climate vulnerabilities

### 5. Opportunities (2-4 items)
**Purpose**: Development potential leveraging strengths

**Examples**:
- Eco-tourism (high forest cover)
- NTFP value chains
- Sustainable agriculture (good groundwater)
- Community forest rights (FRA)

### 6. Summary (3-4 sentences)
**Purpose**: Executive overview for decision-makers

**Includes**:
- Overall assessment
- Key statistics
- FRA eligibility conclusion
- Development potential

### 7. Confidence Level
**Purpose**: Data quality indicator

- **High**: Comprehensive data across all indicators
- **Medium**: Some data gaps but sufficient for analysis
- **Low**: Significant missing data, manual review needed

## Data Inputs Used

The AI analyzes the following indicators:

| Category | Data Points | Source Layer |
|----------|-------------|--------------|
| **Forest Cover** | forest_area_sqkm, forest_percentage, geographic_area_sqkm | State boundary (FSI) |
| **Groundwater** | category, stage_of_development_pc, stressed, water_level_trend | District boundary + GW measurements |
| **Aquifer** | type, code | Major aquifers layer |
| **MGNREGA** | worker_activation_rate, women_participation, ST/SC percentages | MGNREGA workers layer |
| **Location** | state, district, village | AOI resolution |

## Configuration

### Enable AI Analysis

Set environment variables or configuration:

```bash
# Required for Vertex AI
export GCP_PROJECT="your-gcp-project-id"
export GCP_LOCATION="us-central1"  # Or your preferred region
export USE_VERTEX=true

# Optional: Google Application Credentials
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"
```

### Configuration File

In `app/config.py` or `.env`:

```python
GCP_PROJECT=your-project-id
GCP_LOCATION=us-central1
USE_VERTEX=true
```

## API Usage

### Get Report with AI Analysis

```bash
# AI analysis is generated automatically when Vertex AI is enabled
curl "http://localhost:8000/report?state=Tripura&district=Dhalai"
```

### Response Structure

```json
{
  "aoi": { ... },
  "indicators": { ... },
  "meta": { ... },
  "narrative": null,
  "ai_analysis": {
    "fra_recommendation": "...",
    "key_findings": [...],
    "development_priorities": [...],
    "risk_factors": [...],
    "opportunities": [...],
    "summary": "...",
    "confidence": "High",
    "generated_at": "2025-10-04T10:30:00",
    "model_used": "gemini-1.5-flash"
  }
}
```

## AI Prompt Engineering

The AI analysis uses a carefully crafted prompt that:

1. **Provides Context**: Explains the FRA and rural development context
2. **Supplies Data**: Structured JSON with all collected indicators
3. **Defines Requirements**: Clear specifications for each analysis component
4. **Enforces Format**: Requires specific JSON structure
5. **Sets Constraints**: Specifies item counts and content requirements

### Prompt Structure

```
You are an expert analyst for FRA and rural development.

DATA:
{structured_indicators}

REQUIREMENTS:
1. FRA RECOMMENDATION - Assess qualification based on forest cover, ST population
2. KEY FINDINGS - List 4-6 critical insights with specific numbers
3. DEVELOPMENT PRIORITIES - Identify 3-5 actionable interventions
4. RISK FACTORS - List 2-4 environmental/social risks
5. OPPORTUNITIES - List 2-4 development opportunities
6. SUMMARY - 3-4 sentence executive summary
7. CONFIDENCE - High/Medium/Low based on data completeness

Return JSON in exact format: {...}
```

## Error Handling

### Fallback Analysis

If AI generation fails, the system returns:

```json
{
  "ai_analysis": {
    "fra_recommendation": "Unable to generate - manual review required",
    "key_findings": ["AI analysis unavailable"],
    "development_priorities": ["Require manual assessment"],
    "risk_factors": ["Data incomplete"],
    "opportunities": ["Further analysis needed"],
    "summary": "AI analysis could not be completed. Please review data manually.",
    "confidence": "Low",
    "model_used": "gemini-1.5-flash"
  }
}
```

### When Vertex AI is Disabled

```json
{
  "ai_analysis": null
}
```

No error is thrown - the field is simply omitted.

## Cost Considerations

### Vertex AI Pricing

**Gemini 1.5 Flash** (as of 2024):
- Input: ~$0.00001875 per 1K characters
- Output: ~$0.000075 per 1K characters

**Typical Request**:
- Input: ~2,000 characters (data + prompt)
- Output: ~1,500 characters (analysis)
- **Cost per analysis**: ~$0.0001-0.0002 USD

**Monthly Estimate** (1000 reports):
- Cost: ~$0.10-0.20 USD

💡 Very cost-effective for production use!

## Testing Without Vertex AI

### Option 1: Disable AI Analysis
```python
# In config
USE_VERTEX=false
```

Response will have `ai_analysis: null`

### Option 2: Mock Vertex Client
For testing, modify `app/vertex.py`:

```python
def generate_ai_analysis(self, aoi, indicators):
    # Return mock data for testing
    return AIAnalysis(
        fra_recommendation="Mock: Highly Recommended",
        key_findings=["Test finding 1", "Test finding 2"],
        # ... etc
    )
```

## Code Locations

| Component | File | Lines |
|-----------|------|-------|
| AIAnalysis model | `app/model.py` | ~77-90 |
| Report model updated | `app/model.py` | ~105 |
| VertexClient.generate_ai_analysis() | `app/vertex.py` | ~110-280 |
| build_report() integration | `app/indicators.py` | ~692-720 |

## Example Use Cases

### 1. FRA Approval Workflow
```python
# Get report
report = get_report(state="Tripura", district="Dhalai")

# Check FRA recommendation
if "Highly Recommended" in report.ai_analysis.fra_recommendation:
    # Fast-track FRA application
    process_fra_application(report)
elif "Not Recommended" in report.ai_analysis.fra_recommendation:
    # Flag for manual review
    flag_for_review(report)
```

### 2. Development Planning
```python
# Extract priorities
priorities = report.ai_analysis.development_priorities

# Allocate resources
for priority in priorities:
    if "groundwater" in priority.lower():
        allocate_budget("water_conservation", priority)
    elif "forest" in priority.lower():
        allocate_budget("forestry", priority)
```

### 3. Risk Assessment
```python
# Check confidence level
if report.ai_analysis.confidence == "Low":
    # Request additional data collection
    request_field_survey(report.aoi)
else:
    # Proceed with analysis
    approve_analysis(report)
```

## Future Enhancements

### Potential Additions:

1. **Historical Trend Analysis**
   - Compare with previous years' data
   - Detect degradation/improvement patterns

2. **Comparative Analysis**
   - Benchmark against similar districts
   - State/national averages

3. **Predictive Modeling**
   - Forecast groundwater trends
   - Project forest cover changes

4. **Multi-language Support**
   - Generate analysis in regional languages
   - Already supported via `narrative` field

5. **Custom Recommendation Rules**
   - Allow users to define FRA criteria weights
   - Configurable thresholds

## Troubleshooting

### Issue: "AI analysis not available"

**Solution**: Check Vertex AI configuration
```bash
# Verify environment variables
echo $GCP_PROJECT
echo $USE_VERTEX

# Test Google Cloud authentication
gcloud auth application-default login
```

### Issue: "Confidence: Low" on every report

**Solution**: Check data completeness
- Verify all layers are accessible
- Check for missing indicators
- Review `meta.notes` for data gaps

### Issue: JSON parsing errors

**Solution**: Check Gemini response format
- Increase `temperature` for more structured output
- Add stricter JSON schema validation
- Use `response_mime_type: "application/json"`

## Summary

✅ **Implemented**: Complete AI analysis infrastructure  
🎯 **Purpose**: FRA recommendations + development insights  
🤖 **Model**: Google Gemini 1.5 Flash (Vertex AI)  
💰 **Cost**: ~$0.0001 per analysis  
📊 **Output**: 7 analysis components with confidence rating  
🔧 **Config**: Requires GCP project + Vertex AI enabled  

The AI analysis transforms raw indicators into actionable recommendations, making the DSS report a powerful decision-support tool for FRA and rural development! 🌳📊🤖
