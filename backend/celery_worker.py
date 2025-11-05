"""Celery worker for background tasks."""
from celery import Celery
import os
from sqlalchemy.orm import Session

# Initialize Celery
celery_app = Celery(
    'mist_worker',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000
)


@celery_app.task(name='normalize_dataset')
def normalize_dataset(dataset_id: int):
    """Background task to normalize a dataset."""
    from database import SessionLocal
    from models import Dataset, DatasetStatus
    from normalizer import DataNormalizer
    import os

    db = SessionLocal()
    try:
        # Get dataset
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            return {"error": "Dataset not found"}

        # Update status to processing
        dataset.status = DatasetStatus.PROCESSING
        db.commit()

        # Initialize normalizer
        normalizer = DataNormalizer()

        # Determine file type and normalize
        file_extension = dataset.original_format.lower()

        try:
            if file_extension == 'csv':
                df_normalized, metadata = normalizer.normalize_csv(dataset.upload_path)

                # Save normalized file
                normalized_path = f"./normalized/{dataset.id}_normalized.csv"
                normalizer.export_to_csv(df_normalized, normalized_path)

            elif file_extension == 'json':
                normalized_data, metadata = normalizer.normalize_json(dataset.upload_path)

                # Save normalized file
                normalized_path = f"./normalized/{dataset.id}_normalized.json"
                normalizer.export_to_mdf_json(pd.DataFrame(normalized_data), normalized_path)

            else:
                raise ValueError(f"Unsupported file format: {file_extension}")

            # Update dataset with results
            dataset.status = DatasetStatus.NORMALIZED
            dataset.normalized_path = normalized_path
            dataset.total_records = metadata.get('total_records', 0)
            dataset.normalized_records = metadata.get('normalized_records', 0)
            dataset.field_mappings = metadata.get('field_mappings', {})
            dataset.confidence_score = metadata.get('confidence_score', 0.0)
            dataset.data_categories = [metadata.get('category', 'unknown')]

            db.commit()

            return {
                "status": "success",
                "dataset_id": dataset_id,
                "normalized_records": metadata.get('normalized_records', 0),
                "confidence_score": metadata.get('confidence_score', 0.0)
            }

        except Exception as e:
            # Update dataset with error
            dataset.status = DatasetStatus.FAILED
            dataset.error_message = str(e)
            db.commit()

            return {
                "status": "failed",
                "dataset_id": dataset_id,
                "error": str(e)
            }

    finally:
        db.close()


@celery_app.task(name='cleanup_old_exports')
def cleanup_old_exports():
    """Clean up expired export files."""
    from database import SessionLocal
    from models import Export
    from datetime import datetime
    import os

    db = SessionLocal()
    try:
        # Find expired exports
        expired_exports = db.query(Export).filter(
            Export.expires_at < datetime.utcnow()
        ).all()

        cleaned = 0
        for export in expired_exports:
            # Delete file
            if export.file_path and os.path.exists(export.file_path):
                os.remove(export.file_path)
                cleaned += 1

            # Delete record
            db.delete(export)

        db.commit()

        return {
            "status": "success",
            "cleaned": cleaned
        }

    finally:
        db.close()


@celery_app.task(name='generate_monthly_invoices')
def generate_monthly_invoices():
    """Generate monthly invoices for all users."""
    from database import SessionLocal
    from models import User, Billing, Invoice, InvoiceStatus
    from datetime import datetime, timedelta
    import uuid

    db = SessionLocal()
    try:
        # Get all users with transactions this month
        first_day = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
        last_month = first_day - timedelta(days=1)
        last_month_first = last_month.replace(day=1)

        users = db.query(User).all()
        invoices_created = 0

        for user in users:
            # Get transactions for last month
            transactions = db.query(Billing).filter(
                Billing.user_id == user.id,
                Billing.created_at >= last_month_first,
                Billing.created_at < first_day
            ).all()

            if not transactions:
                continue

            # Calculate totals
            subtotal = sum(t.amount for t in transactions if t.transaction_type == "sale")

            if subtotal <= 0:
                continue

            # Create invoice
            invoice = Invoice(
                user_id=user.id,
                invoice_number=f"INV-{datetime.utcnow().strftime('%Y%m')}-{uuid.uuid4().hex[:8].upper()}",
                status=InvoiceStatus.PENDING,
                subtotal=subtotal,
                tax=0.0,
                total=subtotal,
                period_start=last_month_first,
                period_end=first_day,
                due_date=datetime.utcnow() + timedelta(days=30)
            )
            db.add(invoice)
            invoices_created += 1

        db.commit()

        return {
            "status": "success",
            "invoices_created": invoices_created
        }

    finally:
        db.close()


@celery_app.task(name='reset_billing_period')
def reset_billing_period():
    """Reset billing period at the start of each month."""
    from database import SessionLocal
    from models import User

    db = SessionLocal()
    try:
        # This is a placeholder - in production, you might reset monthly quotas, etc.
        users = db.query(User).all()

        return {
            "status": "success",
            "users_processed": len(users)
        }

    finally:
        db.close()


# Periodic tasks configuration
celery_app.conf.beat_schedule = {
    'cleanup-exports-daily': {
        'task': 'cleanup_old_exports',
        'schedule': 86400.0,  # Run daily
    },
    'generate-invoices-monthly': {
        'task': 'generate_monthly_invoices',
        'schedule': 2592000.0,  # Run monthly (30 days)
    },
}


if __name__ == '__main__':
    celery_app.start()
