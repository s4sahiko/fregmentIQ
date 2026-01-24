"""
Streaming Service - Coordinates MQTT and WebSocket for real-time data flow
This is the main orchestrator that doesn't require an actual MQTT broker.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
import threading
import time
from typing import Dict, List, Optional, Callable
from datetime import datetime

from models.fermentation_generator import FermentationDataGenerator
from models.data_comparator import DataComparator
from services.sms_service import get_sms_service


class StreamingService:
    """
    Coordinates data generation, comparison, and WebSocket streaming
    Works without external MQTT broker by simulating the message passing internally
    """
    
    def __init__(self):
        self.generator = FermentationDataGenerator()
        self.comparator = DataComparator(golden_standard_path="data/golden_standard.json")
        self.sms_service = get_sms_service()
        
        # Pre-generate batch data
        self.batch_data: Dict[int, Dict] = {}
        self.current_index: Dict[int, int] = {1: 0, 2: 0, 3: 0, 4: 0}
        
        # Connected WebSocket clients (managed externally)
        self.broadcast_callback: Optional[Callable] = None
        
        # History tracking for REST API access
        self.batch_history: Dict[int, List[Dict]] = {1: [], 2: [], 3: [], 4: []}
        
        self.is_running = False
        self._lock = threading.Lock()
    
    def initialize(self):
        """Initialize by generating all batch data"""
        print("[StreamingService] Generating batch data...")
        for batch_num in range(1, 5):
            self.batch_data[batch_num] = self.generator.generate_batch_profile(
                batch_number=batch_num,
                duration_hours=72,
                sampling_interval_minutes=30
            )
            print(f"  Batch {batch_num}: {self.batch_data[batch_num]['batch_status']} - {len(self.batch_data[batch_num]['timestamps'])} samples")
        print("[StreamingService] Initialization complete")
    
    def get_next_data_point(self, batch_num: int) -> Dict:
        """Get the next data point for a batch (simulates MQTT message)"""
        with self._lock:
            if batch_num not in self.batch_data:
                self.initialize()
            
            batch = self.batch_data[batch_num]
            idx = self.current_index[batch_num]
            
            # Check if we reached the end - Return None to stop
            if idx >= len(batch["timestamps"]):
                return None
            
            data_point = {
                "batch_number": batch_num,
                "batch_status": batch["batch_status"],
                "expected_quality_score": batch["expected_quality_score"],
                "description": batch["description"],
                "timestamp": batch["timestamps"][idx],
                "ph": batch["ph"][idx],
                "temperature": batch["temperature"][idx],
                "co2": batch["co2"][idx],
                "sample_index": idx,
                "total_samples": len(batch["timestamps"])
            }
            
            # Increment index
            self.current_index[batch_num] = idx + 1
            
            return data_point
    
    def compare_data_point(self, batch_num: int, data_point: Dict) -> Dict:
        """Compare data point with golden standard (simulates MQTT subscriber)"""
        if self.comparator.golden_standard is None:
            return {"error": "Golden standard not loaded"}
        
        idx = data_point["sample_index"]
        gs = self.comparator.golden_standard
        
        # Get ideal values
        ideal_ph = gs["ph"][idx] if idx < len(gs["ph"]) else gs["ph"][-1]
        ideal_temp = gs["temperature"][idx] if idx < len(gs["temperature"]) else gs["temperature"][-1]
        ideal_co2 = gs["co2"][idx] if idx < len(gs["co2"]) else gs["co2"][-1]
        
        # Calculate deviations
        ph_deviation = abs(data_point["ph"] - ideal_ph)
        temp_deviation = abs(data_point["temperature"] - ideal_temp)
        co2_deviation = abs(data_point["co2"] - ideal_co2)
        
        # Determine status
        def get_status(dev, warn_thresh, crit_thresh):
            if dev < warn_thresh:
                return "normal"
            elif dev < crit_thresh:
                return "warning"
            return "critical"
        
        ph_status = get_status(ph_deviation, 0.3, 0.5)
        temp_status = get_status(temp_deviation, 2.0, 3.5)
        co2_status = get_status(co2_deviation, 1.5, 3.0)
        
        # Calculate quality score
        ph_score = max(0, 100 * (1 - ph_deviation / 1.0))
        temp_score = max(0, 100 * (1 - temp_deviation / 5.0))
        co2_score = max(0, 100 * (1 - co2_deviation / 5.0))
        quality_score = (ph_score + temp_score + co2_score) / 3
        
        # Determine overall status based on Quality Score (matching Frontend logic)
        if quality_score >= 95:
            overall_status = "perfect"
        elif quality_score >= 90:
            overall_status = "acceptable"
        elif quality_score >= 80:
            overall_status = "concerning"
        else:
            overall_status = "failed"
        
        return {
            "batch_number": batch_num,
            "sample_index": idx,
            "timestamp": data_point["timestamp"],
            "actual": {
                "ph": round(data_point["ph"], 3),
                "temperature": round(data_point["temperature"], 2),
                "co2": round(data_point["co2"], 3)
            },
            "ideal": {
                "ph": round(ideal_ph, 3),
                "temperature": round(ideal_temp, 2),
                "co2": round(ideal_co2, 3)
            },
            "deviations": {
                "ph": round(ph_deviation, 3),
                "temperature": round(temp_deviation, 2),
                "co2": round(co2_deviation, 3)
            },
            "status": {
                "ph": ph_status,
                "temperature": temp_status,
                "co2": co2_status,
                "overall": overall_status
            },
            "quality_score": round(quality_score, 1),
            "batch_status": data_point["batch_status"],
            "expected_quality": data_point["expected_quality_score"]
        }
    
    def process_all_batches(self) -> List[Dict]:
        """Process one data point for all batches"""
        results = []
        for batch_num in range(1, 5):
            data_point = self.get_next_data_point(batch_num)
            if data_point:
                comparison = self.compare_data_point(batch_num, data_point)
                result = {
                    "batch_number": batch_num,
                    "data_point": data_point,
                    "comparison": comparison
                }
                
                # Check for SMS alerts
                current_status = comparison["status"]["overall"]
                previous_status = self.sms_service.check_alert_condition(batch_num, current_status)
                
                if previous_status is not None:
                    details = f"pH: {comparison['actual']['ph']} | Temp: {comparison['actual']['temperature']} | CO2: {comparison['actual']['co2']}"
                    # Don't hold up the stream for SMS
                    threading.Thread(
                        target=self.sms_service.send_alert,
                        args=(batch_num, current_status, previous_status, details)
                    ).start()

                results.append(result)
                
                # Store in history for REST API access
                self.batch_history[batch_num].append(result)
        return results
    
    def get_batch_history(self, batch_num: int) -> List[Dict]:
        """Get all historical data points for a batch (used by REST API)"""
        if batch_num not in self.batch_history:
            return []
        return self.batch_history[batch_num]
    
    def set_broadcast_callback(self, callback: Callable):
        """Set callback for broadcasting to WebSocket clients"""
        self.broadcast_callback = callback
    
    async def stream_loop(self, interval_seconds: float = 1.0):
        """Async loop for streaming data to WebSocket clients"""
        self.is_running = True
        self.initialize()
        
        while self.is_running:
            results = self.process_all_batches()
            
            if not results:
                print("[StreamingService] All batches completed. Stopping stream.")
                self.is_running = False
                break
            
            if self.broadcast_callback:
                for result in results:
                    await self.broadcast_callback(result)
            
            await asyncio.sleep(interval_seconds)
    
    def stop(self):
        """Stop the streaming service"""
        self.is_running = False


# Singleton instance
_streaming_service: StreamingService = None


def get_streaming_service() -> StreamingService:
    """Get or create streaming service instance"""
    global _streaming_service
    if _streaming_service is None:
        _streaming_service = StreamingService()
    return _streaming_service


# For testing
if __name__ == "__main__":
    service = StreamingService()
    service.initialize()
    
    print("\nProcessing one cycle of all batches:")
    results = service.process_all_batches()
    
    for result in results:
        comp = result["comparison"]
        print(f"\nBatch {comp['batch_number']} ({comp['batch_status']}):")
        print(f"  Sample: {comp['sample_index']}")
        print(f"  pH: {comp['actual']['ph']:.2f} vs {comp['ideal']['ph']:.2f} (dev: {comp['deviations']['ph']:.3f})")
        print(f"  Temp: {comp['actual']['temperature']:.1f}°C vs {comp['ideal']['temperature']:.1f}°C")
        print(f"  CO2: {comp['actual']['co2']:.2f} vs {comp['ideal']['co2']:.2f}")
        print(f"  Quality Score: {comp['quality_score']:.1f}")
        print(f"  Status: {comp['status']['overall']}")
