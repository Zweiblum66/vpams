from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import structlog
from prometheus_client import make_asgi_app

from .core.config import settings
from .db.base import init_db, close_db
from .api import quantum_keys, analytics
from .models.schemas import HealthResponse, AlgorithmType

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    logger.info("Starting Quantum Encryption Service", 
               service=settings.service_name,
               port=settings.service_port)
    
    # Initialize database
    await init_db()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Quantum Encryption Service")
    await close_db()

# Create FastAPI app
app = FastAPI(
    title="MAMS Quantum Encryption Service",
    description="Post-quantum cryptography service for MAMS platform",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(quantum_keys.router)
app.include_router(analytics.router)

# Mount Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint."""
    return {
        "service": "MAMS Quantum Encryption Service",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    supported_algorithms = [
        # KEMs
        AlgorithmType.KYBER512,
        AlgorithmType.KYBER768,
        AlgorithmType.KYBER1024,
        AlgorithmType.NTRU_HPS2048509,
        AlgorithmType.NTRU_HPS2048677,
        AlgorithmType.NTRU_HPS4096821,
        AlgorithmType.SABER_LIGHT,
        AlgorithmType.SABER,
        AlgorithmType.SABER_FIRE,
        # Signatures
        AlgorithmType.DILITHIUM2,
        AlgorithmType.DILITHIUM3,
        AlgorithmType.DILITHIUM5,
        AlgorithmType.FALCON512,
        AlgorithmType.FALCON1024,
        AlgorithmType.SPHINCS_SHA256_128F,
        AlgorithmType.SPHINCS_SHA256_192F,
        AlgorithmType.SPHINCS_SHA256_256F,
        # Classical (for hybrid)
        AlgorithmType.RSA2048,
        AlgorithmType.RSA4096,
        AlgorithmType.ECC_P256,
        AlgorithmType.ECC_P384,
        AlgorithmType.ECC_P521,
        AlgorithmType.AES256,
    ]
    
    return HealthResponse(
        status="healthy",
        service="quantum-encryption",
        version="1.0.0",
        quantum_ready=True,
        supported_algorithms=supported_algorithms
    )

@app.get("/api/v1/quantum/capabilities")
async def get_quantum_capabilities():
    """Get detailed quantum encryption capabilities."""
    return {
        "service": "MAMS Quantum Encryption Service",
        "version": "1.0.0",
        "capabilities": {
            "key_encapsulation_mechanisms": {
                "kyber": ["512", "768", "1024"],
                "ntru": ["hps2048509", "hps2048677", "hps4096821"],
                "saber": ["light", "standard", "fire"]
            },
            "digital_signatures": {
                "dilithium": ["2", "3", "5"],
                "falcon": ["512", "1024"],
                "sphincs+": ["sha256-128f", "sha256-192f", "sha256-256f"]
            },
            "hybrid_mode": {
                "supported": True,
                "classical_algorithms": ["RSA-2048", "RSA-4096", "ECC-P256", "ECC-P384", "ECC-P521", "AES-256"]
            },
            "features": [
                "Key generation and management",
                "Quantum-resistant encryption/decryption",
                "Digital signatures",
                "Key rotation with data migration",
                "Hybrid classical-quantum encryption",
                "Batch operations",
                "Key expiration management",
                "Security assessment and analytics",
                "Algorithm migration planning"
            ],
            "security_levels": {
                "NIST_Level_1": "128-bit classical security",
                "NIST_Level_2": "192-bit classical security",
                "NIST_Level_3": "256-bit classical security",
                "NIST_Level_4": "384-bit classical security",
                "NIST_Level_5": "512-bit classical security"
            },
            "performance": {
                "max_concurrent_operations": settings.max_concurrent_operations,
                "key_caching_enabled": settings.enable_key_caching,
                "batch_processing_supported": True
            },
            "compliance": {
                "standards": ["NIST PQC", "ETSI QSC", "ISO/IEC 14888-3"],
                "key_rotation_days": settings.key_rotation_days,
                "max_key_age_days": settings.max_key_age_days
            }
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )