#!/usr/bin/env python3
"""
FastAPI Project Setup Script
Creates the proper project structure and files for the Balance Tracking API
"""

import os
from pathlib import Path


def create_project_structure():
    """Create the FastAPI project directory structure"""
    
    # Define the project structure
    structure = {
        "api": {
            "__init__.py": "",
            "config.py": "# Configuration file - content from fastapi_config artifact",
            "database.py": "# Database manager - content from fastapi_database artifact", 
            "models.py": "# Pydantic models - content from fastapi_models artifact",
            "dependencies.py": "# Dependencies - content from fastapi_dependencies artifact",
            "routes": {
                "__init__.py": "",
                "users.py": "# User routes - extract from fastapi_basic_routes artifact",
                "balances.py": "# Balance routes - extract from fastapi_basic_routes artifact", 
                "transactions.py": "# Transaction routes - extract from fastapi_basic_routes artifact",
                "currencies.py": "# Currency routes - extract from fastapi_basic_routes artifact"
            }
        },
        "main.py": "# Main application - content from fastapi_main_app artifact",
        "requirements.txt": """fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic[email]==2.5.0
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-decouple==3.8
""",
        ".env.example": """# Database configuration
DATABASE_URL=sqlite:///balance_tracker.db

# Security
SECRET_KEY=your-secret-key-change-in-production
JWT_EXPIRE_MINUTES=30

# Environment
ENVIRONMENT=development
DEBUG=true

# Rate limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Logging
LOG_LEVEL=INFO
""",
        "README_API.md": """# Balance Tracking System - FastAPI Backend

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
curl -X POST "http://localhost:8000/api/v1/transactions/deposit" \\
  -H "Content-Type: application/json" \\
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
"""
    }
    
    def create_structure(base_path, structure_dict):
        """Recursively create directory structure"""
        for name, content in structure_dict.items():
            path = base_path / name
            
            if isinstance(content, dict):
                # It's a directory
                path.mkdir(exist_ok=True)
                create_structure(path, content)
            else:
                # It's a file
                path.write_text(content)
                print(f"✅ Created: {path}")
    
    # Create the structure
    base_path = Path("fastapi_backend")
    base_path.mkdir(exist_ok=True)
    
    print("🚀 Creating FastAPI project structure...")
    create_structure(base_path, structure)
    
    print(f"""
✅ FastAPI project structure created in: {base_path.absolute()}

📁 Project Structure:
{base_path}/
├── api/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── dependencies.py
│   └── routes/
│       ├── __init__.py
│       ├── users.py
│       ├── balances.py
│       ├── transactions.py
│       └── currencies.py
├── main.py
├── requirements.txt
├── .env.example
└── README_API.md

🔧 Next Steps:
1. cd {base_path}
2. Copy the artifact contents into the respective files
3. pip install -r requirements.txt
4. cp .env.example .env
5. python3 main.py

📚 API Documentation will be available at:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)
""")

    return base_path


if __name__ == "__main__":
    create_project_structure()
