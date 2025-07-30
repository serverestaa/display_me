# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from configs.oauth import oauth
from config import settings
import os
from database import Base, engine
from routers import auth, users, sections, blocks, resume
from routers import cover_letter, cv_analyzer

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Resume Builder with JWT",
    description="A comprehensive resume builder API with JWT authentication",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add session middleware
app.add_middleware(
    SessionMiddleware, 
    secret_key=settings.SECRET_KEY
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.state.oauth = oauth

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(sections.router)
app.include_router(blocks.router)
app.include_router(cv_analyzer.router)
app.include_router(cover_letter.router)
app.include_router(resume.router)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to Resume Builder API",
        "version": "1.0.0",
        "docs": "/docs"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )