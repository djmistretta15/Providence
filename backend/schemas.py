"""Pydantic schemas for API validation."""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# Enums
class UserRole(str, Enum):
    PATIENT = "patient"
    BUYER = "buyer"
    ADMIN = "admin"


class DatasetStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    NORMALIZED = "normalized"
    FAILED = "failed"


class ExportFormat(str, Enum):
    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"
    FHIR = "fhir"


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    role: UserRole = UserRole.PATIENT


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    organization: Optional[str] = None
    research_interests: Optional[str] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    total_earnings: float
    total_spent: float
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None


# Dataset Schemas
class DatasetBase(BaseModel):
    filename: str
    description: Optional[str] = None
    is_for_sale: bool = False
    price: Optional[float] = None


class DatasetCreate(DatasetBase):
    pass


class DatasetUpdate(BaseModel):
    description: Optional[str] = None
    is_for_sale: Optional[bool] = None
    price: Optional[float] = None


class DatasetResponse(DatasetBase):
    id: int
    owner_id: int
    status: DatasetStatus
    original_format: Optional[str]
    file_size: Optional[int]
    total_records: Optional[int]
    normalized_records: Optional[int]
    confidence_score: Optional[float]
    consent_token: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class DatasetDetailResponse(DatasetResponse):
    field_mappings: Optional[Dict[str, Any]]
    data_categories: Optional[List[str]]
    error_message: Optional[str]


# Mapping Schemas
class MappingResponse(BaseModel):
    id: int
    source_field: str
    target_field: str
    confidence: float
    data_type: Optional[str]
    transformation: Optional[str]
    sample_values: Optional[List[str]]

    class Config:
        from_attributes = True


# Export Schemas
class ExportCreate(BaseModel):
    dataset_id: int
    format: ExportFormat


class ExportResponse(BaseModel):
    id: int
    dataset_id: int
    format: ExportFormat
    file_path: str
    file_size: int
    download_count: int
    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


# Billing Schemas
class BillingResponse(BaseModel):
    id: int
    transaction_type: str
    amount: float
    currency: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Marketplace Schemas
class MarketplaceListingResponse(BaseModel):
    dataset_id: int
    filename: str
    description: Optional[str]
    price: float
    total_records: int
    data_categories: Optional[List[str]]
    date_range_start: Optional[datetime]
    date_range_end: Optional[datetime]
    confidence_score: Optional[float]
    seller_organization: Optional[str]

    class Config:
        from_attributes = True


class MarketplacePurchaseRequest(BaseModel):
    dataset_id: int
    payment_method_id: str  # Stripe payment method


# Stats Schemas
class DashboardStats(BaseModel):
    total_datasets: int
    normalized_datasets: int
    total_earnings: float
    total_records_processed: int
    recent_uploads: List[DatasetResponse]


# Consent Schema
class ConsentCreate(BaseModel):
    dataset_id: int
    consent_text: str
    agreed: bool = True


class ConsentResponse(BaseModel):
    dataset_id: int
    consent_token: str
    timestamp: datetime


# === MIST DATA FORMAT (MDF) DEFINITION ===

class MDFVital(BaseModel):
    """MDF Vital Signs Schema."""
    timestamp: datetime
    vital_type: str  # "blood_pressure", "heart_rate", "temperature", etc.
    value: float
    unit: str
    source: Optional[str] = None


class MDFLabResult(BaseModel):
    """MDF Lab Results Schema."""
    timestamp: datetime
    test_name: str
    test_code: Optional[str] = None  # LOINC code
    value: float
    unit: str
    reference_range: Optional[str] = None
    status: Optional[str] = None  # "final", "preliminary"


class MDFMedication(BaseModel):
    """MDF Medication Schema."""
    medication_name: str
    medication_code: Optional[str] = None  # RxNorm code
    dosage: str
    frequency: str
    start_date: datetime
    end_date: Optional[datetime] = None
    prescriber: Optional[str] = None


class MDFDiagnosis(BaseModel):
    """MDF Diagnosis Schema."""
    diagnosis_code: str  # ICD-10 code
    diagnosis_name: str
    diagnosis_date: datetime
    status: str  # "active", "resolved"
    severity: Optional[str] = None


class MDFProcedure(BaseModel):
    """MDF Procedure Schema."""
    procedure_code: str  # CPT code
    procedure_name: str
    procedure_date: datetime
    provider: Optional[str] = None
    location: Optional[str] = None


class MDFAllergy(BaseModel):
    """MDF Allergy Schema."""
    allergen: str
    allergen_code: Optional[str] = None
    reaction: str
    severity: str  # "mild", "moderate", "severe"
    onset_date: Optional[datetime] = None


class MDFImmunization(BaseModel):
    """MDF Immunization Schema."""
    vaccine_name: str
    vaccine_code: Optional[str] = None  # CVX code
    administration_date: datetime
    dose_number: Optional[int] = None
    provider: Optional[str] = None


class MDFEncounter(BaseModel):
    """MDF Encounter Schema."""
    encounter_id: str
    encounter_type: str  # "inpatient", "outpatient", "emergency"
    encounter_date: datetime
    provider: Optional[str] = None
    facility: Optional[str] = None
    discharge_date: Optional[datetime] = None


class MDFPatientDemographics(BaseModel):
    """MDF Patient Demographics (De-identified)."""
    age_range: str  # "18-25", "26-35", etc. (HIPAA Safe Harbor)
    gender: str
    zip_code_prefix: str  # First 3 digits only (HIPAA Safe Harbor)
    state: Optional[str] = None
    ethnicity: Optional[str] = None
    language: Optional[str] = None


class MDFDataset(BaseModel):
    """Complete MDF Dataset."""
    patient_id: str  # De-identified patient ID
    demographics: MDFPatientDemographics
    vitals: Optional[List[MDFVital]] = []
    lab_results: Optional[List[MDFLabResult]] = []
    medications: Optional[List[MDFMedication]] = []
    diagnoses: Optional[List[MDFDiagnosis]] = []
    procedures: Optional[List[MDFProcedure]] = []
    allergies: Optional[List[MDFAllergy]] = []
    immunizations: Optional[List[MDFImmunization]] = []
    encounters: Optional[List[MDFEncounter]] = []
    metadata: Optional[Dict[str, Any]] = {}


# File Upload Schema
class FileUploadResponse(BaseModel):
    dataset_id: int
    filename: str
    file_size: int
    status: str
    message: str


# Health Check
class HealthCheck(BaseModel):
    status: str
    database: bool
    redis: bool
    timestamp: datetime
