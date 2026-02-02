# FermentIQ

FermentIQ is an AI-powered fermentation monitoring and analysis system. It provides real-time insights into fermentation processes by comparing live data against a "Golden Standard" to ensure quality and consistency.

## Features

-   **Real-Time Monitoring**: Live tracking of pH, Temperature, and CO2 levels for multiple batches.
-   **AI-Driven Comparison**: Automatic comparison with golden standard data to detect deviations.
-   **Multi-Batch Support**: Monitor up to 4 concurrent fermentation batches with different simulated quality profiles (Perfect, Acceptable, Concerning, Failed).
-   **WebSocket Streaming**: Low-latency data updates via WebSockets.
-   **REST API**: Comprehensive API for data retrieval, history, and report generation.

## Tech Stack

-   **Backend**: Python, FastAPI, Uvicorn, Scikit-learn, Pandas, NumPy.
-   **Frontend**: HTML5, CSS3, Vanilla JavaScript.

## Quick Start

### 1. Backend Setup

Navigate to the `Backend` directory and install the dependencies:

```bash
cd Backend
pip install -r requirements.txt
```

Start the FastAPI server:

```bash
uvicorn main:app --reload --port 8000
```

The backend API will be available at `http://localhost:8000`. You can view the API documentation at `http://localhost:8000/docs`.

### 2. Frontend Setup

No build process is required for the frontend. Simply open `Frontend/index.html` in your web browser.

## Usage

1.  Ensure the Backend server is running.
2.  Open the Frontend dashboard.
3.  The dashboard will automatically connect to the backend and start displaying real-time data for 4 simulated batches.

## Batch Profiles

-   **Batch 1 (Green)**: Acceptable quality (90% match).
-   **Batch 2 (Blue)**: Perfect quality (100% match).
-   **Batch 3 (Red)**: Failed batch (<75% match).
-   **Batch 4 (Orange)**: Concerning batch (85% match).
 
