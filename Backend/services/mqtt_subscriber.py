"""
MQTT Subscriber Service - Receives data and passes to comparator
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import threading
from typing import Dict, Callable, Optional, List
import paho.mqtt.client as mqtt

from models.data_comparator import DataComparator


class MQTTSubscriber:
    """
    Subscribes to fermentation data topics and passes to comparator
    """
    
    def __init__(
        self,
        broker_host: str = "localhost",
        broker_port: int = 1883,
        client_id: str = "fermentiq_subscriber"
    ):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client_id = client_id
        
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # Initialize comparator
        self.comparator = DataComparator(
            golden_standard_path="data/golden_standard.json"
        )
        
        # Store accumulated data for each batch
        self.batch_history: Dict[int, List[Dict]] = {1: [], 2: [], 3: [], 4: []}
        
        # Callback for when comparison is ready
        self.on_comparison_callback: Optional[Callable] = None
    
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            print(f"[MQTT Subscriber] Connected to broker at {self.broker_host}:{self.broker_port}")
            # Subscribe to all batch topics
            client.subscribe("fermentiq/batch/+/data", qos=1)
            print("[MQTT Subscriber] Subscribed to fermentiq/batch/+/data")
        else:
            print(f"[MQTT Subscriber] Connection failed with code {rc}")
    
    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        print(f"[MQTT Subscriber] Disconnected from broker (code: {rc})")
    
    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            # Extract batch number from topic
            parts = topic.split("/")
            batch_num = int(parts[2])
            
            # Store data point
            self.batch_history[batch_num].append(payload)
            
            # Only keep last 144 points (full 72-hour cycle)
            if len(self.batch_history[batch_num]) > 144:
                self.batch_history[batch_num] = self.batch_history[batch_num][-144:]
            
            # Perform comparison
            comparison_result = self._compare_batch(batch_num, payload)
            
            # Call callback if set
            if self.on_comparison_callback:
                self.on_comparison_callback(batch_num, payload, comparison_result)
            
        except Exception as e:
            print(f"[MQTT Subscriber] Error processing message: {e}")
    
    def _compare_batch(self, batch_num: int, data_point: Dict) -> Dict:
        """Compare single data point with golden standard"""
        if self.comparator.golden_standard is None:
            return {"error": "Golden standard not loaded"}
        
        idx = data_point.get("sample_index", 0)
        gs = self.comparator.golden_standard
        
        # Get ideal values at this index
        ideal_ph = gs["ph"][idx] if idx < len(gs["ph"]) else gs["ph"][-1]
        ideal_temp = gs["temperature"][idx] if idx < len(gs["temperature"]) else gs["temperature"][-1]
        ideal_co2 = gs["co2"][idx] if idx < len(gs["co2"]) else gs["co2"][-1]
        
        # Calculate deviations
        ph_deviation = abs(data_point["ph"] - ideal_ph)
        temp_deviation = abs(data_point["temperature"] - ideal_temp)
        co2_deviation = abs(data_point["co2"] - ideal_co2)
        
        # Determine status based on thresholds
        ph_status = "normal" if ph_deviation < 0.3 else ("warning" if ph_deviation < 0.5 else "critical")
        temp_status = "normal" if temp_deviation < 2.0 else ("warning" if temp_deviation < 3.5 else "critical")
        co2_status = "normal" if co2_deviation < 1.5 else ("warning" if co2_deviation < 3.0 else "critical")
        
        # Overall status
        statuses = [ph_status, temp_status, co2_status]
        if "critical" in statuses:
            overall_status = "critical"
        elif "warning" in statuses:
            overall_status = "warning"
        else:
            overall_status = "normal"
        
        # Calculate quality score (simple version)
        max_ph_dev, max_temp_dev, max_co2_dev = 1.0, 5.0, 5.0
        ph_score = max(0, 100 * (1 - ph_deviation / max_ph_dev))
        temp_score = max(0, 100 * (1 - temp_deviation / max_temp_dev))
        co2_score = max(0, 100 * (1 - co2_deviation / max_co2_dev))
        quality_score = (ph_score + temp_score + co2_score) / 3
        
        return {
            "batch_number": batch_num,
            "sample_index": idx,
            "timestamp": data_point["timestamp"],
            "actual": {
                "ph": data_point["ph"],
                "temperature": data_point["temperature"],
                "co2": data_point["co2"]
            },
            "ideal": {
                "ph": ideal_ph,
                "temperature": ideal_temp,
                "co2": ideal_co2
            },
            "deviations": {
                "ph": ph_deviation,
                "temperature": temp_deviation,
                "co2": co2_deviation
            },
            "status": {
                "ph": ph_status,
                "temperature": temp_status,
                "co2": co2_status,
                "overall": overall_status
            },
            "quality_score": quality_score,
            "batch_status": data_point.get("batch_status", "unknown"),
            "expected_quality": data_point.get("expected_quality_score", 0)
        }
    
    def set_comparison_callback(self, callback: Callable):
        """Set callback to receive comparison results"""
        self.on_comparison_callback = callback
    
    def connect(self) -> bool:
        """Connect to MQTT broker"""
        try:
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"[MQTT Subscriber] Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.client.loop_stop()
        self.client.disconnect()


# For testing
if __name__ == "__main__":
    def on_comparison(batch_num, data, comparison):
        print(f"\nBatch {batch_num} Comparison:")
        print(f"  Quality Score: {comparison['quality_score']:.1f}")
        print(f"  Status: {comparison['status']['overall']}")
    
    subscriber = MQTTSubscriber()
    subscriber.set_comparison_callback(on_comparison)
    
    print("Testing MQTT Subscriber (no broker connection)...")
    print("Subscriber initialized successfully!")
