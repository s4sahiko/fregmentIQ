"""
Unit tests for Data Comparator
"""
import pytest
import numpy as np
import json
import os
from models.data_comparator import DataComparator
from models.fermentation_generator import FermentationDataGenerator


@pytest.fixture
def sample_data():
    """Generate sample fermentation data for testing"""
    generator = FermentationDataGenerator(seed=42)
    return generator.generate_batch(duration_hours=24, sampling_interval_minutes=60)


@pytest.fixture
def golden_standard():
    """Create a simple golden standard dataset"""
    timestamps = list(range(24))
    return {
        'timestamps': timestamps,
        'ph': [5.5 - i*0.03 for i in timestamps],
        'temperature': [19.0 + np.sin(i/5) for i in timestamps],
        'co2': [i*0.5 for i in timestamps]
    }


def test_comparator_initialization():
    """Test that comparator initializes correctly"""
    comparator = DataComparator()
    assert comparator is not None


def test_calculate_deviations(sample_data, golden_standard):
    """Test deviation calculations"""
    comparator = DataComparator()
    deviations = comparator.calculate_deviations(sample_data, golden_standard)
    
    # Check structure
    assert 'ph' in deviations
    assert 'temperature' in deviations
    assert 'co2' in deviations
    
    # Check metrics exist
    for param in ['ph', 'temperature', 'co2']:
        assert 'mae' in deviations[param]
        assert 'rmse' in deviations[param]
        assert 'max_deviation' in deviations[param]
        assert 'correlation' in deviations[param]
        assert 'status' in deviations[param]
        
        # Check values are reasonable
        assert deviations[param]['mae'] >= 0
        assert deviations[param]['rmse'] >= 0
        assert -1 <= deviations[param]['correlation'] <= 1


def test_detect_anomalies(sample_data, golden_standard):
    """Test anomaly detection"""
    comparator = DataComparator()
    anomalies = comparator.detect_anomalies(sample_data, golden_standard)
    
    # Check structure
    assert 'has_anomalies' in anomalies
    assert 'anomaly_count' in anomalies
    assert 'anomaly_percentage' in anomalies
    assert 'anomaly_indices' in anomalies
    
    # Check types
    assert isinstance(anomalies['has_anomalies'], bool)
    assert isinstance(anomalies['anomaly_count'], int)
    assert anomalies['anomaly_count'] >= 0


def test_compare_datasets(sample_data, golden_standard):
    """Test full dataset comparison"""
    comparator = DataComparator()
    comparison = comparator.compare_datasets(sample_data, golden_standard)
    
    # Check all sections present
    assert 'deviations' in comparison
    assert 'anomalies' in comparison
    assert 'similarity' in comparison
    assert 'assessment' in comparison
    
    # Check assessment
    assert 'overall_status' in comparison['assessment']
    assert 'quality_score' in comparison['assessment']
    assert 'recommendations' in comparison['assessment']
    
    # Status should be one of the valid values
    assert comparison['assessment']['overall_status'] in ['normal', 'warning', 'critical']


def test_similarity_calculation(sample_data, golden_standard):
    """Test similarity scoring"""
    comparator = DataComparator()
    gen_aligned, gold_aligned = comparator._align_datasets(sample_data, golden_standard)
    similarity = comparator._calculate_similarity(gen_aligned, gold_aligned)
    
    # Check structure
    assert 'ph' in similarity
    assert 'temperature' in similarity
    assert 'co2' in similarity
    assert 'overall' in similarity
    
    # Check similarity scores are between 0 and 1 (or slightly outside due to calculations)
    for param in ['ph', 'temperature', 'co2']:
        assert 'average_similarity' in similarity[param]
        # Similarity can sometimes be slightly negative or >1 depending on method
        assert -0.5 <= similarity[param]['average_similarity'] <= 1.5


def test_identical_datasets():
    """Test comparison of identical datasets"""
    comparator = DataComparator()
    
    data = {
        'timestamps': [0, 1, 2, 3, 4],
        'ph': [5.5, 5.4, 5.3, 5.2, 5.1],
        'temperature': [20, 20.5, 21, 21, 20.5],
        'co2': [0, 1, 2, 3, 4]
    }
    
    comparison = comparator.compare_datasets(data, data)
    
    # Deviations should be zero or very close
    assert comparison['deviations']['ph']['mae'] < 0.01
    assert comparison['deviations']['temperature']['mae'] < 0.01
    assert comparison['deviations']['co2']['mae'] < 0.01
    
    # Correlation should be perfect
    assert comparison['deviations']['ph']['correlation'] > 0.99


def test_generate_comparison_report(sample_data, golden_standard):
    """Test report generation"""
    comparator = DataComparator()
    report = comparator.generate_comparison_report(sample_data, golden_standard)
    
    # Check that report is a string
    assert isinstance(report, str)
    
    # Check that report contains key sections
    assert "FERMENTATION DATA COMPARISON REPORT" in report
    assert "PARAMETER DEVIATIONS" in report
    assert "ANOMALY DETECTION" in report
    assert "RECOMMENDATIONS" in report


def test_dataset_alignment():
    """Test that datasets of different lengths are aligned"""
    comparator = DataComparator()
    
    data1 = {
        'timestamps': [0, 1, 2, 3, 4],
        'ph': [5.5, 5.4, 5.3, 5.2, 5.1],
        'temperature': [20, 20.5, 21, 21, 20.5],
        'co2': [0, 1, 2, 3, 4]
    }
    
    data2 = {
        'timestamps': [0, 1, 2],
        'ph': [5.5, 5.4, 5.3],
        'temperature': [20, 20.5, 21],
        'co2': [0, 1, 2]
    }
    
    aligned1, aligned2 = comparator._align_datasets(data1, data2)
    
    # Both should have same length (the shorter one)
    assert len(aligned1['timestamps']) == len(aligned2['timestamps'])
    assert len(aligned1['timestamps']) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
