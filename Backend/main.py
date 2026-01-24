"""
FastAPI Main Application for FermentIQ Backend with WebSocket Support
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Set
import uvicorn
import asyncio
import json
from datetime import datetime

from models.fermentation_generator import FermentationDataGenerator
from models.data_comparator import DataComparator
from services.streaming_service import StreamingService
from config import CORS_ORIGINS, API_HOST, API_PORT

# Initialize FastAPI app
app = FastAPI(
    title="FermentIQ AI Backend",
    description="AI-powered fermentation data generation and comparison API with real-time WebSocket streaming",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize AI models
fermentation_generator = FermentationDataGenerator(seed=42)
data_comparator = DataComparator(golden_standard_path="data/golden_standard.json")

# Initialize streaming service
streaming_service = StreamingService()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.latest_data: Dict[int, Dict] = {}
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        print(f"[WebSocket] Client connected. Total: {len(self.active_connections)}")
        
        # Send initial state if available
        if self.latest_data:
            await websocket.send_json({
                "type": "initial_state",
                "data": self.latest_data,
                "timestamp": datetime.now().isoformat()
            })
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        print(f"[WebSocket] Client disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.add(connection)
        
        self.active_connections -= disconnected

manager = ConnectionManager()

# Background streaming task
streaming_task = None

async def stream_data():
    """Background task to stream data to all connected clients"""
    streaming_service.initialize()
    
    while True:
        if manager.active_connections:
            results = streaming_service.process_all_batches()
            
            if not results:
                print("[StreamingService] All batches completed. Stopping stream.")
                break
            
            for result in results:
                batch_num = result["batch_number"]
                manager.latest_data[batch_num] = result
                
                await manager.broadcast({
                    "type": "batch_update",
                    "batch_number": batch_num,
                    "data_point": result["data_point"],
                    "comparison": result["comparison"],
                    "timestamp": datetime.now().isoformat()
                })
        
        await asyncio.sleep(1.0)  # Update every 1 second (144 data points in 144 seconds)


@app.on_event("startup")
async def startup_event():
    """Start background streaming on app startup"""
    global streaming_task
    streaming_task = asyncio.create_task(stream_data())
    print("[Startup] Background streaming task started")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    global streaming_task
    if streaming_task:
        streaming_task.cancel()
    print("[Shutdown] Background streaming task stopped")


# Pydantic models for request/response validation
class GenerateRequest(BaseModel):
    duration_hours: int = Field(default=72, ge=1, le=168, description="Fermentation duration in hours")
    sampling_interval_minutes: int = Field(default=30, ge=1, le=120, description="Sampling interval in minutes")
    variation_factor: float = Field(default=1.0, ge=0.1, le=3.0, description="Variation factor for noise")
    add_anomalies: bool = Field(default=False, description="Whether to inject anomalies")


class FermentationData(BaseModel):
    timestamps: List[float]
    ph: List[float]
    temperature: List[float]
    co2: List[float]
    duration_hours: int
    sampling_interval_minutes: int
    variation_factor: Optional[float] = None
    has_anomalies: Optional[bool] = None


class CompareRequest(BaseModel):
    generated_data: Dict[str, List[float]] = Field(
        description="Generated fermentation data with timestamps, ph, temperature, co2"
    )
    use_golden_standard: bool = Field(
        default=True,
        description="Whether to use the default golden standard"
    )
    custom_golden_standard: Optional[Dict[str, List[float]]] = Field(
        default=None,
        description="Custom golden standard data (if not using default)"
    )


class ComparisonResponse(BaseModel):
    deviations: Dict
    anomalies: Dict
    similarity: Dict
    assessment: Dict
    comparison_timestamp: str


class HealthResponse(BaseModel):
    status: str
    message: str
    models_loaded: Dict[str, bool]
    websocket_clients: int


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time batch data streaming
    
    Connect to ws://localhost:8000/ws to receive live batch updates
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"[WebSocket] Error: {e}")
        manager.disconnect(websocket)


# ============================================
# REST API Endpoints for Data Access
# ============================================

@app.get("/api/batches", tags=["Data Access"])
async def get_all_batches():
    """
    Get current status of all active batches
    
    Returns real-time status, quality scores, and latest readings for all 4 batches.
    """
    if not manager.latest_data:
        return {
            "message": "No batch data available yet. Wait for streaming to start.",
            "batches": {}
        }
    
    batches = {}
    for batch_num, data in manager.latest_data.items():
        batches[batch_num] = {
            "batch_number": batch_num,
            "status": data["data_point"].get("batch_status", "unknown"),
            "quality_score": data["comparison"].get("quality_score", 0),
            "current_values": {
                "ph": data["data_point"].get("ph"),
                "temperature": data["data_point"].get("temperature"),
                "co2": data["data_point"].get("co2"),
                "timestamp": data["data_point"].get("timestamp")
            },
            "ideal_values": data["comparison"].get("ideal", {}),
            "deviations": data["comparison"].get("deviations", {})
        }
    
    return {
        "total_batches": len(batches),
        "batches": batches,
        "retrieved_at": datetime.now().isoformat()
    }


@app.get("/api/batches/{batch_number}", tags=["Data Access"])
async def get_batch_details(batch_number: int):
    """
    Get detailed information for a specific batch
    
    - **batch_number**: Batch ID (1-4)
    """
    if batch_number < 1 or batch_number > 4:
        raise HTTPException(status_code=400, detail="batch_number must be 1-4")
    
    if batch_number not in manager.latest_data:
        raise HTTPException(status_code=404, detail=f"Batch {batch_number} data not available yet")
    
    data = manager.latest_data[batch_number]
    return {
        "batch_number": batch_number,
        "data_point": data["data_point"],
        "comparison": data["comparison"],
        "retrieved_at": datetime.now().isoformat()
    }


@app.get("/api/batches/{batch_number}/history", tags=["Data Access"])
async def get_batch_history(batch_number: int):
    """
    Get complete historical data for a batch
    
    Returns all recorded data points since the batch started streaming.
    - **batch_number**: Batch ID (1-4)
    """
    if batch_number < 1 or batch_number > 4:
        raise HTTPException(status_code=400, detail="batch_number must be 1-4")
    
    history = streaming_service.get_batch_history(batch_number)
    
    if not history:
        raise HTTPException(status_code=404, detail=f"No history available for Batch {batch_number}")
    
    return {
        "batch_number": batch_number,
        "total_data_points": len(history),
        "history": history,
        "retrieved_at": datetime.now().isoformat()
    }


@app.get("/api/batches/{batch_number}/download", tags=["Data Access"])
async def download_batch_data(
    batch_number: int,
    format: str = "json"
):
    """
    Download batch data as JSON or CSV
    
    - **batch_number**: Batch ID (1-4)
    - **format**: Output format - 'json' or 'csv' (default: json)
    """
    if batch_number < 1 or batch_number > 4:
        raise HTTPException(status_code=400, detail="batch_number must be 1-4")
    
    if format not in ["json", "csv"]:
        raise HTTPException(status_code=400, detail="format must be 'json' or 'csv'")
    
    history = streaming_service.get_batch_history(batch_number)
    
    if not history:
        raise HTTPException(status_code=404, detail=f"No data available for Batch {batch_number}")
    
    if format == "json":
        return {
            "batch_number": batch_number,
            "format": "json",
            "total_records": len(history),
            "data": history,
            "generated_at": datetime.now().isoformat()
        }
    
    # CSV format
    csv_lines = ["timestamp,ph,temperature,co2,ideal_ph,ideal_temperature,ideal_co2,quality_score,status"]
    
    for record in history:
        dp = record.get("data_point", {})
        comp = record.get("comparison", {})
        ideal = comp.get("ideal", {})
        
        csv_lines.append(
            f"{dp.get('timestamp', '')},{dp.get('ph', '')},{dp.get('temperature', '')},"
            f"{dp.get('co2', '')},{ideal.get('ph', '')},{ideal.get('temperature', '')},"
            f"{ideal.get('co2', '')},{comp.get('quality_score', '')},{dp.get('batch_status', '')}"
        )
    
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        content="\n".join(csv_lines),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=batch_{batch_number}_data.csv"
        }
    )


@app.get("/api/summary", tags=["Data Access"])
async def get_summary_statistics():
    """
    Get aggregated summary statistics for all batches
    
    Returns counts by status, average quality scores, and overall health metrics.
    """
    if not manager.latest_data:
        return {
            "message": "No data available yet",
            "summary": {}
        }
    
    status_counts = {"perfect": 0, "acceptable": 0, "concerning": 0, "failed": 0}
    quality_scores = []
    
    for batch_num, data in manager.latest_data.items():
        score = data["comparison"].get("quality_score", 0)
        quality_scores.append(score)
        
        # Determine status from quality score
        if score >= 95:
            status_counts["perfect"] += 1
        elif score >= 90:
            status_counts["acceptable"] += 1
        elif score >= 80:
            status_counts["concerning"] += 1
        else:
            status_counts["failed"] += 1
    
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    
    return {
        "total_active_batches": len(manager.latest_data),
        "status_distribution": status_counts,
        "average_quality_score": round(avg_quality, 2),
        "min_quality_score": min(quality_scores) if quality_scores else 0,
        "max_quality_score": max(quality_scores) if quality_scores else 0,
        "batches_needing_attention": status_counts["concerning"] + status_counts["failed"],
        "retrieved_at": datetime.now().isoformat()
    }


@app.get("/api/export/all", tags=["Data Access"])
async def export_all_batches(format: str = "json"):
    """
    Export data for all batches combined
    
    - **format**: Output format - 'json' or 'csv' (default: json)
    """
    if format not in ["json", "csv"]:
        raise HTTPException(status_code=400, detail="format must be 'json' or 'csv'")
    
    all_data = {}
    for batch_num in range(1, 5):
        history = streaming_service.get_batch_history(batch_num)
        if history:
            all_data[batch_num] = history
    
    if not all_data:
        raise HTTPException(status_code=404, detail="No batch data available for export")
    
    if format == "json":
        return {
            "format": "json",
            "batches": all_data,
            "generated_at": datetime.now().isoformat()
        }
    
    # CSV format - all batches combined
    csv_lines = ["batch_number,timestamp,ph,temperature,co2,ideal_ph,ideal_temperature,ideal_co2,quality_score,status"]
    
    for batch_num, history in all_data.items():
        for record in history:
            dp = record.get("data_point", {})
            comp = record.get("comparison", {})
            ideal = comp.get("ideal", {})
            
            csv_lines.append(
                f"{batch_num},{dp.get('timestamp', '')},{dp.get('ph', '')},{dp.get('temperature', '')},"
                f"{dp.get('co2', '')},{ideal.get('ph', '')},{ideal.get('temperature', '')},"
                f"{ideal.get('co2', '')},{comp.get('quality_score', '')},{dp.get('batch_status', '')}"
            )
    
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        content="\n".join(csv_lines),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=all_batches_data.csv"
        }
    )


# API Endpoints
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to FermentIQ AI Backend",
        "version": "2.0.0",
        "docs": "/docs",
        "websocket": "ws://localhost:8000/ws"
    }


@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "All systems operational",
        "models_loaded": {
            "fermentation_generator": fermentation_generator is not None,
            "data_comparator": data_comparator is not None,
            "golden_standard": data_comparator.golden_standard is not None,
            "streaming_service": streaming_service is not None
        },
        "websocket_clients": len(manager.active_connections)
    }


@app.post("/api/generate", response_model=FermentationData, tags=["Generation"])
async def generate_fermentation_data(request: GenerateRequest):
    """
    Generate fermentation process data (pH, Temperature, CO2)
    
    This endpoint uses an AI model to generate realistic fermentation data
    with temporal correlations and optional anomalies.
    """
    try:
        data = fermentation_generator.generate_batch(
            duration_hours=request.duration_hours,
            sampling_interval_minutes=request.sampling_interval_minutes,
            variation_factor=request.variation_factor,
            add_anomalies=request.add_anomalies
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating data: {str(e)}")


@app.post("/api/generate-batch-profile", tags=["Generation"])
async def generate_batch_profile(
    batch_number: int = 1,
    duration_hours: int = 72,
    sampling_interval_minutes: int = 30
):
    """
    Generate predefined batch profiles with specific quality targets
    
    - **Batch 1**: 90% match - Acceptable (degrades after 48-50 hours)
    - **Batch 2**: 100% match - Perfect (matches golden standard throughout)
    - **Batch 3**: <75% match - Failed (poor quality throughout)
    - **Batch 4**: 85% match - Concerning (moderate deviations)
    """
    if batch_number < 1 or batch_number > 4:
        raise HTTPException(status_code=400, detail="batch_number must be 1-4")
    
    try:
        data = fermentation_generator.generate_batch_profile(
            batch_number=batch_number,
            duration_hours=duration_hours,
            sampling_interval_minutes=sampling_interval_minutes
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating batch profile: {str(e)}")


@app.post("/api/compare", response_model=ComparisonResponse, tags=["Comparison"])
async def compare_with_golden_standard(request: CompareRequest):
    """
    Compare generated fermentation data with golden standard dataset
    
    This endpoint performs comprehensive statistical analysis and anomaly detection
    to evaluate the quality of fermentation data.
    """
    try:
        # Determine which golden standard to use
        golden_standard = None
        if not request.use_golden_standard and request.custom_golden_standard:
            golden_standard = request.custom_golden_standard
        
        # Perform comparison
        comparison_result = data_comparator.compare_datasets(
            generated_data=request.generated_data,
            golden_standard=golden_standard
        )
        
        return comparison_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparing data: {str(e)}")


@app.get("/api/golden-standard", tags=["Golden Standard"])
async def get_golden_standard():
    """
    Retrieve the golden standard dataset
    
    Returns the ideal fermentation process parameters used for comparison.
    """
    if data_comparator.golden_standard is None:
        raise HTTPException(status_code=404, detail="Golden standard not loaded")
    
    return data_comparator.golden_standard


@app.post("/api/generate-and-compare", tags=["Combined"])
async def generate_and_compare(request: GenerateRequest):
    """
    Generate fermentation data and immediately compare with golden standard
    
    This is a convenience endpoint that combines generation and comparison.
    """
    try:
        # Generate data
        generated_data = fermentation_generator.generate_batch(
            duration_hours=request.duration_hours,
            sampling_interval_minutes=request.sampling_interval_minutes,
            variation_factor=request.variation_factor,
            add_anomalies=request.add_anomalies
        )
        
        # Compare with golden standard
        comparison_result = data_comparator.compare_datasets(generated_data)
        
        # Generate text report
        text_report = data_comparator.generate_comparison_report(generated_data)
        
        return {
            "generated_data": generated_data,
            "comparison": comparison_result,
            "text_report": text_report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in generate and compare: {str(e)}")


@app.post("/api/comparison-report", tags=["Comparison"])
async def get_comparison_report(request: CompareRequest):
    """
    Get a human-readable comparison report
    
    Returns a formatted text report of the comparison analysis.
    """
    try:
        golden_standard = None
        if not request.use_golden_standard and request.custom_golden_standard:
            golden_standard = request.custom_golden_standard
        
        report = data_comparator.generate_comparison_report(
            generated_data=request.generated_data,
            golden_standard=golden_standard
        )
        
        return {"report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")


# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True
    )
