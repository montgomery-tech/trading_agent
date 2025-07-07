# Balance Tracking System - FastAPI Backend

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

3. Ensure database exists:
```bash
python3 setup_database.py sqlite
```

4. Run the server:
```bash
python3 main.py
# or
uvicorn main:app --reload
```

5. Open API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### System
- GET `/` - API information
- GET `/health` - Health check

### Users
- GET `/api/v1/users/{username}` - Get user details

### Balances  
- GET `/api/v1/balances/user/{username}` - Get user balances

### Transactions
- POST `/api/v1/transactions/deposit` - Create deposit

### Currencies
- GET `/api/v1/currencies/` - List currencies

## Example Usage

### Create a Deposit
```bash
curl -X POST "http://localhost:8000/api/v1/transactions/deposit" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "demo_user",
    "amount": 1000,
    "currency_code": "USD",
    "description": "Initial deposit"
  }'
```

### Get User Balances
```bash
curl "http://localhost:8000/api/v1/balances/user/demo_user"
```
