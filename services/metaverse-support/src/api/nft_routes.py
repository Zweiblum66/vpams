"""NFT-specific API routes"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/collection/{collection_id}")
async def get_nft_collection(collection_id: str):
    """Get NFT collection details"""
    return {
        "collection_id": collection_id,
        "status": "active"
    }

@router.post("/transfer")
async def transfer_nft():
    """Transfer NFT ownership"""
    return {"status": "transferred"}