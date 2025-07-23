"""
Web3 Integration Service for MAMS

This service provides comprehensive Web3 features including:
- Decentralized Identity (DID) support
- Web3 wallet connectivity
- Token-gated access control
- IPFS integration
- ENS integration
- Cross-chain asset management
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
import uvicorn

from core.config import settings
from core.logging import setup_logging
from db.base import init_db
from api import (
    auth_routes,
    identity_routes,
    storage_routes,
    token_gate_routes,
    wallet_routes,
    ens_routes,
    cross_chain_routes,
    analytics_routes,
    nft_marketplace_routes
)

# Setup logging
logger = setup_logging(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Web3 Integration Service...")
    
    # Initialize database
    await init_db()
    
    # Initialize Web3 connections
    from services.web3_connector import Web3ConnectorService
    connector = Web3ConnectorService()
    await connector.initialize()
    
    # Initialize IPFS client
    from services.ipfs_service import IPFSService
    ipfs = IPFSService()
    await ipfs.initialize()
    
    yield
    
    # Cleanup
    logger.info("Shutting down Web3 Integration Service...")
    await connector.cleanup()
    await ipfs.cleanup()

# Create FastAPI app
app = FastAPI(
    title="MAMS Web3 Integration Service",
    description="Comprehensive Web3 features for decentralized media management",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include routers
app.include_router(auth_routes.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(identity_routes.router, prefix="/api/v1/identity", tags=["Decentralized Identity"])
app.include_router(wallet_routes.router, prefix="/api/v1/wallet", tags=["Wallet Management"])
app.include_router(storage_routes.router, prefix="/api/v1/storage", tags=["Decentralized Storage"])
app.include_router(token_gate_routes.router, prefix="/api/v1/token-gate", tags=["Token Gating"])
app.include_router(ens_routes.router, prefix="/api/v1/ens", tags=["ENS"])
app.include_router(cross_chain_routes.router, prefix="/api/v1/cross-chain", tags=["Cross-Chain"])
app.include_router(analytics_routes.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(nft_marketplace_routes.router, prefix="/api/v1/marketplace", tags=["NFT Marketplace"])

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "service": "MAMS Web3 Integration Service",
        "version": "1.0.0",
        "status": "operational",
        "features": [
            "Decentralized Identity (DID)",
            "Web3 Wallet Connectivity",
            "Token-Gated Access",
            "IPFS Storage",
            "ENS Integration",
            "Cross-Chain Support",
            "NFT Marketplace Integration"
        ]
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    try:
        # Check database
        from db.base import get_db
        async for db in get_db():
            await db.execute("SELECT 1")
        
        # Check Web3 connection
        from services.web3_connector import Web3ConnectorService
        connector = Web3ConnectorService()
        eth_connected = await connector.check_connection("ethereum")
        
        # Check IPFS
        from services.ipfs_service import IPFSService
        ipfs = IPFSService()
        ipfs_connected = await ipfs.check_connection()
        
        return {
            "status": "healthy",
            "services": {
                "database": "connected",
                "ethereum": "connected" if eth_connected else "disconnected",
                "ipfs": "connected" if ipfs_connected else "disconnected"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.get("/capabilities", tags=["Capabilities"])
async def get_capabilities():
    """Get service capabilities"""
    return {
        "identity": {
            "did_methods": ["did:ethr", "did:web", "did:key"],
            "verifiable_credentials": True,
            "ssi_support": True
        },
        "wallets": {
            "supported": ["MetaMask", "WalletConnect", "Coinbase Wallet", "Trust Wallet"],
            "multi_chain": True,
            "hardware_wallet_support": True
        },
        "chains": {
            "ethereum": {
                "mainnet": True,
                "goerli": True,
                "sepolia": True
            },
            "polygon": {
                "mainnet": True,
                "mumbai": True
            },
            "binance_smart_chain": {
                "mainnet": True,
                "testnet": True
            },
            "avalanche": {
                "mainnet": True,
                "fuji": True
            },
            "arbitrum": {
                "mainnet": True,
                "goerli": True
            },
            "optimism": {
                "mainnet": True,
                "goerli": True
            }
        },
        "storage": {
            "ipfs": {
                "pinning": True,
                "gateway": True,
                "cluster": True
            },
            "filecoin": {
                "deals": True,
                "retrieval": True
            },
            "arweave": {
                "permanent_storage": True
            }
        },
        "token_gating": {
            "erc20": True,
            "erc721": True,
            "erc1155": True,
            "custom_rules": True,
            "time_based": True
        },
        "marketplace": {
            "opensea": True,
            "rarible": True,
            "custom": True,
            "royalties": True,
            "auctions": True
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )