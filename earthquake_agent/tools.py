import json
import os
from datetime import datetime, timezone
import pandas as pd
import requests
from google.cloud import storage

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch_earthquake_data() -> dict:
    """Fetches the past 7 days of M2.5+ global earthquakes from the USGS public API and saves raw JSON locally.

    Returns:
        dict: Status, total earthquake count, and the local file path of the saved raw JSON.
    """
    url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_week.geojson"
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    data = response.json()

    raw_path = os.path.join(OUTPUT_DIR, "raw_earthquakes.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    count = len(data.get("features", []))
    return {
        "status": "success",
        "total_events": count,
        "raw_file_path": raw_path,
    }


def process_earthquake_data(raw_file_path: str) -> dict:
    """Cleans raw USGS earthquake JSON, categorizes events by severity, aggregates metrics, and saves processed JSON.

    Args:
        raw_file_path (str): Path to the raw JSON file produced by fetch_earthquake_data.

    Returns:
        dict: Status, summary statistics, severity breakdown, and local file path of the processed JSON.
    """
    with open(raw_file_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    records = []
    for item in raw_data.get("features", []):
        props = item.get("properties", {})
        geom = item.get("geometry", {})
        coords = geom.get("coordinates", [None, None, None])
        mag = props.get("mag")
        if mag is None:
            continue

        if mag < 4.0:
            severity = "Minor (2.5 - 3.9)"
        elif mag < 5.0:
            severity = "Light (4.0 - 4.9)"
        elif mag < 6.0:
            severity = "Moderate (5.0 - 5.9)"
        else:
            severity = "Strong (6.0+)"

        ts_ms = props.get("time")
        event_time = (
            datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            if ts_ms
            else "Unknown"
        )

        records.append({
            "place": props.get("place", "Unknown"),
            "magnitude": round(float(mag), 2),
            "depth_km": round(float(coords[2]), 1) if coords[2] is not None else 0.0,
            "severity": severity,
            "time_utc": event_time,
        })

    df = pd.DataFrame(records)
    severity_counts = df["severity"].value_counts().to_dict()
    top_10 = df.sort_values(by="magnitude", ascending=False).head(10).to_dict(orient="records")

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "total_processed": int(len(df)),
        "average_magnitude": round(float(df["magnitude"].mean()), 2),
        "max_magnitude": round(float(df["magnitude"].max()), 2),
        "average_depth_km": round(float(df["depth_km"].mean()), 1),
        "severity_breakdown": severity_counts,
        "top_10_earthquakes": top_10,
    }

    processed_path = os.path.join(OUTPUT_DIR, "processed_earthquakes.json")
    with open(processed_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return {
        "status": "success",
        "processed_file_path": processed_path,
        "total_processed": summary["total_processed"],
        "average_magnitude": summary["average_magnitude"],
        "max_magnitude": summary["max_magnitude"],
        "severity_breakdown": severity_counts,
    }


def upload_to_gcs(local_file_path: str, destination_blob_name: str) -> dict:
    """Uploads a local data file to the configured Google Cloud Storage bucket.

    Args:
        local_file_path (str): Path to the local file to upload.
        destination_blob_name (str): Target object name inside the GCS bucket.

    Returns:
        dict: Upload status and the resulting gs:// URI.
    """
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if not bucket_name:
        raise ValueError("GCS_BUCKET_NAME is not set in the environment variables.")

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(local_file_path)

    return {
        "status": "success",
        "gcs_uri": f"gs://{bucket_name}/{destination_blob_name}",
    }


def generate_html_report(processed_file_path: str) -> dict:
    """Generates a standalone HTML dashboard with a Chart.js bar chart and table of top earthquakes.

    Args:
        processed_file_path (str): Path to the processed JSON file produced by process_earthquake_data.

    Returns:
        dict: Status and local path to the generated HTML report.
    """
    with open(processed_file_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    labels = list(summary["severity_breakdown"].keys())
    values = list(summary["severity_breakdown"].values())

    rows_html = ""
    for eq in summary["top_10_earthquakes"]:
        rows_html += f"""
        <tr>
            <td><strong>{eq['magnitude']}</strong></td>
            <td>{eq['severity']}</td>
            <td>{eq['place']}</td>
            <td>{eq['depth_km']} km</td>
            <td>{eq['time_utc']}</td>
        </tr>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>USGS Weekly Earthquake Pipeline Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 960px; margin: 40px auto; padding: 0 20px; color: #222; background: #f8f9fa; }}
        h1 {{ color: #1a365d; }}
        .cards {{ display: flex; gap: 16px; margin: 20px 0; }}
        .card {{ background: white; padding: 16px 24px; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); flex: 1; }}
        .card h3 {{ margin: 0 0 8px; font-size: 14px; color: #555; }}
        .card p {{ margin: 0; font-size: 24px; font-weight: bold; color: #1a365d; }}
        .chart-box {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); margin-bottom: 24px; }}
        table {{ width: 100%; border-collapse: collapse; background: white; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
        th {{ background: #1a365d; color: white; }}
    </style>
</head>
<body>
    <h1>USGS Weekly Earthquake Activity Report</h1>
    <p>Generated at: {summary['generated_at_utc']}</p>
    <div class="cards">
        <div class="card"><h3>Total Events (M2.5+)</h3><p>{summary['total_processed']}</p></div>
        <div class="card"><h3>Max Magnitude</h3><p>{summary['max_magnitude']}</p></div>
        <div class="card"><h3>Average Magnitude</h3><p>{summary['average_magnitude']}</p></div>
        <div class="card"><h3>Avg Depth</h3><p>{summary['average_depth_km']} km</p></div>
    </div>
    <div class="chart-box">
        <h2>Earthquakes by Severity Category</h2>
        <canvas id="severityChart" height="100"></canvas>
    </div>
    <h2>Top 10 Strongest Earthquakes (Past 7 Days)</h2>
    <table>
        <thead>
            <tr><th>Magnitude</th><th>Severity</th><th>Location</th><th>Depth</th><th>Time (UTC)</th></tr>
        </thead>
        <tbody>{rows_html}</tbody>
    </table>
    <script>
        new Chart(document.getElementById('severityChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(labels)},
                datasets: [{{
                    label: 'Number of Earthquakes',
                    data: {json.dumps(values)},
                    backgroundColor: ['#3182ce', '#dd6b20', '#e53e3e', '#805ad5']
                }}]
            }},
            options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }} }}
        }});
    </script>
</body>
</html>
"""

    report_path = os.path.join(OUTPUT_DIR, "report.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return {
        "status": "success",
        "html_report_path": report_path,
    }