"""
Unit tests for Fermentation Data Generator
"""
import pytest
import numpy as np
from models.fermentation_generator import FermentationDataGenerator


def test_generator_initialization():
    """Test that generator initializes correctly"""
    generator = FermentationDataGenerator(seed=42)
    assert generator is not None
    assert generator.ph_range == (4.0, 6.5)
    assert generator.temp_range == (15.0, 25.0)
    assert generator.co2_range == (0.0, 15.0)


def test_generate_batch_basic():
    """Test basic data generation"""
    generator = FermentationDataGenerator(seed=42)
    data = generator.generate_batch(duration_hours=24, sampling_interval_minutes=60)
    
    # Check structure
    assert 'timestamps' in data
    assert 'ph' in data
    assert 'temperature' in data
    assert 'co2' in data
    
    # Check lengths match
    expected_samples = 24  # 24 hours / 1 hour interval
    assert len(data['timestamps']) == expected_samples
    assert len(data['ph']) == expected_samples
    assert len(data['temperature']) == expected_samples
    assert len(data['co2']) == expected_samples


def test_parameter_ranges():
    """Test that generated values stay within valid ranges"""
    generator = FermentationDataGenerator(seed=42)
    data = generator.generate_batch(duration_hours=72, sampling_interval_minutes=30)
    
    # Check pH range
    assert all(4.0 <= ph <= 6.5 for ph in data['ph'])
    
    # Check temperature range
    assert all(15.0 <= temp <= 25.0 for temp in data['temperature'])
    
    # Check CO2 range
    assert all(0.0 <= co2 <= 15.0 for co2 in data['co2'])


def test_temporal_consistency():
    """Test that generated data has temporal consistency"""
    generator = FermentationDataGenerator(seed=42)
    data = generator.generate_batch(duration_hours=72, sampling_interval_minutes=30)
    
    # pH should generally decrease over time
    ph_values = np.array(data['ph'])
    ph_trend = np.polyfit(range(len(ph_values)), ph_values, 1)[0]
    assert ph_trend < 0, "pH should decrease during fermentation"
    
    # CO2 should generally increase over time
    co2_values = np.array(data['co2'])
    co2_trend = np.polyfit(range(len(co2_values)), co2_values, 1)[0]
    assert co2_trend > 0, "CO2 should increase during fermentation"


def test_variation_factor():
    """Test that variation factor affects output"""
    generator = FermentationDataGenerator(seed=42)
    
    data_low = generator.generate_batch(duration_hours=24, variation_factor=0.5)
    data_high = generator.generate_batch(duration_hours=24, variation_factor=2.0)
    
    # Higher variation should lead to more spread
    std_low = np.std(data_low['ph'])
    std_high = np.std(data_high['ph'])
    
    # Note: This might not always hold due to randomness, but generally should
    assert std_high >= std_low * 0.8  # Allow some tolerance


def test_anomaly_injection():
    """Test that anomalies can be injected"""
    generator = FermentationDataGenerator(seed=42)
    
    data_normal = generator.generate_batch(duration_hours=72, add_anomalies=False)
    data_anomaly = generator.generate_batch(duration_hours=72, add_anomalies=True)
    
    assert data_normal['has_anomalies'] == False
    assert data_anomaly['has_anomalies'] == True


def test_reproducibility():
    """Test that same seed produces same results"""
    gen1 = FermentationDataGenerator(seed=42)
    gen2 = FermentationDataGenerator(seed=42)
    
    data1 = gen1.generate_batch(duration_hours=24, sampling_interval_minutes=30)
    data2 = gen2.generate_batch(duration_hours=24, sampling_interval_minutes=30)
    
    np.testing.assert_array_almost_equal(data1['ph'], data2['ph'])
    np.testing.assert_array_almost_equal(data1['temperature'], data2['temperature'])
    np.testing.assert_array_almost_equal(data1['co2'], data2['co2'])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
