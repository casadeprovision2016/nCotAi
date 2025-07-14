"""
COTAI AI Engine Service
Advanced AI/ML service for tender document analysis and intelligent scoring
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.api.routes import router
from app.services.ai_models import AIModelManager
from app.services.cache import CacheManager
from app.services.scoring import ScoringEngine

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    settings = get_settings()
    
    # Initialize telemetry
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)
    
    jaeger_exporter = JaegerExporter(
        agent_host_name=settings.jaeger_host,
        agent_port=settings.jaeger_port,
    )
    
    span_processor = BatchSpanProcessor(jaeger_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
    
    # Initialize AI models
    logger.info("Loading AI models...")
    ai_manager = AIModelManager()
    await ai_manager.load_models()
    app.state.ai_manager = ai_manager
    
    # Initialize cache
    cache_manager = CacheManager(settings.redis_url)
    await cache_manager.connect()
    app.state.cache_manager = cache_manager
    
    # Initialize scoring engine
    scoring_engine = ScoringEngine(ai_manager, cache_manager)
    app.state.scoring_engine = scoring_engine
    
    logger.info("AI Engine service started successfully")
    
    yield
    
    # Cleanup
    await cache_manager.disconnect()
    logger.info("AI Engine service stopped")


def create_app() -> FastAPI:
    """Create FastAPI application"""
    settings = get_settings()
    
    app = FastAPI(
        title="COTAI AI Engine",
        description="Advanced AI/ML service for tender document analysis",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(router, prefix="/api/v1")
    
    # Instrument with OpenTelemetry
    FastAPIInstrumentor.instrument_app(app)
    
    return app


app = create_app()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "cotai-ai-engine",
        "version": "1.0.0"
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    try:
        # Check if AI models are loaded
        ai_manager = getattr(app.state, 'ai_manager', None)
        if not ai_manager or not ai_manager.models_loaded:
            return {"status": "not ready", "reason": "AI models not loaded"}, 503
            
        # Check cache connection
        cache_manager = getattr(app.state, 'cache_manager', None)
        if not cache_manager or not await cache_manager.ping():
            return {"status": "not ready", "reason": "Cache not available"}, 503
            
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"status": "not ready", "reason": str(e)}, 503


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )