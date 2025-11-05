"""SQLAlchemy database models."""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


# Enums
class UserRole(str, enum.Enum):
    PATIENT = "patient"
    BUYER = "buyer"
    ADMIN = "admin"


class DatasetStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    NORMALIZED = "normalized"
    FAILED = "failed"


class ExportFormat(str, enum.Enum):
    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"
    FHIR = "fhir"


class InvoiceStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"


class User(Base):
    """User model - patients, buyers, and admins."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(SQLEnum(UserRole), default=UserRole.PATIENT, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    phone = Column(String(50))
    organization = Column(String(255))  # For buyers
    research_interests = Column(Text)  # For buyers

    # Billing
    stripe_customer_id = Column(String(255))
    total_earnings = Column(Float, default=0.0)
    total_spent = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))

    # Relationships
    datasets = relationship("Dataset", back_populates="owner", cascade="all, delete-orphan")
    exports = relationship("Export", back_populates="user", cascade="all, delete-orphan")
    billing_records = relationship("Billing", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class Dataset(Base):
    """Dataset model - uploaded and normalized data."""
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # File info
    filename = Column(String(255), nullable=False)
    original_format = Column(String(50))  # csv, json, hl7, fhir, etc.
    file_size = Column(Integer)  # bytes
    upload_path = Column(String(500))
    normalized_path = Column(String(500))

    # Processing
    status = Column(SQLEnum(DatasetStatus), default=DatasetStatus.UPLOADED, nullable=False)
    error_message = Column(Text)

    # Normalization metadata
    total_records = Column(Integer)
    normalized_records = Column(Integer)
    field_mappings = Column(JSON)  # MDF field mappings
    confidence_score = Column(Float)  # Overall normalization confidence

    # Marketplace
    is_for_sale = Column(Boolean, default=False)
    price = Column(Float)
    description = Column(Text)
    data_categories = Column(JSON)  # ["vitals", "labs", "medications"]
    date_range_start = Column(DateTime)
    date_range_end = Column(DateTime)

    # Consent & Privacy
    consent_token = Column(String(500))  # Blockchain token hash
    anonymization_level = Column(String(50), default="hipaa_safe_harbor")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="datasets")
    mappings = relationship("Mapping", back_populates="dataset", cascade="all, delete-orphan")
    exports = relationship("Export", back_populates="dataset", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Dataset {self.filename} ({self.status})>"


class Mapping(Base):
    """Field mapping model - tracks UDT to MDF conversions."""
    __tablename__ = "mappings"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)

    # Mapping details
    source_field = Column(String(255), nullable=False)  # UDT field name
    target_field = Column(String(255), nullable=False)  # MDF field name
    confidence = Column(Float)  # 0.0 - 1.0
    data_type = Column(String(50))  # string, integer, float, datetime
    transformation = Column(String(255))  # Applied transformation function

    # Sample values
    sample_values = Column(JSON)  # For validation

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    dataset = relationship("Dataset", back_populates="mappings")

    def __repr__(self):
        return f"<Mapping {self.source_field} → {self.target_field} ({self.confidence:.2f})>"


class Export(Base):
    """Export model - tracks data exports."""
    __tablename__ = "exports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="SET NULL"))

    # Export details
    format = Column(SQLEnum(ExportFormat), nullable=False)
    file_path = Column(String(500))
    file_size = Column(Integer)

    # Download tracking
    download_count = Column(Integer, default=0)
    last_downloaded = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="exports")
    dataset = relationship("Dataset", back_populates="exports")

    def __repr__(self):
        return f"<Export {self.format} by User {self.user_id}>"


class Billing(Base):
    """Billing model - tracks transactions."""
    __tablename__ = "billing"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Transaction details
    transaction_type = Column(String(50))  # sale, purchase, commission
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")

    # Payment gateway
    stripe_payment_id = Column(String(255))
    stripe_charge_id = Column(String(255))

    # Marketplace transaction
    buyer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    seller_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="SET NULL"))
    commission_amount = Column(Float)  # 12% platform fee

    # Description
    description = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="billing_records", foreign_keys=[user_id])

    def __repr__(self):
        return f"<Billing ${self.amount} {self.transaction_type}>"


class Invoice(Base):
    """Invoice model - monthly billing."""
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Invoice details
    invoice_number = Column(String(50), unique=True, nullable=False)
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.PENDING)

    # Amounts
    subtotal = Column(Float, nullable=False)
    tax = Column(Float, default=0.0)
    total = Column(Float, nullable=False)

    # Period
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)

    # Payment
    due_date = Column(DateTime(timezone=True))
    paid_at = Column(DateTime(timezone=True))
    stripe_invoice_id = Column(String(255))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Invoice {self.invoice_number} ({self.status})>"


class AuditLog(Base):
    """Audit log model - compliance tracking."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Event details
    event_type = Column(String(100), nullable=False)  # login, upload, export, consent_given
    resource_type = Column(String(50))  # dataset, user, export
    resource_id = Column(Integer)

    # Context
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    action = Column(String(255))
    details = Column(JSON)

    # Result
    success = Column(Boolean, default=True)
    error_message = Column(Text)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog {self.event_type} by User {self.user_id}>"
