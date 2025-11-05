"""Data normalization engine - converts UDT (User Data Types) to MDF (Mist Data Format)."""
import pandas as pd
import json
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
import re


class DataNormalizer:
    """Normalize uploaded data to MDF format."""

    # MDF Standard Fields
    MDF_FIELDS = {
        # Vitals
        "vitals": ["timestamp", "vital_type", "value", "unit", "source"],
        # Lab Results
        "lab_results": ["timestamp", "test_name", "test_code", "value", "unit", "reference_range", "status"],
        # Medications
        "medications": ["medication_name", "medication_code", "dosage", "frequency", "start_date", "end_date"],
        # Diagnoses
        "diagnoses": ["diagnosis_code", "diagnosis_name", "diagnosis_date", "status", "severity"],
        # Procedures
        "procedures": ["procedure_code", "procedure_name", "procedure_date", "provider", "location"],
        # Demographics
        "demographics": ["age_range", "gender", "zip_code_prefix", "state", "ethnicity", "language"]
    }

    # Common field name mappings
    FIELD_MAPPINGS = {
        # Timestamp variations
        "date": "timestamp",
        "datetime": "timestamp",
        "time": "timestamp",
        "recorded_at": "timestamp",
        "measurement_date": "timestamp",

        # Vital signs
        "blood_pressure": "vital_type",
        "bp": "vital_type",
        "heart_rate": "vital_type",
        "hr": "vital_type",
        "temperature": "vital_type",
        "temp": "vital_type",
        "weight": "vital_type",
        "height": "vital_type",

        # Lab results
        "test": "test_name",
        "lab_test": "test_name",
        "test_result": "value",
        "result": "value",
        "loinc": "test_code",

        # Medications
        "drug": "medication_name",
        "medicine": "medication_name",
        "medication": "medication_name",
        "rxnorm": "medication_code",
        "dose": "dosage",

        # Demographics
        "age": "age_range",
        "sex": "gender",
        "zipcode": "zip_code_prefix",
        "zip": "zip_code_prefix",
        "race": "ethnicity"
    }

    def __init__(self):
        """Initialize normalizer."""
        self.confidence_scores = {}

    def normalize_csv(self, file_path: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Normalize a CSV file to MDF format."""
        # Read CSV
        df = pd.read_csv(file_path)

        # Detect data category
        category = self._detect_category(df.columns.tolist())

        # Map fields
        field_mappings = self._map_fields(df.columns.tolist(), category)

        # Rename columns
        df_normalized = df.rename(columns=field_mappings)

        # Apply transformations
        df_normalized = self._apply_transformations(df_normalized, category)

        # Calculate confidence score
        confidence = self._calculate_confidence(field_mappings, category)

        metadata = {
            "category": category,
            "field_mappings": field_mappings,
            "confidence_score": confidence,
            "total_records": len(df),
            "normalized_records": len(df_normalized)
        }

        return df_normalized, metadata

    def normalize_json(self, file_path: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Normalize a JSON file to MDF format."""
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Convert to DataFrame for processing
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            df = pd.DataFrame([data])
        else:
            raise ValueError("Unsupported JSON structure")

        # Use CSV normalization logic
        df_normalized, metadata = self.normalize_csv_dataframe(df)

        # Convert back to JSON
        normalized_data = df_normalized.to_dict(orient='records')

        return normalized_data, metadata

    def normalize_csv_dataframe(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Normalize a DataFrame to MDF format."""
        category = self._detect_category(df.columns.tolist())
        field_mappings = self._map_fields(df.columns.tolist(), category)
        df_normalized = df.rename(columns=field_mappings)
        df_normalized = self._apply_transformations(df_normalized, category)

        confidence = self._calculate_confidence(field_mappings, category)

        metadata = {
            "category": category,
            "field_mappings": field_mappings,
            "confidence_score": confidence,
            "total_records": len(df),
            "normalized_records": len(df_normalized)
        }

        return df_normalized, metadata

    def _detect_category(self, columns: List[str]) -> str:
        """Detect data category based on column names."""
        columns_lower = [col.lower() for col in columns]

        # Score each category
        scores = {category: 0 for category in self.MDF_FIELDS.keys()}

        for col in columns_lower:
            for category, fields in self.MDF_FIELDS.items():
                for field in fields:
                    if field.lower() in col or col in field.lower():
                        scores[category] += 1
                    # Check mappings
                    for source, target in self.FIELD_MAPPINGS.items():
                        if source in col and target in fields:
                            scores[category] += 0.5

        # Return category with highest score
        best_category = max(scores, key=scores.get)
        return best_category if scores[best_category] > 0 else "unknown"

    def _map_fields(self, columns: List[str], category: str) -> Dict[str, str]:
        """Map source fields to MDF fields."""
        mappings = {}
        mdf_fields = self.MDF_FIELDS.get(category, [])

        for col in columns:
            col_lower = col.lower()

            # Direct mapping
            if col_lower in mdf_fields:
                mappings[col] = col_lower
                self.confidence_scores[col] = 1.0
                continue

            # Check common mappings
            mapped = False
            for source, target in self.FIELD_MAPPINGS.items():
                if source in col_lower and target in mdf_fields:
                    mappings[col] = target
                    self.confidence_scores[col] = 0.8
                    mapped = True
                    break

            if mapped:
                continue

            # Fuzzy matching
            best_match = None
            best_score = 0
            for mdf_field in mdf_fields:
                score = self._fuzzy_match(col_lower, mdf_field)
                if score > best_score and score > 0.6:
                    best_score = score
                    best_match = mdf_field

            if best_match:
                mappings[col] = best_match
                self.confidence_scores[col] = best_score
            else:
                # Keep original if no match
                mappings[col] = col
                self.confidence_scores[col] = 0.3

        return mappings

    def _fuzzy_match(self, str1: str, str2: str) -> float:
        """Calculate fuzzy match score between two strings."""
        # Simple Levenshtein-like similarity
        str1_set = set(str1.split('_'))
        str2_set = set(str2.split('_'))

        if not str1_set or not str2_set:
            return 0.0

        intersection = str1_set.intersection(str2_set)
        union = str1_set.union(str2_set)

        return len(intersection) / len(union)

    def _apply_transformations(self, df: pd.DataFrame, category: str) -> pd.DataFrame:
        """Apply data transformations for MDF compliance."""
        df_copy = df.copy()

        # Timestamp normalization
        if 'timestamp' in df_copy.columns:
            df_copy['timestamp'] = pd.to_datetime(df_copy['timestamp'], errors='coerce')

        # Demographics: Age to age_range
        if category == 'demographics' and 'age' in df_copy.columns:
            df_copy['age_range'] = df_copy['age'].apply(self._age_to_range)
            df_copy = df_copy.drop('age', axis=1)

        # Demographics: Zip code to prefix
        if 'zip_code_prefix' in df_copy.columns:
            df_copy['zip_code_prefix'] = df_copy['zip_code_prefix'].astype(str).str[:3]

        # Vitals: Standardize units
        if category == 'vitals' and 'unit' in df_copy.columns:
            df_copy['unit'] = df_copy['unit'].apply(self._standardize_unit)

        return df_copy

    def _age_to_range(self, age: Any) -> str:
        """Convert age to HIPAA-compliant age range."""
        try:
            age = int(age)
            if age < 18:
                return "0-17"
            elif age < 26:
                return "18-25"
            elif age < 36:
                return "26-35"
            elif age < 46:
                return "36-45"
            elif age < 56:
                return "46-55"
            elif age < 66:
                return "56-65"
            elif age < 76:
                return "66-75"
            elif age < 90:
                return "76-89"
            else:
                return "90+"
        except:
            return "unknown"

    def _standardize_unit(self, unit: Any) -> str:
        """Standardize measurement units."""
        unit_mappings = {
            "f": "°F",
            "fahrenheit": "°F",
            "c": "°C",
            "celsius": "°C",
            "lb": "lbs",
            "pound": "lbs",
            "kg": "kg",
            "kilogram": "kg",
            "cm": "cm",
            "centimeter": "cm",
            "in": "in",
            "inch": "in"
        }

        unit_str = str(unit).lower().strip()
        return unit_mappings.get(unit_str, str(unit))

    def _calculate_confidence(self, mappings: Dict[str, str], category: str) -> float:
        """Calculate overall confidence score for normalization."""
        if not mappings:
            return 0.0

        total_confidence = sum(self.confidence_scores.values())
        avg_confidence = total_confidence / len(mappings)

        # Bonus for category detection
        if category != "unknown":
            avg_confidence *= 1.1

        return min(avg_confidence, 1.0)

    def export_to_mdf_json(self, df: pd.DataFrame, output_path: str):
        """Export normalized data to MDF JSON format."""
        mdf_data = {
            "version": "1.0",
            "generated_at": datetime.utcnow().isoformat(),
            "records": df.to_dict(orient='records')
        }

        with open(output_path, 'w') as f:
            json.dump(mdf_data, f, indent=2, default=str)

    def export_to_csv(self, df: pd.DataFrame, output_path: str):
        """Export normalized data to CSV."""
        df.to_csv(output_path, index=False)

    def export_to_excel(self, df: pd.DataFrame, output_path: str):
        """Export normalized data to Excel."""
        df.to_excel(output_path, index=False, engine='openpyxl')
