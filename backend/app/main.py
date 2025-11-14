from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .api.user import generate, upload, extract, analyze, improve, history
from .api.admin import profiles, users, analytics
from .api.auth import router as auth_router

# This creates the tables. For production, use Alembic migrations.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Resume Intelligence Platform",
    description="API for managing, analyzing, and improving resumes.",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Mount Routers ---

# Auth
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])

# User Module
user_router_prefix = "/api/v1/user"
app.include_router(generate.router, prefix=user_router_prefix, tags=["User"])
app.include_router(upload.router, prefix=user_router_prefix, tags=["User"])
app.include_router(extract.router, prefix=user_router_prefix, tags=["User"])
app.include_router(analyze.router, prefix=user_router_prefix, tags=["User"])
app.include_router(improve.router, prefix=user_router_prefix, tags=["User"])
app.include_router(history.router, prefix=user_router_prefix, tags=["User"])

# Admin Module
admin_router_prefix = "/api/v1/admin"
app.include_router(profiles.router, prefix=admin_router_prefix, tags=["Admin"])
app.include_router(users.router, prefix=admin_router_prefix, tags=["Admin"])
app.include_router(analytics.router, prefix=admin_router_prefix, tags=["Admin"])

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "message": "API is running"}