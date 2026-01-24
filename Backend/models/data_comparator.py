"""
Data Comparison Model for Fermentation Process Analysis
Compares generated data with golden standard dataset
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from typing import Dict, List, Tuple, Optional
from sklearn.ensemble import IsolationForest
from scipy import stats
from scipy.spatial.distance import euclidean
from dtaidistance import dtw
import json

from config import GOLDEN_STANDARD_CONFIG, COMPARISON_CONFIG


class DataComparator:
    """
    AI Model for comparing fermentation data against golden standard
    Uses statistical analysis and anomaly detection
    """
    
    def __init__(self, golden_standard_path: Optional[str] = None):
        """
        Initialize the data comparator
        
        Args:
            golden_standard_path: Path to golden standard JSON file
        """
        self.golden_standard = None
        if golden_standard_path:
            self.load_golden_standard(golden_standard_path)
        
        self.ph_warning = GOLDEN_STANDARD_CONFIG["ph_deviation_warning"]
        self.ph_critical = GOLDEN_STANDARD_CONFIG["ph_deviation_critical"]
        self.temp_warning = GOLDEN_STANDARD_CONFIG["temp_deviation_warning"]
        self.temp_critical = GOLDEN_STANDARD_CONFIG["temp_deviation_critical"]
        self.co2_warning = GOLDEN_STANDARD_CONFIG["co2_deviation_warning"]
        self.co2_critical = GOLDEN_STANDARD_CONFIG["co2_deviation_critical"]
        
        self.similarity_threshold = COMPARISON_CONFIG["similarity_threshold"]
    
    def load_golden_standard(self, filepath: str):
        """Load golden standard dataset from JSON file"""
        with open(filepath, 'r') as f:
            self.golden_standard = json.load(f)
        print(f"Loaded golden standard from {filepath}")
    
    def compare_datasets(
        self,
        generated_data: Dict[str, List[float]],
        golden_standard: Optional[Dict[str, List[float]]] = None
    ) -> Dict[str, any]:
        """
        Perform comprehensive comparison between generated and golden standard data
        
        Args:
            generated_data: Generated fermentation data
            golden_standard: Golden standard data (uses loaded if not provided)
            
        Returns:
            Comprehensive comparison report
        """
        if golden_standard is None:
            golden_standard = self.golden_standard
        
        if golden_standard is None:
            raise ValueError("No golden standard data available")
        
        # Align datasets (interpolate if different lengths)
        gen_aligned, gold_aligned = self._align_datasets(generated_data, golden_standard)
        
        # Calculate deviations
        deviations = self.calculate_deviations(gen_aligned, gold_aligned)
        
        # Detect anomalies
        anomalies = self.detect_anomalies(gen_aligned, gold_aligned)
        
        # Calculate similarity scores
        similarity = self._calculate_similarity(gen_aligned, gold_aligned)
        
        # Generate overall assessment
        assessment = self._generate_assessment(deviations, anomalies, similarity)
        
        # Compile comprehensive report
        report = {
            "deviations": deviations,
            "anomalies": anomalies,
            "similarity": similarity,
            "assessment": assessment,
            "comparison_timestamp": self._get_timestamp()
        }
        
        return report
    
    def calculate_deviations(
        self,
        generated: Dict[str, List[float]],
        golden: Dict[str, List[float]]
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate statistical deviations for each parameter
        
        Returns:
            Dictionary with deviation metrics for pH, temperature, and CO2
        """
        deviations = {}
        
        for param in ['ph', 'temperature', 'co2']:
            gen_values = np.array(generated[param])
            gold_values = np.array(golden[param])
            
            # Calculate various metrics
            mae = np.mean(np.abs(gen_values - gold_values))
            rmse = np.sqrt(np.mean((gen_values - gold_values)**2))
            max_deviation = np.max(np.abs(gen_values - gold_values))
            
            # Calculate correlation
            correlation, p_value = stats.pearsonr(gen_values, gold_values)
            
            # Point-by-point deviations
            point_deviations = (gen_values - gold_values).tolist()
            
            deviations[param] = {
                "mae": float(mae),
                "rmse": float(rmse),
                "max_deviation": float(max_deviation),
                "correlation": float(correlation),
                "correlation_p_value": float(p_value),
                "point_deviations": point_deviations,
                "status": self._get_deviation_status(param, mae, max_deviation)
            }
        
        return deviations
    
    def detect_anomalies(
        self,
        generated: Dict[str, List[float]],
        golden: Dict[str, List[float]]
    ) -> Dict[str, any]:
        """
        Detect anomalies in generated data using Isolation Forest
        
        Returns:
            Anomaly detection results
        """
        # Prepare data matrix
        gen_matrix = np.column_stack([
            generated['ph'],
            generated['temperature'],
            generated['co2']
        ])
        
        gold_matrix = np.column_stack([
            golden['ph'],
            golden['temperature'],
            golden['co2']
        ])
        
        # Train Isolation Forest on golden standard
        iso_forest = IsolationForest(
            contamination=GOLDEN_STANDARD_CONFIG["anomaly_contamination"],
            random_state=42
        )
        iso_forest.fit(gold_matrix)
        
        # Predict anomalies in generated data
        predictions = iso_forest.predict(gen_matrix)
        anomaly_scores = iso_forest.score_samples(gen_matrix)
        
        # Identify anomalous points
        anomaly_indices = np.where(predictions == -1)[0].tolist()
        anomaly_timestamps = [generated['timestamps'][i] for i in anomaly_indices]
        
        # Analyze anomaly types
        anomaly_details = self._analyze_anomaly_types(
            generated, golden, anomaly_indices
        )
        
        return {
            "has_anomalies": len(anomaly_indices) > 0,
            "anomaly_count": len(anomaly_indices),
            "anomaly_percentage": (len(anomaly_indices) / len(predictions)) * 100,
            "anomaly_indices": anomaly_indices,
            "anomaly_timestamps": anomaly_timestamps,
            "anomaly_scores": anomaly_scores.tolist(),
            "anomaly_details": anomaly_details
        }
    
    def _analyze_anomaly_types(
        self,
        generated: Dict[str, List[float]],
        golden: Dict[str, List[float]],
        anomaly_indices: List[int]
    ) -> List[Dict[str, any]]:
        """Analyze what type of anomaly occurred at each anomalous point"""
        details = []
        
        for idx in anomaly_indices:
            ph_dev = abs(generated['ph'][idx] - golden['ph'][idx])
            temp_dev = abs(generated['temperature'][idx] - golden['temperature'][idx])
            co2_dev = abs(generated['co2'][idx] - golden['co2'][idx])
            
            anomaly_type = []
            if ph_dev > self.ph_critical:
                anomaly_type.append("critical_ph_deviation")
            elif ph_dev > self.ph_warning:
                anomaly_type.append("warning_ph_deviation")
            
            if temp_dev > self.temp_critical:
                anomaly_type.append("critical_temp_deviation")
            elif temp_dev > self.temp_warning:
                anomaly_type.append("warning_temp_deviation")
            
            if co2_dev > self.co2_critical:
                anomaly_type.append("critical_co2_deviation")
            elif co2_dev > self.co2_warning:
                anomaly_type.append("warning_co2_deviation")
            
            details.append({
                "index": idx,
                "timestamp": generated['timestamps'][idx],
                "types": anomaly_type,
                "deviations": {
                    "ph": float(ph_dev),
                    "temperature": float(temp_dev),
                    "co2": float(co2_dev)
                }
            })
        
        return details
    
    def _calculate_similarity(
        self,
        generated: Dict[str, List[float]],
        golden: Dict[str, List[float]]
    ) -> Dict[str, float]:
        """
        Calculate similarity scores using multiple methods
        """
        similarity = {}
        
        for param in ['ph', 'temperature', 'co2']:
            gen_values = np.array(generated[param])
            gold_values = np.array(golden[param])
            
            # Normalized Euclidean distance
            euclidean_dist = euclidean(gen_values, gold_values)
            max_possible_dist = np.sqrt(len(gen_values)) * (gen_values.max() - gen_values.min())
            euclidean_similarity = 1 - (euclidean_dist / max_possible_dist) if max_possible_dist > 0 else 1.0
            
            # Dynamic Time Warping distance
            dtw_distance = dtw.distance(gen_values, gold_values)
            dtw_similarity = 1 / (1 + dtw_distance)
            
            # Cosine similarity
            cosine_sim = np.dot(gen_values, gold_values) / (
                np.linalg.norm(gen_values) * np.linalg.norm(gold_values)
            )
            
            # Average similarity
            avg_similarity = (euclidean_similarity + dtw_similarity + cosine_sim) / 3
            
            similarity[param] = {
                "euclidean_similarity": float(euclidean_similarity),
                "dtw_similarity": float(dtw_similarity),
                "cosine_similarity": float(cosine_sim),
                "average_similarity": float(avg_similarity)
            }
        
        # Overall similarity
        overall = np.mean([
            similarity['ph']['average_similarity'],
            similarity['temperature']['average_similarity'],
            similarity['co2']['average_similarity']
        ])
        
        similarity['overall'] = float(overall)
        
        return similarity
    
    def _align_datasets(
        self,
        generated: Dict[str, List[float]],
        golden: Dict[str, List[float]]
    ) -> Tuple[Dict[str, List[float]], Dict[str, List[float]]]:
        """
        Align datasets by interpolating to same length if needed
        """
        gen_len = len(generated['timestamps'])
        gold_len = len(golden['timestamps'])
        
        if gen_len == gold_len:
            return generated, golden
        
        # Use the shorter length
        target_len = min(gen_len, gold_len)
        
        gen_aligned = {
            'timestamps': generated['timestamps'][:target_len],
            'ph': generated['ph'][:target_len],
            'temperature': generated['temperature'][:target_len],
            'co2': generated['co2'][:target_len]
        }
        
        gold_aligned = {
            'timestamps': golden['timestamps'][:target_len],
            'ph': golden['ph'][:target_len],
            'temperature': golden['temperature'][:target_len],
            'co2': golden['co2'][:target_len]
        }
        
        return gen_aligned, gold_aligned
    
    def _get_deviation_status(
        self,
        param: str,
        mae: float,
        max_dev: float
    ) -> str:
        """Determine deviation status (normal, warning, critical)"""
        if param == 'ph':
            warning_threshold = self.ph_warning
            critical_threshold = self.ph_critical
        elif param == 'temperature':
            warning_threshold = self.temp_warning
            critical_threshold = self.temp_critical
        else:  # co2
            warning_threshold = self.co2_warning
            critical_threshold = self.co2_critical
        
        if max_dev >= critical_threshold:
            return "critical"
        elif mae >= warning_threshold:
            return "warning"
        else:
            return "normal"
    
    def _generate_assessment(
        self,
        deviations: Dict,
        anomalies: Dict,
        similarity: Dict
    ) -> Dict[str, any]:
        """Generate overall assessment of fermentation quality"""
        
        # Check if any parameter is critical
        critical_params = [
            param for param, data in deviations.items()
            if data['status'] == 'critical'
        ]
        
        warning_params = [
            param for param, data in deviations.items()
            if data['status'] == 'warning'
        ]
        
        # Overall status
        if critical_params:
            overall_status = "critical"
            message = f"Critical deviations detected in: {', '.join(critical_params)}"
        elif warning_params:
            overall_status = "warning"
            message = f"Warning deviations detected in: {', '.join(warning_params)}"
        elif anomalies['has_anomalies']:
            overall_status = "warning"
            message = f"Anomalies detected at {anomalies['anomaly_count']} time points"
        elif similarity['overall'] < self.similarity_threshold:
            overall_status = "warning"
            message = f"Low similarity score: {similarity['overall']:.2f}"
        else:
            overall_status = "normal"
            message = "Fermentation process is within normal parameters"
        
        return {
            "overall_status": overall_status,
            "message": message,
            "critical_parameters": critical_params,
            "warning_parameters": warning_params,
            "quality_score": float(similarity['overall'] * 100),
            "recommendations": self._generate_recommendations(
                overall_status, critical_params, warning_params, anomalies
            )
        }
    
    def _generate_recommendations(
        self,
        status: str,
        critical_params: List[str],
        warning_params: List[str],
        anomalies: Dict
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if 'ph' in critical_params:
            recommendations.append("URGENT: Check pH levels - possible contamination or acid imbalance")
        elif 'ph' in warning_params:
            recommendations.append("Monitor pH closely - slight deviation detected")
        
        if 'temperature' in critical_params:
            recommendations.append("URGENT: Check temperature control - cooling system may be failing")
        elif 'temperature' in warning_params:
            recommendations.append("Monitor temperature - ensure cooling system is functioning")
        
        if 'co2' in critical_params:
            recommendations.append("URGENT: Check CO2 levels - fermentation may be stalled or over-active")
        elif 'co2' in warning_params:
            recommendations.append("Monitor CO2 production - fermentation rate may be abnormal")
        
        if anomalies['has_anomalies'] and anomalies['anomaly_percentage'] > 10:
            recommendations.append("Multiple anomalies detected - consider full system inspection")
        
        if not recommendations:
            recommendations.append("Continue monitoring - process is normal")
        
        return recommendations
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def generate_comparison_report(
        self,
        generated_data: Dict[str, List[float]],
        golden_standard: Optional[Dict[str, List[float]]] = None
    ) -> str:
        """
        Generate a human-readable comparison report
        
        Returns:
            Formatted text report
        """
        comparison = self.compare_datasets(generated_data, golden_standard)
        
        report = []
        report.append("=" * 60)
        report.append("FERMENTATION DATA COMPARISON REPORT")
        report.append("=" * 60)
        report.append("")
        
        # Overall Assessment
        assessment = comparison['assessment']
        report.append(f"Overall Status: {assessment['overall_status'].upper()}")
        report.append(f"Quality Score: {assessment['quality_score']:.1f}/100")
        report.append(f"Message: {assessment['message']}")
        report.append("")
        
        # Deviations
        report.append("PARAMETER DEVIATIONS:")
        report.append("-" * 60)
        for param, data in comparison['deviations'].items():
            report.append(f"{param.upper()}:")
            report.append(f"  Status: {data['status']}")
            report.append(f"  MAE: {data['mae']:.3f}")
            report.append(f"  RMSE: {data['rmse']:.3f}")
            report.append(f"  Max Deviation: {data['max_deviation']:.3f}")
            report.append(f"  Correlation: {data['correlation']:.3f}")
            report.append("")
        
        # Anomalies
        report.append("ANOMALY DETECTION:")
        report.append("-" * 60)
        anomalies = comparison['anomalies']
        report.append(f"Anomalies Detected: {anomalies['has_anomalies']}")
        report.append(f"Anomaly Count: {anomalies['anomaly_count']}")
        report.append(f"Anomaly Percentage: {anomalies['anomaly_percentage']:.1f}%")
        report.append("")
        
        # Recommendations
        report.append("RECOMMENDATIONS:")
        report.append("-" * 60)
        for i, rec in enumerate(assessment['recommendations'], 1):
            report.append(f"{i}. {rec}")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)


if __name__ == "__main__":
    # Test the comparator
    print("Testing Data Comparator...")
    
    # This would normally load real data
    comparator = DataComparator()
    print("Data Comparator initialized successfully!")
