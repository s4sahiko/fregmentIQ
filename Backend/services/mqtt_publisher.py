"""
MQTT Publisher Service - Generates and publishes fermentation data
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
import threading
from typing import Dict, Callable, Optional
import paho.mqtt.client as mqtt

from models.fermentation_generator import FermentationDataGenerator
from config import FERMENTATION_CONFIG


class MQTTPublisher:
    """
    Publishes fermentation batch data to MQTT topics
    """
    
    def __init__(
        self,
        broker_host: str = "localhost",
        broker_port: int = 1883,
        client_id: str = "fermentiq_publisher"
    ):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client_id = client_id
        
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        
        self.generator = FermentationDataGenerator()
        self.is_running = False
        self.threads: Dict[int, threading.Thread] = {}
        
        # Store batch data for each batch
        self.batch_data: Dict[int, Dict] = {}
        self.current_index: Dict[int, int] = {1: 0, 2: 0, 3: 0, 4: 0}
    
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            print(f"[MQTT Publisher] Connected to broker at {self.broker_host}:{self.broker_port}")
        else:
            print(f"[MQTT Publisher] Connection failed with code {rc}")
    
    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        print(f"[MQTT Publisher] Disconnected from broker (code: {rc})")
    
    def connect(self) -> bool:
        """Connect to MQTT broker"""
        try:
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"[MQTT Publisher] Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.is_running = False
        self.client.loop_stop()
        self.client.disconnect()
    
    def generate_all_batches(self):
        """Pre-generate data for all 4 batches"""
        for batch_num in range(1, 5):
            self.batch_data[batch_num] = self.generator.generate_batch_profile(
                batch_number=batch_num,
                duration_hours=72,
                sampling_interval_minutes=30
            )
            print(f"[MQTT Publisher] Generated data for Batch {batch_num}")
    
    def publish_batch_point(self, batch_num: int) -> Dict:
        """Publish a single data point for a batch"""
        if batch_num not in self.batch_data:
            self.generate_all_batches()
        
        batch = self.batch_data[batch_num]
        idx = self.current_index[batch_num]
        
        # Get current data point
        data_point = {
            "batch_number": batch_num,
            "batch_status": batch["batch_status"],
            "expected_quality_score": batch["expected_quality_score"],
            "timestamp": batch["timestamps"][idx],
            "ph": batch["ph"][idx],
            "temperature": batch["temperature"][idx],
            "co2": batch["co2"][idx],
            "sample_index": idx,
            "total_samples": len(batch["timestamps"])
        }
        
        # Publish to MQTT topic
        topic = f"fermentiq/batch/{batch_num}/data"
        payload = json.dumps(data_point)
        
        result = self.client.publish(topic, payload, qos=1)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"[MQTT Publisher] Published Batch {batch_num} point {idx}: pH={data_point['ph']:.2f}, Temp={data_point['temperature']:.1f}°C, CO2={data_point['co2']:.2f}")
        
        # Increment index (loop back to 0 at end)
        self.current_index[batch_num] = (idx + 1) % len(batch["timestamps"])
        
        return data_point
    
    def start_publishing(self, interval_seconds: float = 2.0, on_publish: Optional[Callable] = None):
        """Start publishing data for all batches at regular intervals"""
        self.is_running = True
        self.generate_all_batches()
        
        def publish_loop():
            while self.is_running:
                for batch_num in range(1, 5):
                    if not self.is_running:
                        break
                    data_point = self.publish_batch_point(batch_num)
                    if on_publish:
                        on_publish(batch_num, data_point)
                time.sleep(interval_seconds)
        
        self.publish_thread = threading.Thread(target=publish_loop, daemon=True)
        self.publish_thread.start()
        print(f"[MQTT Publisher] Started publishing every {interval_seconds}s")
    
    def stop_publishing(self):
        """Stop publishing data"""
        self.is_running = False
        print("[MQTT Publisher] Stopped publishing")


# For testing
if __name__ == "__main__":
    publisher = MQTTPublisher()
    
    # For testing without a real broker, just generate and print
    print("Testing MQTT Publisher (no broker connection)...")
    publisher.generate_all_batches()
    
    for batch_num in range(1, 5):
        batch = publisher.batch_data[batch_num]
        print(f"\nBatch {batch_num} ({batch['batch_status']}):")
        print(f"  Samples: {len(batch['timestamps'])}")
        print(f"  pH range: {min(batch['ph']):.2f} - {max(batch['ph']):.2f}")
