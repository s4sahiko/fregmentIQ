"""
Golden Standard Dataset Generator for Ideal Fermentation Process
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import json
from typing import Dict, List, Tuple
from config import FERMENTATION_CONFIG


class GoldenStandardGenerator:
    """Generates the ideal fermentation process dataset"""
    
    def __init__(self):
        self.ph_range = FERMENTATION_CONFIG["ph_range"]
        self.temp_range = FERMENTATION_CONFIG["temp_range"]
        self.co2_range = FERMENTATION_CONFIG["co2_range"]
        
    def generate_ideal_fermentation(
        self, 
        duration_hours: int = 72, 
        sampling_interval_minutes: int = 30
    ) -> Dict[str, List[float]]:
        """
        Generate ideal fermentation process data
        
        Args:
            duration_hours: Total fermentation duration
            sampling_interval_minutes: Time between samples
            
        Returns:
            Dictionary with timestamps, pH, temperature, and CO2 values
        """
        num_samples = int((duration_hours * 60) / sampling_interval_minutes)
        timestamps = np.linspace(0, duration_hours, num_samples)
        
        # Generate ideal pH trajectory (decreases during fermentation)
        ph_values = self._generate_ideal_ph(timestamps)
        
        # Generate ideal temperature trajectory (slight increase then stabilize)
        temp_values = self._generate_ideal_temperature(timestamps)
        
        # Generate ideal CO2 trajectory (increases during fermentation)
        co2_values = self._generate_ideal_co2(timestamps)
        
        return {
            "timestamps": timestamps.tolist(),
            "ph": ph_values.tolist(),
            "temperature": temp_values.tolist(),
            "co2": co2_values.tolist(),
            "duration_hours": duration_hours,
            "sampling_interval_minutes": sampling_interval_minutes
        }
    
    def _generate_ideal_ph(self, timestamps: np.ndarray) -> np.ndarray:
        """
        Generate ideal pH trajectory
        pH starts around 5.5-6.0 and gradually decreases to 4.5-5.0
        """
        duration = timestamps[-1]
        
        # Initial pH
        ph_start = 5.8
        ph_end = 4.8
        
        # Sigmoid-like decrease
        ph_values = ph_start - (ph_start - ph_end) / (1 + np.exp(-0.1 * (timestamps - duration/2)))
        
        return ph_values
    
    def _generate_ideal_temperature(self, timestamps: np.ndarray) -> np.ndarray:
        """
        Generate ideal temperature trajectory
        Temperature starts around 18°C, rises to 20-22°C during active fermentation,
        then stabilizes
        """
        duration = timestamps[-1]
        
        # Base temperature
        temp_base = 18.0
        temp_peak = 21.0
        
        # Temperature rises during exponential phase, then stabilizes
        temp_rise = (temp_peak - temp_base) * np.exp(-((timestamps - 15)**2) / 200)
        temp_values = temp_base + temp_rise
        
        return temp_values
    
    def _generate_ideal_co2(self, timestamps: np.ndarray) -> np.ndarray:
        """
        Generate ideal CO2 trajectory
        CO2 starts near 0 and increases during fermentation following logistic curve
        """
        duration = timestamps[-1]
        
        # Logistic growth curve for CO2 production
        co2_max = 12.0
        growth_rate = 0.15
        midpoint = duration / 2
        
        co2_values = co2_max / (1 + np.exp(-growth_rate * (timestamps - midpoint)))
        
        return co2_values
    
    def save_to_json(self, filepath: str, duration_hours: int = 72):
        """Save golden standard dataset to JSON file"""
        data = self.generate_ideal_fermentation(duration_hours)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Golden standard dataset saved to {filepath}")
        return data


def create_golden_standard():
    """Create and save the golden standard dataset"""
    generator = GoldenStandardGenerator()
    data = generator.save_to_json(
        "data/golden_standard.json",
        duration_hours=72
    )
    return data


if __name__ == "__main__":
    # Create data directory if it doesn't exist
    import os
    os.makedirs("data", exist_ok=True)
    
    # Generate golden standard
    create_golden_standard()
    print("Golden standard dataset created successfully!")
