# USGS Earthquake Agentic Data Pipeline (Google ADK)

An end-to-end agentic data engineering pipeline built with Python and Google's Agent Development Kit (ADK). The `earthquake_pipeline_agent` orchestrates four modular tools to ingest live M2.5+ earthquake data from the USGS public API, clean and aggregate severity metrics with `pandas`, upload both raw and processed datasets to Google Cloud Storage (GCS), and generate an interactive HTML dashboard (`output/report.html`).

## Project Structure
- `earthquake_agent/agent.py` — ADK `root_agent` definition and orchestration instructions
- `earthquake_agent/tools.py` — Modular tools for API ingestion, data transformation, GCS upload, and HTML generation
- `output/` — Generated JSON artifacts and `report.html` dashboard
- `requirements.txt` — Python dependencies
- `.env.example` — Environment variable template

## Setup & Run Instructions
1. Clone the repository and create a virtual environment:
   ```bash
   git clone [https://github.com/kmnagler25/usgs-earthquake-adk.git](https://github.com/kmnagler25/usgs-earthquake-adk.git)
   cd usgs-earthquake-adk
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt