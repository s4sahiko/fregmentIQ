"""
Demo script for testing all 4 batch profiles
"""
import requests
import json

BASE_URL = "http://localhost:8000"

print("=" * 80)
print("FermentIQ - Batch Profile Demo")
print("=" * 80)
print()

# Test all 4 batch profiles
batch_descriptions = {
    1: "Batch 1: 90% Match - Acceptable (degrades after 48 hours)",
    2: "Batch 2: 100% Match - Perfect",
    3: "Batch 3: <75% Match - Failed",
    4: "Batch 4: 85% Match - Concerning"
}

for batch_num in range(1, 5):
    print(f"\n{'='*80}")
    print(f"{batch_descriptions[batch_num]}")
    print(f"{'='*80}\n")
    
    # Generate batch profile
    print(f"Generating Batch {batch_num}...")
    response = requests.post(
        f"{BASE_URL}/api/generate-batch-profile",
        params={
            "batch_number": batch_num,
            "duration_hours": 72,
            "sampling_interval_minutes": 30
        }
    )
    
    batch_data = response.json()
    
    print(f"✓ Batch Number: {batch_data['batch_number']}")
    print(f"✓ Status: {batch_data['batch_status'].upper()}")
    print(f"✓ Expected Quality: {batch_data['expected_quality_score']}%")
    print(f"✓ Description: {batch_data['description']}")
    print(f"✓ Samples Generated: {len(batch_data['timestamps'])}")
    
    # Show data ranges
    print(f"\nData Ranges:")
    print(f"  pH: {min(batch_data['ph']):.2f} - {max(batch_data['ph']):.2f}")
    print(f"  Temperature: {min(batch_data['temperature']):.2f}°C - {max(batch_data['temperature']):.2f}°C")
    print(f"  CO2: {min(batch_data['co2']):.2f} - {max(batch_data['co2']):.2f} g/L")
    
    # Compare with golden standard
    print(f"\nComparing with Golden Standard...")
    compare_response = requests.post(
        f"{BASE_URL}/api/compare",
        json={
            "generated_data": {
                "timestamps": batch_data['timestamps'],
                "ph": batch_data['ph'],
                "temperature": batch_data['temperature'],
                "co2": batch_data['co2']
            },
            "use_golden_standard": True
        }
    )
    
    comparison = compare_response.json()
    assessment = comparison['assessment']
    
    print(f"\n{'─'*80}")
    print(f"COMPARISON RESULTS:")
    print(f"{'─'*80}")
    print(f"  Overall Status: {assessment['overall_status'].upper()}")
    print(f"  Actual Quality Score: {assessment['quality_score']:.1f}/100")
    print(f"  Expected Quality Score: {batch_data['expected_quality_score']}/100")
    print(f"  Difference: {abs(assessment['quality_score'] - batch_data['expected_quality_score']):.1f} points")
    
    print(f"\n  Parameter Deviations:")
    for param in ['ph', 'temperature', 'co2']:
        dev = comparison['deviations'][param]
        print(f"    {param.upper()}: {dev['status'].upper()} (MAE: {dev['mae']:.3f}, Correlation: {dev['correlation']:.3f})")
    
    print(f"\n  Anomaly Detection:")
    print(f"    Anomalies Found: {comparison['anomalies']['has_anomalies']}")
    print(f"    Anomaly Count: {comparison['anomalies']['anomaly_count']}")
    print(f"    Anomaly Percentage: {comparison['anomalies']['anomaly_percentage']:.1f}%")
    
    print(f"\n  Recommendations:")
    for i, rec in enumerate(assessment['recommendations'], 1):
        print(f"    {i}. {rec}")
    
    # Special analysis for Batch 1 (degradation after 48 hours)
    if batch_num == 1:
        print(f"\n  Special Analysis - Late Degradation:")
        # Check pH values before and after 48 hours
        timestamps = batch_data['timestamps']
        ph_values = batch_data['ph']
        
        before_48_idx = [i for i, t in enumerate(timestamps) if t < 48]
        after_48_idx = [i for i, t in enumerate(timestamps) if t >= 48]
        
        if before_48_idx and after_48_idx:
            avg_ph_before = sum(ph_values[i] for i in before_48_idx) / len(before_48_idx)
            avg_ph_after = sum(ph_values[i] for i in after_48_idx) / len(after_48_idx)
            
            print(f"    Average pH before 48h: {avg_ph_before:.3f}")
            print(f"    Average pH after 48h: {avg_ph_after:.3f}")
            print(f"    pH change: {(avg_ph_after - avg_ph_before):.3f} (↑ indicates degradation)")

print(f"\n{'='*80}")
print("Batch Profile Demo Completed!")
print(f"{'='*80}\n")

# Summary table
print("\nSUMMARY TABLE:")
print(f"{'─'*80}")
print(f"{'Batch':<10} {'Status':<15} {'Expected':<12} {'Description':<43}")
print(f"{'─'*80}")
print(f"{'Batch 1':<10} {'Acceptable':<15} {'90%':<12} {'Good, degrades after 48h':<43}")
print(f"{'Batch 2':<10} {'Perfect':<15} {'100%':<12} {'Matches golden standard':<43}")
print(f"{'Batch 3':<10} {'Failed':<15} {'<75%':<12} {'Significant deviations':<43}")
print(f"{'Batch 4':<10} {'Concerning':<15} {'85%':<12} {'Moderate deviations':<43}")
print(f"{'─'*80}\n")

print("API Documentation: http://localhost:8000/docs")
