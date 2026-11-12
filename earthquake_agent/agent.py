from google.adk import Agent
from google.adk.models.google_llm import Gemini
from google.genai import types
from .tools import (
    fetch_earthquake_data,
    process_earthquake_data,
    upload_to_gcs,
    generate_html_report,
)

retry_config = types.HttpRetryOptions(
    attempts=5,
    initial_delay=2,
    exp_base=2,
    http_status_codes=[429, 500, 503, 504],
)

root_agent = Agent(
    name="earthquake_pipeline_agent",
    model=Gemini(model="gemini-3.5-flash-lite", retry_options=retry_config),
    description="Orchestrates an end-to-end USGS earthquake data ingestion, processing, cloud storage, and HTML visualization pipeline.",
    instruction=(
        "You are an automated data engineering agent. When the user asks you to run the pipeline:\n"
        "1. Call `fetch_earthquake_data` to download the latest 7-day USGS M2.5+ earthquake dataset.\n"
        "2. Pass the returned `raw_file_path` into `process_earthquake_data` to categorize events by severity and compute summary statistics.\n"
        "3. Call `upload_to_gcs` twice: first to upload `output/raw_earthquakes.json` as `raw/raw_earthquakes.json`, and second to upload `output/processed_earthquakes.json` as `processed/processed_earthquakes.json`.\n"
        "4. Pass the `processed_file_path` into `generate_html_report` to build the visual dashboard.\n"
        "Verify each step returns status 'success' before continuing, and conclude with a clear summary of the earthquake statistics, GCS URIs, and local HTML report path."
    ),
    tools=[
        fetch_earthquake_data,
        process_earthquake_data,
        upload_to_gcs,
        generate_html_report,
    ],
)