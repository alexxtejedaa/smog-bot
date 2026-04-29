"""
SMOG Bot — FastAPI Application Entry Point

Skeleton only. No trading logic yet.
"""

from fastapi import FastAPI
from src.config import settings
from src.routes.webhook import webhook_router

# Initialize FastAPI app
app = FastAPI(
    title="SMOG Bot",
    description="TradingView webhook handler for MEXC futures",
    version="0.1.0",
)

# Include routers
app.include_router(webhook_router, tags=["webhooks"])

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "SMOG Bot",
        "version": "0.1.0",
    }

@app.get("/health")
async def health():
    """Kubernetes-style health check"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )
