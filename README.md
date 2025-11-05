# Mist Data Steward

**Patient-Empowered Data Sovereignty Platform**

Mist Data Steward is a comprehensive platform that empowers patients to own, control, and monetize their health data while maintaining privacy and compliance with HIPAA regulations.

## Features

- **Data Ingestion**: Upload health data in multiple formats (CSV, JSON, HL7, FHIR)
- **Automatic Normalization**: Convert any format to standardized MDF (Mist Data Format)
- **HIPAA Compliance**: Automatic de-identification using HIPAA Safe Harbor standards
- **Data Marketplace**: Buy and sell normalized health data
- **Consent Management**: Blockchain-ready consent tokens for transparent data usage
- **Revenue Tracking**: Track earnings from data sales with 88% seller payout
- **Advanced Analytics**: Confidence scoring and data quality metrics

## Tech Stack

### Backend
- **FastAPI**: High-performance Python web framework
- **PostgreSQL**: Relational database
- **Redis**: Caching and task queue
- **Celery**: Background task processing
- **SQLAlchemy**: ORM
- **JWT**: Authentication

### Frontend
- **React**: UI framework
- **Vite**: Build tool
- **Tailwind CSS**: Styling
- **Axios**: HTTP client
- **React Router**: Navigation

### Infrastructure
- **Docker**: Containerization
- **Docker Compose**: Multi-container orchestration
- **Nginx**: Reverse proxy (optional)

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Providence
   ```

2. **Start all services**
   ```bash
   docker-compose up -d
   ```

3. **Initialize database**
   ```bash
   docker-compose exec api python scripts/init_db.py
   ```

4. **Create admin user**
   ```bash
   docker-compose exec api python scripts/create_admin.py
   ```

5. **Access the application**
   - Frontend: http://localhost:5173
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Development Setup (Without Docker)

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your configuration
python scripts/init_db.py
uvicorn main:app --reload
```

#### Frontend
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Usage

### 1. Register an Account
- Navigate to http://localhost:5173/register
- Choose account type: Patient (sell data) or Buyer (purchase data)
- Complete registration

### 2. Upload Health Data
- Go to Upload page
- Drag & drop or select file (CSV, JSON, HL7, FHIR)
- File is automatically uploaded, normalized, and de-identified

### 3. View Datasets
- Dashboard shows all uploaded datasets
- Click on dataset to view details, field mappings, and quality scores

### 4. Sell Data (For Patients)
- Mark dataset as "For Sale" with a price
- Data appears in marketplace for buyers
- Earn 88% of sale price (12% platform fee)

### 5. Purchase Data (For Buyers)
- Browse marketplace for available datasets
- Filter by category, price, quality score
- Purchase datasets securely

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get JWT token
- `GET /auth/me` - Get current user info

### Datasets
- `GET /datasets` - List user's datasets
- `GET /datasets/{id}` - Get dataset details
- `POST /ingest` - Upload new dataset
- `PUT /datasets/{id}` - Update dataset
- `DELETE /datasets/{id}` - Delete dataset

### Marketplace
- `GET /marketplace/listings` - Browse available datasets
- `POST /marketplace/purchase` - Purchase a dataset

### Billing
- `GET /billing/transactions` - Get transaction history
- `GET /billing/earnings` - Get earnings summary

### Exports
- `POST /exports` - Create data export
- `GET /exports/{id}/download` - Download export

See full API documentation at http://localhost:8000/docs

## Data Format: MDF (Mist Data Format)

MDF is our standardized medical data format supporting:

- **Vitals**: Blood pressure, heart rate, temperature, etc.
- **Lab Results**: Test results with LOINC codes
- **Medications**: Prescriptions with RxNorm codes
- **Diagnoses**: Conditions with ICD-10 codes
- **Procedures**: Medical procedures with CPT codes
- **Demographics**: De-identified patient information

### Example MDF Structure
```json
{
  "patient_id": "abc123def456",
  "demographics": {
    "age_range": "26-35",
    "gender": "F",
    "zip_code_prefix": "945"
  },
  "vitals": [
    {
      "timestamp": "2024-01-15T10:30:00",
      "vital_type": "blood_pressure",
      "value": 120,
      "unit": "mmHg"
    }
  ],
  "lab_results": [...],
  "medications": [...],
  "diagnoses": [...]
}
```

## HIPAA Compliance

The platform automatically applies HIPAA Safe Harbor de-identification:

1. **Names** - Removed
2. **Geographic subdivisions** - ZIP code to first 3 digits
3. **Dates** - Generalized to year or age ranges
4. **Phone/Fax/Email** - Removed
5. **SSN/MRN** - Removed or hashed
6. **Ages** - Converted to ranges (18-25, 26-35, etc.)
7. **All other identifiers** - Removed or hashed

## Revenue Model

- **Seller Payout**: 88% of sale price
- **Platform Fee**: 12% commission
- **No listing fees**
- **No subscription costs**
- **Transparent pricing**

## Architecture

```
┌─────────────┐
│   Frontend  │ (React + Vite)
│  Port 5173  │
└──────┬──────┘
       │
       │ HTTP/REST
       │
┌──────▼──────┐
│   Nginx     │ (Reverse Proxy)
│   Port 80   │
└──────┬──────┘
       │
       │
┌──────▼──────┐      ┌──────────┐
│   FastAPI   │◄────►│PostgreSQL│
│  Port 8000  │      │ Port 5432│
└──────┬──────┘      └──────────┘
       │
       │ Redis
       │
┌──────▼──────┐
│   Celery    │ (Background Tasks)
│   Worker    │
└─────────────┘
```

## Security

- **JWT Authentication**: Secure token-based auth
- **Password Hashing**: Bcrypt with salt
- **Rate Limiting**: Prevent abuse
- **CORS**: Configurable origins
- **SQL Injection Protection**: Parameterized queries
- **XSS Protection**: Input sanitization
- **HTTPS Ready**: SSL/TLS support

## Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for production deployment instructions.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE)

## Support

- Documentation: [docs/](docs/)
- Issues: GitHub Issues
- Email: support@mistdatasteward.com

## Roadmap

### Phase 1: MVP (Current)
- ✅ Core data ingestion
- ✅ Basic normalization
- ✅ User authentication
- ✅ Marketplace

### Phase 2: Enhanced Features
- 🔄 Advanced medical parsers (HL7, FHIR)
- 🔄 Real-time data quality monitoring
- 🔄 Enhanced marketplace matching
- 🔄 Payment integration (Stripe)

### Phase 3: Enterprise
- ⏳ Multi-tenant support
- ⏳ Advanced analytics dashboard
- ⏳ Blockchain integration for consent
- ⏳ API for external integrations

### Phase 4: Scale
- ⏳ Machine learning for data matching
- ⏳ Real-time data streaming
- ⏳ Mobile applications
- ⏳ International expansion

---

**Built with ❤️ for patient data sovereignty**
