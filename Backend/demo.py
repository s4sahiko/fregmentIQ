"""
Demo script showing how to use the FermentIQ AI models
"""
import requests
import json

BASE_URL = "http://localhost:8000"

print("=" * 70)
print("FermentIQ AI Models - Demo")
print("=" * 70)

# 1. Generate fermentation data
print("\n1. Generating fermentation data...")
generate_payload = {
    "duration_hours": 72,
    "sampling_interval_minutes": 30,
    "variation_factor": 1.0,
    "add_anomalies": False
}

response = requests.post(f"{BASE_URL}/api/generate", json=generate_payload)
generated_data = response.json()

print(f"   ✓ Generated {len(generated_data['timestamps'])} data points")
print(f"   ✓ Duration: {generated_data['duration_hours']} hours")
print(f"   ✓ pH range: {min(generated_data['ph']):.2f} - {max(generated_data['ph']):.2f}")
print(f"   ✓ Temperature range: {min(generated_data['temperature']):.2f}°C - {max(generated_data['temperature']):.2f}°C")
print(f"   ✓ CO2 range: {min(generated_data['co2']):.2f} - {max(generated_data['co2']):.2f} g/L")

# 2. Use the combined endpoint (easier)
print("\n2. Using Generate & Compare endpoint...")
response = requests.post(f"{BASE_URL}/api/generate-and-compare", json=generate_payload)
result = response.json()

comparison = result['comparison']
assessment = comparison['assessment']

print(f"\n   COMPARISON RESULTS:")
print(f"   {'='*60}")
print(f"   Overall Status: {assessment['overall_status'].upper()}")
print(f"   Quality Score: {assessment['quality_score']:.1f}/100")
print(f"   Message: {assessment['message']}")

print(f"\n   PARAMETER DEVIATIONS:")
for param in ['ph', 'temperature', 'co2']:
    dev = comparison['deviations'][param]
    print(f"   {param.upper()}:")
    print(f"     - Status: {dev['status']}")
    print(f"     - MAE: {dev['mae']:.3f}")
    print(f"     - Correlation: {dev['correlation']:.3f}")

print(f"\n   ANOMALY DETECTION:")
print(f"     - Anomalies Found: {comparison['anomalies']['has_anomalies']}")
print(f"     - Anomaly Count: {comparison['anomalies']['anomaly_count']}")
print(f"     - Anomaly Percentage: {comparison['anomalies']['anomaly_percentage']:.1f}%")

print(f"\n   RECOMMENDATIONS:")
for i, rec in enumerate(assessment['recommendations'], 1):
    print(f"     {i}. {rec}")

# 3. Generate data with anomalies
print(f"\n{'='*70}")
print("3. Generating data WITH anomalies...")
anomaly_payload = {
    "duration_hours": 72,
    "sampling_interval_minutes": 30,
    "variation_factor": 1.5,
    "add_anomalies": True
}

response = requests.post(f"{BASE_URL}/api/generate-and-compare", json=anomaly_payload)
result = response.json()

comparison = result['comparison']
assessment = comparison['assessment']

print(f"\n   COMPARISON RESULTS (with anomalies):")
print(f"   {'='*60}")
print(f"   Overall Status: {assessment['overall_status'].upper()}")
print(f"   Quality Score: {assessment['quality_score']:.1f}/100")
print(f"   Anomalies Found: {comparison['anomalies']['has_anomalies']}")
print(f"   Anomaly Count: {comparison['anomalies']['anomaly_count']}")

if comparison['anomalies']['has_anomalies']:
    print(f"\n   ANOMALY DETAILS:")
    for detail in comparison['anomalies']['anomaly_details'][:3]:  # Show first 3
        print(f"     - Time: {detail['timestamp']:.1f}h")
        print(f"       Types: {', '.join(detail['types'])}")
        print(f"       pH deviation: {detail['deviations']['ph']:.2f}")
        print(f"       Temp deviation: {detail['deviations']['temperature']:.2f}°C")
        print(f"       CO2 deviation: {detail['deviations']['co2']:.2f} g/L")

print(f"\n   RECOMMENDATIONS:")
for i, rec in enumerate(assessment['recommendations'], 1):
    print(f"     {i}. {rec}")

print(f"\n{'='*70}")
print("Demo completed successfully! ✓")
print(f"{'='*70}")
print("\nAPI Documentation: http://localhost:8000/docs")
