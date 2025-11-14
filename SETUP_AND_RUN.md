# Resume AI - Complete Setup & Startup Guide

## Prerequisites

Before starting, ensure you have the following installed:

### Backend Requirements
- **Python 3.8+** - Download from https://www.python.org/downloads/
- **PostgreSQL Database** - Download from https://www.postgresql.org/download/
- **pip** (comes with Python)

### Frontend Requirements
- **Node.js 14+** (includes npm) - Download from https://nodejs.org/

## Quick Start (Windows)

### Step 1: Setup Backend

1. **Open PowerShell in the backend directory:**
   ```powershell
   cd "c:\A I  - P R O J E C T S\RESUME-AI-PROJECT\backend"
   ```

2. **Create a Python virtual environment (recommended):**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install Python dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Verify .env file exists** with required variables:
   - DATABASE_URL (PostgreSQL connection string)
   - SECRET_KEY (JWT secret)
   - ALGORITHM (HS256)
   - ACCESS_TOKEN_EXPIRE_MINUTES

5. **Start the backend server:**
   ```powershell
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   
   Or use the batch script:
   ```powershell
   .\start_backend.bat
   ```

   **Success indicators:**
   - Should see: `Uvicorn running on http://0.0.0.0:8000`
   - Check health: Open http://localhost:8000/health
   - API docs: Open http://localhost:8000/docs

### Step 2: Setup Frontend

1. **Open a NEW PowerShell window in the frontend directory:**
   ```powershell
   cd "c:\A I  - P R O J E C T S\RESUME-AI-PROJECT\frontend"
   ```

2. **Install npm dependencies:**
   ```powershell
   npm install
   ```

3. **Start the development server:**
   ```powershell
   npm start
   ```
   
   Or use the batch script:
   ```powershell
   .\start_frontend.bat
   ```

   **Success indicators:**
   - Browser opens automatically to http://localhost:3000
   - Should see the Resume AI application
   - No console errors

## Troubleshooting

### Backend Issues

#### Error: "pydantic_core._pydantic_core.ValidationError: DATABASE_URL Field required"
**Solution:** Make sure `.env` file exists in the backend root with correct values:
```
DATABASE_URL=postgresql://user:password@localhost:5432/database_name
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

#### Error: "ModuleNotFoundError: No module named 'fastapi'"
**Solution:** Install dependencies:
```powershell
pip install -r requirements.txt
```

#### Error: "PSYCOPG2 Error / Connection refused"
**Solution:** 
- Ensure PostgreSQL is running
- Verify DATABASE_URL in .env file is correct
- Check PostgreSQL credentials are valid

### Frontend Issues

#### Error: "Could not find a required file. Name: index.html"
**Solution:** Already fixed! The `public/index.html` file has been created.

#### Error: "npm: command not found"
**Solution:** Install Node.js from https://nodejs.org/

#### Error: "Port 3000 already in use"
**Solution:**
```powershell
# Find and kill process using port 3000
netstat -ano | findstr :3000
taskkill /PID <PID> /F
```

#### Error: Module not found (after npm install)
**Solution:**
```powershell
# Clear cache and reinstall
rmdir /s node_modules
del package-lock.json
npm install
```

## Project Structure

```
RESUME-AI-PROJECT/
├── backend/
│   ├── app/
│   │   ├── api/              # API endpoints (user, admin)
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic (LLM, extraction, analysis)
│   │   ├── utils/            # Utilities (auth, file handling)
│   │   ├── config.py         # Configuration from .env
│   │   ├── database.py       # Database setup
│   │   └── main.py           # FastAPI app entry point
│   ├── requirements.txt      # Python dependencies
│   ├── start_backend.bat     # Windows startup script
│   └── .env                  # Environment variables
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/            # Page components
│   │   ├── features/         # Redux features (slices, API)
│   │   ├── app/              # Redux store setup
│   │   ├── App.tsx           # Main app component
│   │   └── index.tsx         # Entry point
│   ├── public/               # Static assets
│   │   └── index.html        # HTML template
│   ├── package.json          # npm dependencies
│   ├── start_frontend.bat    # Windows startup script
│   └── tsconfig.json         # TypeScript configuration
└── .env                      # Root environment file

```

## Available Endpoints

### User API (http://localhost:8000/api/v1/user)
- `POST /upload_resume` - Upload a resume file
- `POST /generate_resume` - Generate a resume using AI
- `POST /extract_resume` - Extract data from a resume
- `POST /analyze_resume` - Analyze resume for ATS score
- `POST /improve_resume` - Get AI improvement suggestions
- `GET /history` - Get resume history

### Admin API (http://localhost:8000/api/v1/admin)
- `GET /users` - List all users
- `GET /user/{user_id}` - Get user details
- `GET /profiles` - Get all user profiles
- `GET /analytics` - Get platform analytics

### System
- `GET /health` - Health check
- `GET /docs` - Swagger API documentation
- `GET /redoc` - ReDoc API documentation

## Next Steps

1. **Create a User Account** - Use the frontend to sign up
2. **Upload a Resume** - Test the upload functionality
3. **Analyze Resume** - Use AI features to analyze your resume
4. **View Improvements** - Get AI-powered suggestions

## Development Notes

### Environment Variables (.env)

```
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/resume_db

# JWT Configuration
SECRET_KEY=your_super_secret_key_minimum_32_characters_long
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Optional API Keys (for external services)
DEEPSEEK_API_KEY=your_deepseek_key       # For OCR
GITHUB_TOKEN=your_github_token           # For GitHub analytics
HF_TOKEN=your_huggingface_token         # For Hugging Face models
```

### Database Setup

The application uses Alembic for migrations. To apply migrations:

```powershell
cd backend
alembic upgrade head
```

### Running Tests

```powershell
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## Support & Documentation

- **API Documentation**: http://localhost:8000/docs (when backend is running)
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **React Docs**: https://react.dev/
- **PostgreSQL Docs**: https://www.postgresql.org/docs/

---

**Last Updated:** November 13, 2025
**Version:** 1.0.0
