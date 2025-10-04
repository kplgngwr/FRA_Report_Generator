# DSS Report Generation Bot

A FastAPI service that assembles deterministic Decision Support System (DSS) reports for Areas of Interest (AOIs) by querying ArcGIS Living Atlas and custom layers. Optional Vertex AI integration can verbalize the indicators when enabled.

## Features

- AOI resolution (state → district → block → village) with graceful fallbacks
- Indicator bundle generation (groundwater, aquifer, LULC, accessibility, water proximity)
- Deterministic site recommendations (farm pond, check dam, nala bund, percolation tank, tank renovation)
- CSV exports for indicators and recommended sites
- Optional Gemini 1.5 Flash narrative generation when `USE_VERTEX=true`
- Stub mode for local development without live ArcGIS services

## Project layout

```
app/
  main.py          # FastAPI endpoints
  config.py        # Environment-driven configuration
  layers.py        # Layer registry (update with real ArcGIS layer URLs + fields)
  arcgis.py        # REST client with pagination + retry logic
  geo.py           # Geospatial helpers (centroid, haversine, etc.)
  indicators.py    # Indicator orchestration and report assembly
  rules.py         # Deterministic site recommendation engine
  model.py         # Pydantic schema for report payloads
  vertex.py        # Optional Vertex AI narrative helper
```

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `USE_VERTEX` | `false` | Enable Vertex AI narrative generation |
| `GCP_PROJECT` | – | GCP project ID (required when `USE_VERTEX=true`) |
| `GCP_LOCATION` | `us-central1` | Vertex AI region |
| `ARCGIS_TOKEN` | – | Optional ArcGIS token |
| `GW_STRESS_THRESHOLD_M` | `10` | Threshold (m) for groundwater stress classification |
| `NEAREST_POI_RADIUS_M` | `50000` | Search radius for proximity queries |
| `STUB_MODE` | `false` | Return deterministic stub data instead of live queries |

Create a `.env` file (optional) to override defaults.

## Local development

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

Visit [http://localhost:8080/docs](http://localhost:8080/docs) for interactive API docs.

## Running tests

```bash
pytest
```

## Docker

```bash
docker build -t report-bot:local .
docker run -p 8080:8080 -e STUB_MODE=true report-bot:local
```

## Cloud Build → Cloud Run

1. Update `cloudbuild.yaml` substitutions if needed (`_SERVICE_NAME`, `_REGION`, `_IMAGE_URI`).
2. Submit the build:

```bash
gcloud builds submit --config cloudbuild.yaml .
```

3. Cloud Build will push the image to Artifact Registry and deploy to Cloud Run with a `/health` health check.

## Next steps

- Replace placeholder layer URLs in `app/layers.py` with real Living Atlas + custom layers.
- Extend `IndicatorService` methods to map real attribute names and geometries.
- Add more unit tests once real data pipelines are connected.
