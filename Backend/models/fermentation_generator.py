"""
Fermentation Data Generation Model using LSTM
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from typing import Dict, List, Tuple, Optional
from config import FERMENTATION_CONFIG


class FermentationDataGenerator:
    """
    AI Model for generating realistic fermentation process data
    Uses pattern-based generation with temporal dependencies
    """
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the fermentation data generator
        
        Args:
            seed: Random seed for reproducibility
        """
        if seed is not None:
            np.random.seed(seed)
        
        self.ph_range = FERMENTATION_CONFIG["ph_range"]
        self.temp_range = FERMENTATION_CONFIG["temp_range"]
        self.co2_range = FERMENTATION_CONFIG["co2_range"]
        
        self.ph_noise = FERMENTATION_CONFIG["ph_noise_std"]
        self.temp_noise = FERMENTATION_CONFIG["temp_noise_std"]
        self.co2_noise = FERMENTATION_CONFIG["co2_noise_std"]
    
    def generate_batch(
        self,
        duration_hours: int = 72,
        sampling_interval_minutes: int = 30,
        variation_factor: float = 1.0,
        add_anomalies: bool = False
    ) -> Dict[str, List[float]]:
        """
        Generate a batch of fermentation data
        
        Args:
            duration_hours: Total duration of fermentation
            sampling_interval_minutes: Time between samples
            variation_factor: Multiplier for noise (1.0 = normal, >1.0 = more variation)
            add_anomalies: Whether to inject anomalies into the data
            
        Returns:
            Dictionary containing timestamps and parameter values
        """
        num_samples = int((duration_hours * 60) / sampling_interval_minutes)
        timestamps = np.linspace(0, duration_hours, num_samples)
        
        # Generate base trajectories
        ph_values = self._generate_ph_trajectory(timestamps, variation_factor)
        temp_values = self._generate_temp_trajectory(timestamps, variation_factor)
        co2_values = self._generate_co2_trajectory(timestamps, variation_factor)
        
        # Add realistic sensor noise
        ph_values = self._add_realistic_noise(ph_values, self.ph_noise * variation_factor)
        temp_values = self._add_realistic_noise(temp_values, self.temp_noise * variation_factor)
        co2_values = self._add_realistic_noise(co2_values, self.co2_noise * variation_factor)
        
        # Optionally add anomalies
        if add_anomalies:
            ph_values, temp_values, co2_values = self._inject_anomalies(
                timestamps, ph_values, temp_values, co2_values
            )
        
        # Ensure values stay within valid ranges
        ph_values = np.clip(ph_values, self.ph_range[0], self.ph_range[1])
        temp_values = np.clip(temp_values, self.temp_range[0], self.temp_range[1])
        co2_values = np.clip(co2_values, self.co2_range[0], self.co2_range[1])
        
        return {
            "timestamps": timestamps.tolist(),
            "ph": ph_values.tolist(),
            "temperature": temp_values.tolist(),
            "co2": co2_values.tolist(),
            "duration_hours": duration_hours,
            "sampling_interval_minutes": sampling_interval_minutes,
            "variation_factor": variation_factor,
            "has_anomalies": add_anomalies
        }
    
    def _generate_ph_trajectory(self, timestamps: np.ndarray, variation: float) -> np.ndarray:
        """
        Generate pH trajectory with fermentation stages
        pH decreases as fermentation progresses due to acid production
        """
        duration = timestamps[-1]
        
        # Random initial pH within range
        ph_start = np.random.uniform(5.6, 6.2)
        ph_end = np.random.uniform(4.5, 5.2)
        
        # Add variation to the curve shape
        curve_steepness = np.random.uniform(0.08, 0.12) * variation
        curve_midpoint = duration * np.random.uniform(0.4, 0.6)
        
        # Sigmoid decrease
        ph_values = ph_start - (ph_start - ph_end) / (
            1 + np.exp(-curve_steepness * (timestamps - curve_midpoint))
        )
        
        return ph_values
    
    def _generate_temp_trajectory(self, timestamps: np.ndarray, variation: float) -> np.ndarray:
        """
        Generate temperature trajectory
        Temperature rises during active fermentation due to metabolic heat
        """
        duration = timestamps[-1]
        
        # Random base temperature
        temp_base = np.random.uniform(17.0, 19.0)
        temp_peak = temp_base + np.random.uniform(2.0, 4.0) * variation
        
        # Peak during exponential phase
        peak_time = np.random.uniform(12, 20)
        peak_width = np.random.uniform(150, 250)
        
        temp_rise = (temp_peak - temp_base) * np.exp(-((timestamps - peak_time)**2) / peak_width)
        temp_values = temp_base + temp_rise
        
        return temp_values
    
    def _generate_co2_trajectory(self, timestamps: np.ndarray, variation: float) -> np.ndarray:
        """
        Generate CO2 trajectory
        CO2 production follows logistic growth during fermentation
        """
        duration = timestamps[-1]
        
        # Random CO2 parameters
        co2_max = np.random.uniform(10.0, 14.0) * variation
        growth_rate = np.random.uniform(0.12, 0.18)
        midpoint = duration * np.random.uniform(0.45, 0.55)
        
        # Logistic growth
        co2_values = co2_max / (1 + np.exp(-growth_rate * (timestamps - midpoint)))
        
        return co2_values
    
    def _add_realistic_noise(self, values: np.ndarray, noise_std: float) -> np.ndarray:
        """
        Add realistic sensor noise with temporal correlation
        Uses moving average to create correlated noise
        """
        # White noise
        noise = np.random.normal(0, noise_std, len(values))
        
        # Apply moving average for temporal correlation
        window_size = 3
        kernel = np.ones(window_size) / window_size
        correlated_noise = np.convolve(noise, kernel, mode='same')
        
        return values + correlated_noise
    
    def _inject_anomalies(
        self,
        timestamps: np.ndarray,
        ph: np.ndarray,
        temp: np.ndarray,
        co2: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Inject realistic anomalies into the data
        Simulates contamination, temperature spikes, etc.
        """
        duration = timestamps[-1]
        
        # Randomly choose anomaly type
        anomaly_type = np.random.choice(['ph_spike', 'temp_spike', 'stalled_fermentation'])
        
        if anomaly_type == 'ph_spike':
            # Sudden pH increase (contamination)
            spike_time = np.random.uniform(duration * 0.3, duration * 0.7)
            spike_idx = np.argmin(np.abs(timestamps - spike_time))
            ph[spike_idx:spike_idx+5] += np.random.uniform(0.5, 1.0)
            
        elif anomaly_type == 'temp_spike':
            # Temperature spike (cooling failure)
            spike_time = np.random.uniform(duration * 0.2, duration * 0.8)
            spike_idx = np.argmin(np.abs(timestamps - spike_time))
            temp[spike_idx:spike_idx+10] += np.random.uniform(3.0, 5.0)
            
        elif anomaly_type == 'stalled_fermentation':
            # Fermentation stalls (CO2 production stops)
            stall_time = np.random.uniform(duration * 0.4, duration * 0.6)
            stall_idx = np.argmin(np.abs(timestamps - stall_time))
            co2[stall_idx:] = co2[stall_idx] + np.random.normal(0, 0.1, len(co2) - stall_idx)
        
        return ph, temp, co2
    
    def generate_batch_profile(
        self,
        batch_number: int,
        duration_hours: int = 72,
        sampling_interval_minutes: int = 30
    ) -> Dict[str, any]:
        """
        Generate predefined batch profiles with specific quality targets
        
        Args:
            batch_number: 1-4, each with different quality characteristics
                1: 90% match - Acceptable (degrades after 50 hours)
                2: 100% match - Perfect (matches golden standard throughout)
                3: <80% match - Failed (poor quality throughout)
                4: 85% match - Concerning (moderate deviations)
            duration_hours: Total fermentation duration
            sampling_interval_minutes: Time between samples
            
        Returns:
            Dictionary with fermentation data and batch metadata
        """
        num_samples = int((duration_hours * 60) / sampling_interval_minutes)
        timestamps = np.linspace(0, duration_hours, num_samples)
        
        # Load golden standard parameters for reference
        from data.golden_standard import GoldenStandardGenerator
        golden_gen = GoldenStandardGenerator()
        golden_data = golden_gen.generate_ideal_fermentation(duration_hours, sampling_interval_minutes)
        
        golden_ph = np.array(golden_data['ph'])
        golden_temp = np.array(golden_data['temperature'])
        golden_co2 = np.array(golden_data['co2'])
        
        if batch_number == 1:
            # Batch 1: 92% match - Acceptable with late degradation (55 hours)
            ph_values, temp_values, co2_values = self._generate_batch_1(
                timestamps, golden_ph, golden_temp, golden_co2
            )
            status = "acceptable"
            expected_quality = 92
            description = "Good fermentation with slight degradation after 55 hours"
            
        elif batch_number == 2:
            # Batch 2: 100% match - Perfect
            ph_values, temp_values, co2_values = self._generate_batch_2(
                timestamps, golden_ph, golden_temp, golden_co2
            )
            status = "perfect"
            expected_quality = 100
            description = "Perfect fermentation matching golden standard"
            
        elif batch_number == 3:
            # Batch 3: <75% match - Failed
            ph_values, temp_values, co2_values = self._generate_batch_3(
                timestamps, golden_ph, golden_temp, golden_co2
            )
            status = "failed"
            expected_quality = 70
            description = "Failed fermentation with significant deviations"
            
        elif batch_number == 4:
            # Batch 4: 85% match - Concerning
            ph_values, temp_values, co2_values = self._generate_batch_4(
                timestamps, golden_ph, golden_temp, golden_co2
            )
            status = "concerning"
            expected_quality = 85
            description = "Concerning fermentation with moderate deviations throughout"
            
        else:
            raise ValueError(f"Invalid batch_number: {batch_number}. Must be 1-4.")
        
        # Ensure values stay within valid ranges
        ph_values = np.clip(ph_values, self.ph_range[0], self.ph_range[1])
        temp_values = np.clip(temp_values, self.temp_range[0], self.temp_range[1])
        co2_values = np.clip(co2_values, self.co2_range[0], self.co2_range[1])
        
        return {
            "batch_number": batch_number,
            "batch_status": status,
            "expected_quality_score": expected_quality,
            "description": description,
            "timestamps": timestamps.tolist(),
            "ph": ph_values.tolist(),
            "temperature": temp_values.tolist(),
            "co2": co2_values.tolist(),
            "duration_hours": duration_hours,
            "sampling_interval_minutes": sampling_interval_minutes
        }
    
    def _generate_batch_1(
        self,
        timestamps: np.ndarray,
        golden_ph: np.ndarray,
        golden_temp: np.ndarray,
        golden_co2: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Batch 1: 92% match - Acceptable
        Perfect until 55 hours, then very slight degradation
        Target: 90-94% quality (Acceptable/Blue)
        """
        duration = timestamps[-1]
        
        # Start with golden standard values with minimal noise
        ph = golden_ph.copy() + np.random.normal(0, 0.015, len(golden_ph))
        temp = golden_temp.copy() + np.random.normal(0, 0.12, len(golden_temp))
        co2 = golden_co2.copy() + np.random.normal(0, 0.08, len(golden_co2))
        
        # Add very slight degradation after 55 hours (reduced from 50)
        degradation_start_time = 55.0
        for i, t in enumerate(timestamps):
            if t >= degradation_start_time:
                # Progressive but MILD degradation
                degradation_factor = (t - degradation_start_time) / (duration - degradation_start_time)
                
                # pH rises very slightly (reduced from 0.25 to 0.12)
                ph[i] += degradation_factor * 0.12
                
                # Temperature becomes slightly less stable (reduced variation)
                temp[i] += degradation_factor * np.random.uniform(-0.4, 0.6)
                
                # CO2 production slows down very slightly (reduced from 0.1 to 0.05)
                co2[i] *= (1 - degradation_factor * 0.05)
        
        return ph, temp, co2
    
    def _generate_batch_2(
        self,
        timestamps: np.ndarray,
        golden_ph: np.ndarray,
        golden_temp: np.ndarray,
        golden_co2: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Batch 2: 100% match - Perfect fermentation
        Matches golden standard almost exactly throughout
        """
        # Very minimal noise to simulate perfect conditions
        ph = golden_ph.copy() + np.random.normal(0, 0.01, len(golden_ph))
        temp = golden_temp.copy() + np.random.normal(0, 0.1, len(golden_temp))
        co2 = golden_co2.copy() + np.random.normal(0, 0.05, len(golden_co2))
        
        return ph, temp, co2
    
    def _generate_batch_3(
        self,
        timestamps: np.ndarray,
        golden_ph: np.ndarray,
        golden_temp: np.ndarray,
        golden_co2: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Batch 3: <80% match - Failed fermentation
        Perfect until 40 hours, then significant degradation
        """
        duration = timestamps[-1]
        
        # Start matching golden standard well
        ph = golden_ph.copy() + np.random.normal(0, 0.02, len(golden_ph))
        temp = golden_temp.copy() + np.random.normal(0, 0.15, len(golden_temp))
        co2 = golden_co2.copy() + np.random.normal(0, 0.1, len(golden_co2))
        
        # Add major deviations after 40 hours
        degradation_start_time = 40.0
        for i, t in enumerate(timestamps):
            if t >= degradation_start_time:
                degradation_factor = (t - degradation_start_time) / (duration - degradation_start_time)
                
                # pH deviation (too high)
                ph[i] += degradation_factor * 0.6 + np.random.uniform(0, 0.1)
                
                # Temperature control loss
                temp[i] += degradation_factor * np.random.uniform(-3.0, 4.0)
                
                # CO2 production stalls significantly
                co2[i] *= (1 - degradation_factor * 0.4)
        
        return ph, temp, co2
    
    def _generate_batch_4(
        self,
        timestamps: np.ndarray,
        golden_ph: np.ndarray,
        golden_temp: np.ndarray,
        golden_co2: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Batch 4: 85% match - Concerning
        Moderate deviations throughout, more noticeable after 50 hours
        Target: 80-89% quality (Concerning/Yellow)
        """
        duration = timestamps[-1]
        
        # Start with slightly more noise than Batch 1
        ph = golden_ph.copy() + np.random.normal(0, 0.025, len(golden_ph))
        temp = golden_temp.copy() + np.random.normal(0, 0.2, len(golden_temp))
        co2 = golden_co2.copy() + np.random.normal(0, 0.12, len(golden_co2))
        
        # Add moderate deviations after 50 hours (earlier than Batch 1)
        degradation_start_time = 50.0
        for i, t in enumerate(timestamps):
            if t >= degradation_start_time:
                degradation_factor = (t - degradation_start_time) / (duration - degradation_start_time)
                
                # pH deviation - moderate (reduced from 0.3 to 0.22)
                ph[i] += degradation_factor * 0.22
                
                # Temperature variation - noticeable but not extreme (reduced from 1.5 to 1.0)
                temp[i] += np.sin(t) * degradation_factor * 1.0
                
                # CO2 production moderate drop (reduced from 0.15 to 0.12)
                co2[i] *= (1 - degradation_factor * 0.12)
        
        return ph, temp, co2
    
    def simulate_fermentation_stages(
        self,
        duration_hours: int = 72,
        sampling_interval_minutes: int = 30
    ) -> Dict[str, any]:
        """
        Generate data with explicit fermentation stage markers
        
        Returns:
            Data dictionary with stage annotations
        """
        data = self.generate_batch(duration_hours, sampling_interval_minutes)
        
        # Add stage markers
        stages = self._identify_stages(data["timestamps"])
        data["stages"] = stages
        
        return data
    
    def _identify_stages(self, timestamps: List[float]) -> List[Dict[str, any]]:
        """Identify fermentation stages based on time"""
        stages = []
        
        for t in timestamps:
            if t < 6:
                stage = "lag"
            elif t < 24:
                stage = "exponential"
            elif t < 48:
                stage = "stationary"
            else:
                stage = "decline"
            
            stages.append({"time": t, "stage": stage})
        
        return stages


if __name__ == "__main__":
    # Test the generator
    generator = FermentationDataGenerator(seed=42)
    
    # Generate normal data
    normal_data = generator.generate_batch(duration_hours=72, sampling_interval_minutes=30)
    print("Generated normal fermentation data:")
    print(f"  Samples: {len(normal_data['timestamps'])}")
    print(f"  pH range: {min(normal_data['ph']):.2f} - {max(normal_data['ph']):.2f}")
    print(f"  Temp range: {min(normal_data['temperature']):.2f} - {max(normal_data['temperature']):.2f}")
    print(f"  CO2 range: {min(normal_data['co2']):.2f} - {max(normal_data['co2']):.2f}")
    
    # Generate data with anomalies
    anomaly_data = generator.generate_batch(
        duration_hours=72,
        sampling_interval_minutes=30,
        add_anomalies=True
    )
    print("\nGenerated anomalous fermentation data:")
    print(f"  Has anomalies: {anomaly_data['has_anomalies']}")
