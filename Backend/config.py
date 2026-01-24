"""
Configuration settings for FermentIQ Backend
"""
import os
from typing import Dict, Any

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))
API_RELOAD = os.getenv("API_RELOAD", "true").lower() == "true"

# CORS Configuration
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

# Fermentation Model Parameters
FERMENTATION_CONFIG: Dict[str, Any] = {
    # Parameter ranges
    "ph_range": (4.0, 6.5),
    "temp_range": (15.0, 25.0),  # Celsius
    "co2_range": (0.0, 15.0),    # g/L
    
    # Fermentation stages (in hours)
    "lag_phase": (0, 6),
    "exponential_phase": (6, 24),
    "stationary_phase": (24, 48),
    "decline_phase": (48, 72),
    
    # Noise parameters
    "ph_noise_std": 0.05,
    "temp_noise_std": 0.3,
    "co2_noise_std": 0.2,
    
    # Sampling
    "default_duration_hours": 72,
    "default_sampling_interval_minutes": 30,
}

# Golden Standard Thresholds
GOLDEN_STANDARD_CONFIG: Dict[str, Any] = {
    # Acceptable deviation thresholds
    "ph_deviation_warning": 0.3,
    "ph_deviation_critical": 0.5,
    "temp_deviation_warning": 2.0,
    "temp_deviation_critical": 3.5,
    "co2_deviation_warning": 1.5,
    "co2_deviation_critical": 3.0,
    
    # Anomaly detection
    "anomaly_contamination": 0.1,  # Expected proportion of outliers
    "anomaly_threshold_score": -0.5,
}

# Comparison Model Settings
COMPARISON_CONFIG: Dict[str, Any] = {
    "similarity_threshold": 0.85,  # Minimum similarity score (0-1)
    "dtw_window": 10,  # Dynamic Time Warping window size
    "enable_visualization": False,  # Set to True for debugging
}

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# SMS Alert Configuration
SMS_CONFIG: Dict[str, Any] = {
    "enabled": True,  # Set to True to enable console logging of SMS
    "provider": "twilio",  # Options: "console", "twilio"
    "target_numbers": {
        "default": "--",
        # You can add specific numbers for specific batches if needed
        # "1": "+1987654321", 
    },
    
    # Twilio Credentials (required if provider is "twilio")
    "twilio_sid": os.getenv("TWILIO_ACCOUNT_SID", "--"),
    "twilio_auth_token": os.getenv("TWILIO_AUTH_TOKEN"),
    "twilio_from_number": os.getenv("TWILIO_FROM_NUMBER"),
}
