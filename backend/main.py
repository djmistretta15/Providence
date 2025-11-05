"""Main FastAPI application - Mist Data Steward."""
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import os
import shutil
from pathlib import Path

from database import get_db, init_db, check_db_health
from models import User, Dataset, Export, Billing, AuditLog, UserRole, DatasetStatus
from schemas import (
    UserCreate, UserLogin, UserResponse, UserUpdate, Token,
    DatasetResponse, DatasetDetailResponse, DatasetUpdate,
    ExportCreate, ExportResponse, ExportFormat,
    BillingResponse, DashboardStats, HealthCheck,
    FileUploadResponse, ConsentCreate, ConsentResponse,
    MarketplaceListingResponse, MarketplacePurchaseRequest
)
from auth import (
    authenticate_user, create_access_token, get_current_active_user,
    get_password_hash, check_rate_limit, require_role
)

# Initialize FastAPI app
app = FastAPI(
    title="Mist Data Steward API",
    description="Patient-empowered data sovereignty platform",
    version="1.0.0"
)

# CORS configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# File storage directories
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
NORMALIZED_DIR = Path(os.getenv("NORMALIZED_DIR", "./normalized"))
EXPORT_DIR = Path(os.getenv("EXPORT_DIR", "./exports"))

# Create directories
for directory in [UPLOAD_DIR, NORMALIZED_DIR, EXPORT_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


# ==================== HEALTH & INFO ====================

@app.get("/")
def read_root():
    """Welcome endpoint."""
    return {
        "message": "Mist Data Steward API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthCheck)
def health_check():
    """Health check endpoint."""
    db_healthy = check_db_health()
    redis_healthy = True  # TODO: Add Redis health check

    return HealthCheck(
        status="healthy" if db_healthy else "unhealthy",
        database=db_healthy,
        redis=redis_healthy,
        timestamp=datetime.utcnow()
    )


# ==================== AUTHENTICATION ====================

@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    db_user = User(
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        hashed_password=get_password_hash(user.password)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Create audit log
    log = AuditLog(
        user_id=db_user.id,
        event_type="user_registered",
        resource_type="user",
        resource_id=db_user.id,
        success=True
    )
    db.add(log)
    db.commit()

    return db_user


@app.post("/auth/login", response_model=Token)
def login_user(user_login: UserLogin, request: Request, db: Session = Depends(get_db)):
    """Login user and return JWT token."""
    # Rate limiting
    client_ip = request.client.host
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests"
        )

    # Authenticate user
    user = authenticate_user(db, user_login.email, user_login.password)
    if not user:
        # Log failed attempt
        log = AuditLog(
            event_type="login_failed",
            ip_address=client_ip,
            details={"email": user_login.email},
            success=False
        )
        db.add(log)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Create access token
    access_token = create_access_token(data={"sub": user.email})

    # Log successful login
    log = AuditLog(
        user_id=user.id,
        event_type="login_success",
        resource_type="user",
        resource_id=user.id,
        ip_address=client_ip,
        success=True
    )
    db.add(log)
    db.commit()

    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/auth/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information."""
    return current_user


@app.put("/auth/me", response_model=UserResponse)
def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user profile."""
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    if user_update.phone is not None:
        current_user.phone = user_update.phone
    if user_update.organization is not None:
        current_user.organization = user_update.organization
    if user_update.research_interests is not None:
        current_user.research_interests = user_update.research_interests

    db.commit()
    db.refresh(current_user)
    return current_user


# ==================== DATASETS ====================

@app.get("/datasets", response_model=List[DatasetResponse])
def list_datasets(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List user's datasets."""
    datasets = db.query(Dataset).filter(
        Dataset.owner_id == current_user.id
    ).offset(skip).limit(limit).all()
    return datasets


@app.get("/datasets/{dataset_id}", response_model=DatasetDetailResponse)
def get_dataset(
    dataset_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get dataset details."""
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.owner_id == current_user.id
    ).first()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return dataset


@app.put("/datasets/{dataset_id}", response_model=DatasetResponse)
def update_dataset(
    dataset_id: int,
    dataset_update: DatasetUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update dataset metadata."""
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.owner_id == current_user.id
    ).first()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset_update.description is not None:
        dataset.description = dataset_update.description
    if dataset_update.is_for_sale is not None:
        dataset.is_for_sale = dataset_update.is_for_sale
    if dataset_update.price is not None:
        dataset.price = dataset_update.price

    db.commit()
    db.refresh(dataset)
    return dataset


@app.delete("/datasets/{dataset_id}")
def delete_dataset(
    dataset_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a dataset."""
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.owner_id == current_user.id
    ).first()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Delete files
    if dataset.upload_path and os.path.exists(dataset.upload_path):
        os.remove(dataset.upload_path)
    if dataset.normalized_path and os.path.exists(dataset.normalized_path):
        os.remove(dataset.normalized_path)

    # Delete from database
    db.delete(dataset)
    db.commit()

    return {"message": "Dataset deleted successfully"}


# ==================== FILE UPLOAD & PROCESSING ====================

@app.post("/ingest", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload a data file for processing."""
    # Validate file size
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_MB", "100")) * 1024 * 1024
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {MAX_FILE_SIZE / 1024 / 1024}MB"
        )

    # Save file
    file_path = UPLOAD_DIR / f"{current_user.id}_{datetime.utcnow().timestamp()}_{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Create dataset record
    dataset = Dataset(
        owner_id=current_user.id,
        filename=file.filename,
        original_format=file.filename.split('.')[-1].lower(),
        file_size=file_size,
        upload_path=str(file_path),
        status=DatasetStatus.UPLOADED
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    # TODO: Trigger Celery task for normalization
    # normalize_dataset.delay(dataset.id)

    # Create audit log
    log = AuditLog(
        user_id=current_user.id,
        event_type="file_uploaded",
        resource_type="dataset",
        resource_id=dataset.id,
        details={"filename": file.filename, "size": file_size},
        success=True
    )
    db.add(log)
    db.commit()

    return FileUploadResponse(
        dataset_id=dataset.id,
        filename=file.filename,
        file_size=file_size,
        status="uploaded",
        message="File uploaded successfully. Processing will begin shortly."
    )


# ==================== EXPORTS ====================

@app.post("/exports", response_model=ExportResponse)
def create_export(
    export_request: ExportCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create an export of normalized data."""
    # Verify dataset ownership
    dataset = db.query(Dataset).filter(
        Dataset.id == export_request.dataset_id,
        Dataset.owner_id == current_user.id
    ).first()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset.status != DatasetStatus.NORMALIZED:
        raise HTTPException(
            status_code=400,
            detail="Dataset must be normalized before export"
        )

    # Create export record
    export_path = EXPORT_DIR / f"{current_user.id}_{dataset.id}_{datetime.utcnow().timestamp()}.{export_request.format.value}"

    # TODO: Generate actual export file
    export_file_size = 1000  # Placeholder

    export = Export(
        user_id=current_user.id,
        dataset_id=dataset.id,
        format=export_request.format,
        file_path=str(export_path),
        file_size=export_file_size,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(export)
    db.commit()
    db.refresh(export)

    return export


@app.get("/exports/{export_id}/download")
def download_export(
    export_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Download an export file."""
    export = db.query(Export).filter(
        Export.id == export_id,
        Export.user_id == current_user.id
    ).first()

    if not export:
        raise HTTPException(status_code=404, detail="Export not found")

    if export.expires_at and export.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Export has expired")

    if not os.path.exists(export.file_path):
        raise HTTPException(status_code=404, detail="Export file not found")

    # Update download count
    export.download_count += 1
    export.last_downloaded = datetime.utcnow()
    db.commit()

    return FileResponse(
        export.file_path,
        media_type="application/octet-stream",
        filename=os.path.basename(export.file_path)
    )


# ==================== CONSENT ====================

@app.post("/consent", response_model=ConsentResponse)
def create_consent(
    consent: ConsentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Record user consent for data usage."""
    dataset = db.query(Dataset).filter(
        Dataset.id == consent.dataset_id,
        Dataset.owner_id == current_user.id
    ).first()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if not consent.agreed:
        raise HTTPException(status_code=400, detail="Consent must be agreed to")

    # Generate consent token (simplified - in production, use blockchain)
    import hashlib
    consent_data = f"{current_user.id}:{consent.dataset_id}:{datetime.utcnow().isoformat()}:{consent.consent_text}"
    consent_token = hashlib.sha256(consent_data.encode()).hexdigest()

    dataset.consent_token = consent_token
    db.commit()

    # Create audit log
    log = AuditLog(
        user_id=current_user.id,
        event_type="consent_given",
        resource_type="dataset",
        resource_id=dataset.id,
        details={"consent_token": consent_token},
        success=True
    )
    db.add(log)
    db.commit()

    return ConsentResponse(
        dataset_id=dataset.id,
        consent_token=consent_token,
        timestamp=datetime.utcnow()
    )


# ==================== MARKETPLACE ====================

@app.get("/marketplace/listings", response_model=List[MarketplaceListingResponse])
def list_marketplace(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List datasets available for purchase."""
    datasets = db.query(Dataset).filter(
        Dataset.is_for_sale == True,
        Dataset.status == DatasetStatus.NORMALIZED,
        Dataset.owner_id != current_user.id  # Don't show user's own datasets
    ).offset(skip).limit(limit).all()

    listings = []
    for dataset in datasets:
        listings.append(MarketplaceListingResponse(
            dataset_id=dataset.id,
            filename=dataset.filename,
            description=dataset.description,
            price=dataset.price,
            total_records=dataset.total_records or 0,
            data_categories=dataset.data_categories,
            date_range_start=dataset.date_range_start,
            date_range_end=dataset.date_range_end,
            confidence_score=dataset.confidence_score,
            seller_organization=dataset.owner.organization
        ))

    return listings


@app.post("/marketplace/purchase")
def purchase_dataset(
    purchase: MarketplacePurchaseRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Purchase a dataset from the marketplace."""
    dataset = db.query(Dataset).filter(
        Dataset.id == purchase.dataset_id,
        Dataset.is_for_sale == True
    ).first()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or not for sale")

    if dataset.owner_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot purchase your own dataset")

    # TODO: Process payment with Stripe using purchase.payment_method_id

    # Calculate commission (12%)
    commission_rate = float(os.getenv("COMMISSION_RATE", "0.12"))
    commission = dataset.price * commission_rate
    seller_amount = dataset.price - commission

    # Create billing records
    purchase_record = Billing(
        user_id=current_user.id,
        transaction_type="purchase",
        amount=dataset.price,
        buyer_id=current_user.id,
        seller_id=dataset.owner_id,
        dataset_id=dataset.id,
        description=f"Purchased dataset: {dataset.filename}"
    )

    seller_record = Billing(
        user_id=dataset.owner_id,
        transaction_type="sale",
        amount=seller_amount,
        buyer_id=current_user.id,
        seller_id=dataset.owner_id,
        dataset_id=dataset.id,
        commission_amount=commission,
        description=f"Sold dataset: {dataset.filename}"
    )

    commission_record = Billing(
        user_id=dataset.owner_id,
        transaction_type="commission",
        amount=commission,
        buyer_id=current_user.id,
        seller_id=dataset.owner_id,
        dataset_id=dataset.id,
        description=f"Platform commission for: {dataset.filename}"
    )

    db.add_all([purchase_record, seller_record, commission_record])

    # Update user balances
    current_user.total_spent += dataset.price
    dataset.owner.total_earnings += seller_amount

    db.commit()

    return {
        "message": "Purchase successful",
        "dataset_id": dataset.id,
        "amount_paid": dataset.price
    }


# ==================== BILLING ====================

@app.get("/billing/transactions", response_model=List[BillingResponse])
def list_transactions(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List user's billing transactions."""
    transactions = db.query(Billing).filter(
        Billing.user_id == current_user.id
    ).order_by(Billing.created_at.desc()).offset(skip).limit(limit).all()

    return transactions


@app.get("/billing/earnings")
def get_earnings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's earnings summary."""
    sales = db.query(Billing).filter(
        Billing.user_id == current_user.id,
        Billing.transaction_type == "sale"
    ).all()

    return {
        "total_earnings": current_user.total_earnings,
        "total_sales": len(sales),
        "average_sale_price": sum(s.amount for s in sales) / len(sales) if sales else 0,
        "recent_sales": sales[:10]
    }


# ==================== DASHBOARD ====================

@app.get("/dashboard/stats", response_model=DashboardStats)
def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics."""
    datasets = db.query(Dataset).filter(Dataset.owner_id == current_user.id).all()

    total_datasets = len(datasets)
    normalized_datasets = len([d for d in datasets if d.status == DatasetStatus.NORMALIZED])
    total_records = sum(d.total_records or 0 for d in datasets)

    recent_uploads = db.query(Dataset).filter(
        Dataset.owner_id == current_user.id
    ).order_by(Dataset.created_at.desc()).limit(5).all()

    return DashboardStats(
        total_datasets=total_datasets,
        normalized_datasets=normalized_datasets,
        total_earnings=current_user.total_earnings,
        total_records_processed=total_records,
        recent_uploads=recent_uploads
    )


# ==================== ADMIN ====================

@app.get("/admin/users", response_model=List[UserResponse])
def list_all_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Admin: List all users."""
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@app.get("/admin/stats")
def get_admin_stats(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Admin: Get platform statistics."""
    total_users = db.query(User).count()
    total_datasets = db.query(Dataset).count()
    total_transactions = db.query(Billing).count()
    total_revenue = db.query(Billing).filter(
        Billing.transaction_type == "commission"
    ).all()

    return {
        "total_users": total_users,
        "total_datasets": total_datasets,
        "total_transactions": total_transactions,
        "total_revenue": sum(t.amount for t in total_revenue),
        "active_listings": db.query(Dataset).filter(Dataset.is_for_sale == True).count()
    }


# ==================== ERROR HANDLERS ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# ==================== STARTUP/SHUTDOWN ====================

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    print("🚀 Starting Mist Data Steward API...")
    init_db()
    print("✅ Database initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    print("👋 Shutting down Mist Data Steward API...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
