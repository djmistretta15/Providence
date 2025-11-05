"""Medical format parsers - HL7, FHIR, and HIPAA de-identification."""
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import re
import hashlib


class HL7Parser:
    """Parse HL7 v2.x messages."""

    def __init__(self):
        """Initialize HL7 parser."""
        self.segment_delimiter = '\r'
        self.field_delimiter = '|'
        self.component_delimiter = '^'
        self.repetition_delimiter = '~'
        self.escape_delimiter = '\\'
        self.subcomponent_delimiter = '&'

    def parse_message(self, hl7_message: str) -> Dict[str, Any]:
        """Parse an HL7 message into structured data."""
        segments = hl7_message.split(self.segment_delimiter)
        parsed_data = {
            "message_type": None,
            "patient": {},
            "observations": [],
            "raw_segments": {}
        }

        for segment in segments:
            if not segment.strip():
                continue

            fields = segment.split(self.field_delimiter)
            segment_type = fields[0]

            if segment_type == "MSH":
                parsed_data["message_type"] = self._parse_msh(fields)
            elif segment_type == "PID":
                parsed_data["patient"] = self._parse_pid(fields)
            elif segment_type == "OBX":
                parsed_data["observations"].append(self._parse_obx(fields))
            elif segment_type == "OBR":
                parsed_data["order"] = self._parse_obr(fields)

            parsed_data["raw_segments"][segment_type] = fields

        return parsed_data

    def _parse_msh(self, fields: List[str]) -> Dict[str, str]:
        """Parse MSH (Message Header) segment."""
        return {
            "sending_application": fields[2] if len(fields) > 2 else None,
            "sending_facility": fields[3] if len(fields) > 3 else None,
            "message_type": fields[8] if len(fields) > 8 else None,
            "message_control_id": fields[9] if len(fields) > 9 else None,
            "version": fields[11] if len(fields) > 11 else None
        }

    def _parse_pid(self, fields: List[str]) -> Dict[str, Any]:
        """Parse PID (Patient Identification) segment."""
        patient_name = fields[5].split(self.component_delimiter) if len(fields) > 5 else []

        return {
            "patient_id": fields[3] if len(fields) > 3 else None,
            "last_name": patient_name[0] if len(patient_name) > 0 else None,
            "first_name": patient_name[1] if len(patient_name) > 1 else None,
            "middle_name": patient_name[2] if len(patient_name) > 2 else None,
            "birth_date": fields[7] if len(fields) > 7 else None,
            "gender": fields[8] if len(fields) > 8 else None,
            "address": fields[11] if len(fields) > 11 else None,
            "phone": fields[13] if len(fields) > 13 else None
        }

    def _parse_obx(self, fields: List[str]) -> Dict[str, Any]:
        """Parse OBX (Observation/Result) segment."""
        observation_id = fields[3].split(self.component_delimiter) if len(fields) > 3 else []

        return {
            "set_id": fields[1] if len(fields) > 1 else None,
            "value_type": fields[2] if len(fields) > 2 else None,
            "observation_id": observation_id[0] if len(observation_id) > 0 else None,
            "observation_name": observation_id[1] if len(observation_id) > 1 else None,
            "value": fields[5] if len(fields) > 5 else None,
            "units": fields[6] if len(fields) > 6 else None,
            "reference_range": fields[7] if len(fields) > 7 else None,
            "status": fields[11] if len(fields) > 11 else None,
            "timestamp": fields[14] if len(fields) > 14 else None
        }

    def _parse_obr(self, fields: List[str]) -> Dict[str, Any]:
        """Parse OBR (Observation Request) segment."""
        return {
            "set_id": fields[1] if len(fields) > 1 else None,
            "order_id": fields[2] if len(fields) > 2 else None,
            "universal_service_id": fields[4] if len(fields) > 4 else None,
            "observation_datetime": fields[7] if len(fields) > 7 else None,
            "ordering_provider": fields[16] if len(fields) > 16 else None
        }

    def to_mdf(self, hl7_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert parsed HL7 to MDF format."""
        mdf_data = {
            "patient_id": self._hash_patient_id(hl7_data["patient"].get("patient_id", "")),
            "demographics": {
                "age_range": self._calculate_age_range(hl7_data["patient"].get("birth_date")),
                "gender": hl7_data["patient"].get("gender"),
                "zip_code_prefix": self._extract_zip_prefix(hl7_data["patient"].get("address"))
            },
            "vitals": [],
            "lab_results": []
        }

        # Convert observations to vitals or lab results
        for obs in hl7_data.get("observations", []):
            if self._is_vital(obs.get("observation_name")):
                mdf_data["vitals"].append({
                    "timestamp": obs.get("timestamp"),
                    "vital_type": obs.get("observation_name"),
                    "value": self._parse_numeric(obs.get("value")),
                    "unit": obs.get("units")
                })
            else:
                mdf_data["lab_results"].append({
                    "timestamp": obs.get("timestamp"),
                    "test_name": obs.get("observation_name"),
                    "test_code": obs.get("observation_id"),
                    "value": self._parse_numeric(obs.get("value")),
                    "unit": obs.get("units"),
                    "reference_range": obs.get("reference_range"),
                    "status": obs.get("status")
                })

        return mdf_data

    def _is_vital(self, observation_name: Optional[str]) -> bool:
        """Check if observation is a vital sign."""
        if not observation_name:
            return False

        vitals = ["blood pressure", "heart rate", "temperature", "respiratory rate",
                  "oxygen saturation", "weight", "height", "bmi"]
        return any(vital in observation_name.lower() for vital in vitals)

    def _parse_numeric(self, value: Any) -> Optional[float]:
        """Parse numeric value from string."""
        if not value:
            return None
        try:
            return float(re.sub(r'[^\d.-]', '', str(value)))
        except:
            return None

    def _hash_patient_id(self, patient_id: str) -> str:
        """Hash patient ID for de-identification."""
        return hashlib.sha256(patient_id.encode()).hexdigest()[:16]

    def _calculate_age_range(self, birth_date: Optional[str]) -> str:
        """Calculate age range from birth date."""
        if not birth_date:
            return "unknown"

        try:
            # HL7 date format: YYYYMMDD
            birth_year = int(birth_date[:4])
            current_year = datetime.now().year
            age = current_year - birth_year

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

    def _extract_zip_prefix(self, address: Optional[str]) -> str:
        """Extract ZIP code prefix from address."""
        if not address:
            return "000"

        # Extract 5-digit ZIP
        zip_match = re.search(r'\b\d{5}\b', address)
        if zip_match:
            return zip_match.group(0)[:3]

        return "000"


class FHIRParser:
    """Parse FHIR R4 JSON resources."""

    def parse_patient(self, fhir_patient: Dict[str, Any]) -> Dict[str, Any]:
        """Parse FHIR Patient resource."""
        return {
            "patient_id": self._hash_id(fhir_patient.get("id", "")),
            "gender": fhir_patient.get("gender"),
            "birth_date": fhir_patient.get("birthDate"),
            "address": fhir_patient.get("address", [{}])[0] if fhir_patient.get("address") else {}
        }

    def parse_observation(self, fhir_obs: Dict[str, Any]) -> Dict[str, Any]:
        """Parse FHIR Observation resource."""
        code = fhir_obs.get("code", {})
        coding = code.get("coding", [{}])[0] if code.get("coding") else {}

        value = fhir_obs.get("valueQuantity", {})

        return {
            "timestamp": fhir_obs.get("effectiveDateTime"),
            "test_name": coding.get("display"),
            "test_code": coding.get("code"),
            "value": value.get("value"),
            "unit": value.get("unit"),
            "status": fhir_obs.get("status")
        }

    def parse_medication_request(self, fhir_med: Dict[str, Any]) -> Dict[str, Any]:
        """Parse FHIR MedicationRequest resource."""
        medication = fhir_med.get("medicationCodeableConcept", {})
        coding = medication.get("coding", [{}])[0] if medication.get("coding") else {}

        dosage = fhir_med.get("dosageInstruction", [{}])[0] if fhir_med.get("dosageInstruction") else {}

        return {
            "medication_name": coding.get("display"),
            "medication_code": coding.get("code"),
            "dosage": dosage.get("text"),
            "frequency": dosage.get("timing", {}).get("code", {}).get("text")
        }

    def parse_condition(self, fhir_cond: Dict[str, Any]) -> Dict[str, Any]:
        """Parse FHIR Condition resource."""
        code = fhir_cond.get("code", {})
        coding = code.get("coding", [{}])[0] if code.get("coding") else {}

        return {
            "diagnosis_code": coding.get("code"),
            "diagnosis_name": coding.get("display"),
            "diagnosis_date": fhir_cond.get("onsetDateTime"),
            "status": fhir_cond.get("clinicalStatus", {}).get("text")
        }

    def to_mdf(self, fhir_bundle: Dict[str, Any]) -> Dict[str, Any]:
        """Convert FHIR Bundle to MDF format."""
        mdf_data = {
            "patient_id": None,
            "demographics": {},
            "vitals": [],
            "lab_results": [],
            "medications": [],
            "diagnoses": []
        }

        entries = fhir_bundle.get("entry", [])

        for entry in entries:
            resource = entry.get("resource", {})
            resource_type = resource.get("resourceType")

            if resource_type == "Patient":
                patient = self.parse_patient(resource)
                mdf_data["patient_id"] = patient["patient_id"]
                mdf_data["demographics"] = {
                    "age_range": self._calculate_age_range(patient.get("birth_date")),
                    "gender": patient.get("gender"),
                    "zip_code_prefix": self._extract_zip(patient.get("address", {}))
                }

            elif resource_type == "Observation":
                obs = self.parse_observation(resource)
                if self._is_vital(obs.get("test_name")):
                    mdf_data["vitals"].append(obs)
                else:
                    mdf_data["lab_results"].append(obs)

            elif resource_type == "MedicationRequest":
                mdf_data["medications"].append(self.parse_medication_request(resource))

            elif resource_type == "Condition":
                mdf_data["diagnoses"].append(self.parse_condition(resource))

        return mdf_data

    def _hash_id(self, identifier: str) -> str:
        """Hash identifier for de-identification."""
        return hashlib.sha256(identifier.encode()).hexdigest()[:16]

    def _is_vital(self, test_name: Optional[str]) -> bool:
        """Check if observation is a vital sign."""
        if not test_name:
            return False

        vitals = ["blood pressure", "heart rate", "temperature", "respiratory rate",
                  "oxygen saturation", "weight", "height", "bmi"]
        return any(vital in test_name.lower() for vital in vitals)

    def _calculate_age_range(self, birth_date: Optional[str]) -> str:
        """Calculate age range from birth date."""
        if not birth_date:
            return "unknown"

        try:
            birth_year = int(birth_date.split('-')[0])
            current_year = datetime.now().year
            age = current_year - birth_year

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

    def _extract_zip(self, address: Dict[str, Any]) -> str:
        """Extract ZIP code prefix from address."""
        postal_code = address.get("postalCode", "00000")
        return postal_code[:3]


class HIPAADeidentifier:
    """HIPAA Safe Harbor de-identification."""

    # 18 HIPAA identifiers to remove
    IDENTIFIERS_TO_REMOVE = [
        "names", "geographic_subdivisions", "dates", "phone", "fax",
        "email", "ssn", "mrn", "account_numbers", "certificate_numbers",
        "vehicle_ids", "device_ids", "urls", "ip_addresses",
        "biometric_ids", "photos", "unique_ids"
    ]

    def deidentify(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply HIPAA Safe Harbor de-identification."""
        deidentified = data.copy()

        # Remove direct identifiers
        fields_to_remove = ["name", "first_name", "last_name", "middle_name",
                            "ssn", "phone", "email", "mrn", "patient_id"]

        for field in fields_to_remove:
            if field in deidentified:
                deidentified[field] = "[REDACTED]"

        # Generalize dates to year only
        if "birth_date" in deidentified:
            deidentified["birth_date"] = deidentified["birth_date"][:4] + "-01-01"

        # ZIP code to first 3 digits
        if "zip_code" in deidentified:
            deidentified["zip_code_prefix"] = str(deidentified["zip_code"])[:3]
            del deidentified["zip_code"]

        # Age to age range
        if "age" in deidentified:
            deidentified["age_range"] = self._age_to_range(deidentified["age"])
            del deidentified["age"]

        return deidentified

    def _age_to_range(self, age: int) -> str:
        """Convert age to range."""
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
