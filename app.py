from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.db import create_tables
from routes import auth, connections, query, alerts, export
from config import settings

app = FastAPI(
    title       = settings.APP_NAME,
    version     = settings.APP_VERSION,
    description = "AI Powered Business Intelligence Co-Pilot"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["http://localhost", "http://localhost:3000"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

create_tables()

# ── All Routes ────────────────────────────────────────────
app.include_router(auth.router)        
app.include_router(connections.router)  
app.include_router(query.router)       
app.include_router(alerts.router)       
app.include_router(export.router)       

@app.get("/")
def root():
    return {
        "app"    : settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status" : "running",
        "docs"   : "/docs"
    }

@app.get("/health")
def health():
    from utils.cache import get_cache_stats
    return {
        "status": "healthy",
        "cache" : get_cache_stats()
    }