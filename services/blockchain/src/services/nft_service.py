"""
NFT service for comprehensive NFT functionality and marketplace operations.
"""
import asyncio
import json
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
import uuid

from web3 import Web3
from eth_utils import to_checksum_address
import structlog

from ..core.config import settings
from ..db.models import (
    BlockchainAsset, MediaRights, RightsLicense, BlockchainTransaction,
    RoyaltyPayment, NetworkType, TransactionStatus, RightsType, LicenseStatus
)
from .blockchain_service import BlockchainService
from .ipfs_service import IPFSService

logger = structlog.get_logger()


class NFTError(Exception):
    """Base exception for NFT operations."""
    pass


class NFTMintingError(NFTError):
    """Raised when NFT minting fails."""
    pass


class NFTTransferError(NFTError):
    """Raised when NFT transfer fails."""
    pass


class NFTMarketplaceError(NFTError):
    """Raised when marketplace operations fail."""
    pass


class NFTService:
    """Comprehensive NFT service for digital media assets."""
    
    def __init__(self):
        self.blockchain_service = BlockchainService()
        self.ipfs_service = IPFSService()
        self.nft_contract_abi = self._load_nft_contract_abi()
    
    def _load_nft_contract_abi(self) -> List[Dict]:
        """Load NFT contract ABI with marketplace functionality."""
        return [
            # ERC-721 Standard Functions
            {
                "inputs": [
                    {"name": "to", "type": "address"},
                    {"name": "tokenId", "type": "uint256"}
                ],
                "name": "mint",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "from", "type": "address"},
                    {"name": "to", "type": "address"},
                    {"name": "tokenId", "type": "uint256"}
                ],
                "name": "transferFrom",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"name": "tokenId", "type": "uint256"}],
                "name": "ownerOf",
                "outputs": [{"name": "", "type": "address"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"name": "tokenId", "type": "uint256"}],
                "name": "tokenURI",
                "outputs": [{"name": "", "type": "string"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "to", "type": "address"},
                    {"name": "approved", "type": "bool"}
                ],
                "name": "setApprovalForAll",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            # NFT Marketplace Functions
            {
                "inputs": [
                    {"name": "tokenId", "type": "uint256"},
                    {"name": "price", "type": "uint256"},
                    {"name": "duration", "type": "uint256"}
                ],
                "name": "listForSale",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"name": "tokenId", "type": "uint256"}],
                "name": "buyNFT",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "tokenId", "type": "uint256"},
                    {"name": "bidAmount", "type": "uint256"}
                ],
                "name": "placeBid",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "inputs": [{"name": "tokenId", "type": "uint256"}],
                "name": "acceptBid",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"name": "tokenId", "type": "uint256"}],
                "name": "cancelListing",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            # Royalty Functions
            {
                "inputs": [
                    {"name": "tokenId", "type": "uint256"},
                    {"name": "recipient", "type": "address"},
                    {"name": "percentage", "type": "uint256"}
                ],
                "name": "setRoyalty",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "tokenId", "type": "uint256"},
                    {"name": "salePrice", "type": "uint256"}
                ],
                "name": "royaltyInfo",
                "outputs": [
                    {"name": "recipient", "type": "address"},
                    {"name": "royaltyAmount", "type": "uint256"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            # Events
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "name": "from", "type": "address"},
                    {"indexed": True, "name": "to", "type": "address"},
                    {"indexed": True, "name": "tokenId", "type": "uint256"}
                ],
                "name": "Transfer",
                "type": "event"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "name": "tokenId", "type": "uint256"},
                    {"indexed": False, "name": "seller", "type": "address"},
                    {"indexed": False, "name": "price", "type": "uint256"}
                ],
                "name": "NFTListed",
                "type": "event"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "name": "tokenId", "type": "uint256"},
                    {"indexed": False, "name": "buyer", "type": "address"},
                    {"indexed": False, "name": "seller", "type": "address"},
                    {"indexed": False, "name": "price", "type": "uint256"}
                ],
                "name": "NFTSold",
                "type": "event"
            }
        ]
    
    async def create_nft_metadata(
        self,
        asset_data: Dict[str, Any],
        nft_properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create comprehensive NFT metadata following standards."""
        metadata = {
            # OpenSea/ERC-721 Standard
            "name": nft_properties.get("name", asset_data.get("title", "Untitled NFT")),
            "description": nft_properties.get("description", asset_data.get("description", "")),
            "image": nft_properties.get("image_uri", ""),
            "external_url": nft_properties.get("external_url", ""),
            
            # Additional Media Properties
            "animation_url": nft_properties.get("animation_url", ""),  # For videos/interactive content
            "youtube_url": nft_properties.get("youtube_url", ""),
            
            # Attributes for filtering and searching
            "attributes": [
                {
                    "trait_type": "Media Type",
                    "value": asset_data.get("file_type", "unknown")
                },
                {
                    "trait_type": "File Size",
                    "value": asset_data.get("file_size", 0),
                    "display_type": "number"
                },
                {
                    "trait_type": "Duration",
                    "value": asset_data.get("duration", 0),
                    "display_type": "number"
                },
                {
                    "trait_type": "Resolution",
                    "value": asset_data.get("resolution", "unknown")
                },
                {
                    "trait_type": "Creator",
                    "value": asset_data.get("creator", "unknown")
                },
                {
                    "trait_type": "Created Date",
                    "value": asset_data.get("created_date", datetime.now(timezone.utc).isoformat()),
                    "display_type": "date"
                },
                {
                    "trait_type": "Rarity",
                    "value": nft_properties.get("rarity", "common")
                },
                {
                    "trait_type": "Collection",
                    "value": nft_properties.get("collection", "MAMS Media")
                }
            ],
            
            # Additional custom attributes
            "properties": {
                "asset_id": str(asset_data.get("id", "")),
                "blockchain_network": nft_properties.get("network", settings.default_network),
                "royalty_percentage": nft_properties.get("royalty_percentage", 5.0),
                "minted_at": datetime.now(timezone.utc).isoformat(),
                "content_hash": asset_data.get("checksum", ""),
                "license_type": nft_properties.get("license_type", "standard"),
                "commercial_use": nft_properties.get("commercial_use", False),
                "derivative_works": nft_properties.get("derivative_works", False),
                "territories": nft_properties.get("territories", []),
                "languages": nft_properties.get("languages", []),
                "tags": nft_properties.get("tags", []),
                "categories": nft_properties.get("categories", [])
            },
            
            # Technical metadata
            "technical": {
                "file_format": asset_data.get("file_format", ""),
                "codec": asset_data.get("codec", ""),
                "bitrate": asset_data.get("bitrate", 0),
                "frame_rate": asset_data.get("frame_rate", 0),
                "color_space": asset_data.get("color_space", ""),
                "audio_channels": asset_data.get("audio_channels", 0),
                "sample_rate": asset_data.get("sample_rate", 0)
            },
            
            # Rights and licensing
            "rights": {
                "usage_rights": nft_properties.get("usage_rights", []),
                "restrictions": nft_properties.get("restrictions", []),
                "expiration": nft_properties.get("expiration", None),
                "transferable": nft_properties.get("transferable", True),
                "sublicensable": nft_properties.get("sublicensable", False)
            }
        }
        
        # Add custom attributes from nft_properties
        custom_attributes = nft_properties.get("custom_attributes", [])
        metadata["attributes"].extend(custom_attributes)
        
        return metadata
    
    async def mint_nft(
        self,
        asset_id: uuid.UUID,
        recipient_address: str,
        nft_properties: Dict[str, Any],
        network: str = None
    ) -> Dict[str, Any]:
        """Mint a new NFT from media asset."""
        network = network or settings.default_network
        
        try:
            # Get asset data (this would normally come from asset service)
            asset_data = {
                "id": str(asset_id),
                "title": nft_properties.get("title", "Media NFT"),
                "description": nft_properties.get("description", ""),
                "file_type": nft_properties.get("file_type", "image"),
                "file_size": nft_properties.get("file_size", 0),
                "creator": nft_properties.get("creator", recipient_address),
                "created_date": datetime.now(timezone.utc).isoformat()
            }
            
            # Create NFT metadata
            nft_metadata = await self.create_nft_metadata(asset_data, nft_properties)
            
            # Upload metadata to IPFS
            metadata_result = await self.ipfs_service.upload_json(
                nft_metadata,
                asset_id=asset_id,
                content_type="nft_metadata",
                pin=True
            )
            
            # Generate token ID
            token_id = int(str(asset_id).replace("-", ""), 16) % (2**256)
            
            # Get network and contract
            w3 = self.blockchain_service.get_network(network)
            contract_address = self.blockchain_service._get_contract_address(network, "nft")
            
            if not contract_address:
                raise NFTMintingError(f"No NFT contract deployed on {network}")
            
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.nft_contract_abi
            )
            
            # Build mint transaction
            transaction = contract.functions.mint(
                to_checksum_address(recipient_address),
                token_id
            ).build_transaction({
                'from': self.blockchain_service.account.address,
                'gas': settings.gas_limit,
                'gasPrice': w3.to_wei(settings.gas_price_gwei, 'gwei'),
                'nonce': w3.eth.get_transaction_count(self.blockchain_service.account.address)
            })
            
            # Sign and send transaction
            signed_txn = self.blockchain_service.account.sign_transaction(transaction)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for confirmation
            receipt = await self.blockchain_service._wait_for_confirmation(w3, tx_hash)
            
            # Set royalty if specified
            royalty_percentage = nft_properties.get("royalty_percentage", 0)
            royalty_recipient = nft_properties.get("royalty_recipient", recipient_address)
            
            if royalty_percentage > 0:
                await self._set_nft_royalty(
                    token_id,
                    royalty_recipient,
                    royalty_percentage,
                    network
                )
            
            result = {
                "token_id": token_id,
                "contract_address": contract_address,
                "transaction_hash": receipt['transactionHash'].hex(),
                "block_number": receipt['blockNumber'],
                "owner_address": recipient_address,
                "metadata_uri": metadata_result["gateway_url"],
                "ipfs_hash": metadata_result["ipfs_hash"],
                "network": network,
                "gas_used": receipt['gasUsed'],
                "status": "success" if receipt['status'] == 1 else "failed",
                "royalty_percentage": royalty_percentage,
                "royalty_recipient": royalty_recipient
            }
            
            logger.info(f"NFT minted successfully: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to mint NFT: {e}")
            raise NFTMintingError(f"NFT minting failed: {e}")
    
    async def _set_nft_royalty(
        self,
        token_id: int,
        recipient_address: str,
        percentage: float,
        network: str
    ) -> Dict[str, Any]:
        """Set royalty information for an NFT."""
        try:
            w3 = self.blockchain_service.get_network(network)
            contract_address = self.blockchain_service._get_contract_address(network, "nft")
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.nft_contract_abi
            )
            
            # Convert percentage to basis points (e.g., 5% = 500)
            basis_points = int(percentage * 100)
            
            transaction = contract.functions.setRoyalty(
                token_id,
                to_checksum_address(recipient_address),
                basis_points
            ).build_transaction({
                'from': self.blockchain_service.account.address,
                'gas': settings.gas_limit,
                'gasPrice': w3.to_wei(settings.gas_price_gwei, 'gwei'),
                'nonce': w3.eth.get_transaction_count(self.blockchain_service.account.address)
            })
            
            signed_txn = self.blockchain_service.account.sign_transaction(transaction)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            receipt = await self.blockchain_service._wait_for_confirmation(w3, tx_hash)
            
            return {
                "transaction_hash": receipt['transactionHash'].hex(),
                "status": "success" if receipt['status'] == 1 else "failed"
            }
            
        except Exception as e:
            logger.error(f"Failed to set royalty: {e}")
            raise NFTError(f"Royalty setting failed: {e}")
    
    async def transfer_nft(
        self,
        token_id: int,
        from_address: str,
        to_address: str,
        network: str = None
    ) -> Dict[str, Any]:
        """Transfer NFT ownership."""
        network = network or settings.default_network
        
        try:
            w3 = self.blockchain_service.get_network(network)
            contract_address = self.blockchain_service._get_contract_address(network, "nft")
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.nft_contract_abi
            )
            
            # Build transfer transaction
            transaction = contract.functions.transferFrom(
                to_checksum_address(from_address),
                to_checksum_address(to_address),
                token_id
            ).build_transaction({
                'from': self.blockchain_service.account.address,
                'gas': settings.gas_limit,
                'gasPrice': w3.to_wei(settings.gas_price_gwei, 'gwei'),
                'nonce': w3.eth.get_transaction_count(self.blockchain_service.account.address)
            })
            
            signed_txn = self.blockchain_service.account.sign_transaction(transaction)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            receipt = await self.blockchain_service._wait_for_confirmation(w3, tx_hash)
            
            result = {
                "token_id": token_id,
                "from_address": from_address,
                "to_address": to_address,
                "transaction_hash": receipt['transactionHash'].hex(),
                "block_number": receipt['blockNumber'],
                "network": network,
                "gas_used": receipt['gasUsed'],
                "status": "success" if receipt['status'] == 1 else "failed"
            }
            
            logger.info(f"NFT transferred: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to transfer NFT: {e}")
            raise NFTTransferError(f"NFT transfer failed: {e}")
    
    async def get_nft_info(
        self,
        token_id: int,
        network: str = None
    ) -> Dict[str, Any]:
        """Get comprehensive NFT information."""
        network = network or settings.default_network
        
        try:
            w3 = self.blockchain_service.get_network(network)
            contract_address = self.blockchain_service._get_contract_address(network, "nft")
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.nft_contract_abi
            )
            
            # Get basic NFT info
            owner = contract.functions.ownerOf(token_id).call()
            token_uri = contract.functions.tokenURI(token_id).call()
            
            # Get royalty info
            try:
                royalty_info = contract.functions.royaltyInfo(token_id, w3.to_wei(1, 'ether')).call()
                royalty_recipient = royalty_info[0]
                royalty_amount = royalty_info[1]
                royalty_percentage = w3.from_wei(royalty_amount, 'ether') * 100
            except Exception:
                royalty_recipient = None
                royalty_percentage = 0
            
            # Download metadata from IPFS
            metadata = {}
            if token_uri.startswith('ipfs://'):
                ipfs_hash = token_uri.replace('ipfs://', '')
                try:
                    metadata_result = await self.ipfs_service.download_json(ipfs_hash)
                    metadata = metadata_result.get("data", {})
                except Exception as e:
                    logger.warning(f"Failed to load metadata from IPFS: {e}")
            
            nft_info = {
                "token_id": token_id,
                "contract_address": contract_address,
                "owner": owner,
                "token_uri": token_uri,
                "metadata": metadata,
                "royalty_recipient": royalty_recipient,
                "royalty_percentage": royalty_percentage,
                "network": network,
                "retrieved_at": datetime.now(timezone.utc).isoformat()
            }
            
            return nft_info
            
        except Exception as e:
            logger.error(f"Failed to get NFT info: {e}")
            raise NFTError(f"NFT info retrieval failed: {e}")
    
    async def list_nft_for_sale(
        self,
        token_id: int,
        price: Decimal,
        duration_hours: int = 168,  # 1 week default
        network: str = None
    ) -> Dict[str, Any]:
        """List NFT for sale on marketplace."""
        network = network or settings.default_network
        
        try:
            w3 = self.blockchain_service.get_network(network)
            contract_address = self.blockchain_service._get_contract_address(network, "nft")
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.nft_contract_abi
            )
            
            price_wei = w3.to_wei(price, 'ether')
            duration_seconds = duration_hours * 3600
            
            # Build listing transaction
            transaction = contract.functions.listForSale(
                token_id,
                price_wei,
                duration_seconds
            ).build_transaction({
                'from': self.blockchain_service.account.address,
                'gas': settings.gas_limit,
                'gasPrice': w3.to_wei(settings.gas_price_gwei, 'gwei'),
                'nonce': w3.eth.get_transaction_count(self.blockchain_service.account.address)
            })
            
            signed_txn = self.blockchain_service.account.sign_transaction(transaction)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            receipt = await self.blockchain_service._wait_for_confirmation(w3, tx_hash)
            
            result = {
                "token_id": token_id,
                "price": str(price),
                "duration_hours": duration_hours,
                "expires_at": (datetime.now(timezone.utc) + timedelta(hours=duration_hours)).isoformat(),
                "transaction_hash": receipt['transactionHash'].hex(),
                "block_number": receipt['blockNumber'],
                "network": network,
                "status": "listed" if receipt['status'] == 1 else "failed"
            }
            
            logger.info(f"NFT listed for sale: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to list NFT for sale: {e}")
            raise NFTMarketplaceError(f"NFT listing failed: {e}")
    
    async def buy_nft(
        self,
        token_id: int,
        buyer_address: str,
        network: str = None
    ) -> Dict[str, Any]:
        """Buy an NFT from marketplace."""
        network = network or settings.default_network
        
        try:
            w3 = self.blockchain_service.get_network(network)
            contract_address = self.blockchain_service._get_contract_address(network, "nft")
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.nft_contract_abi
            )
            
            # Get NFT price (this would normally be stored or queried from contract)
            # For now, we'll assume the price is provided separately
            # In a real implementation, you'd query the listing price from the contract
            
            transaction = contract.functions.buyNFT(token_id).build_transaction({
                'from': to_checksum_address(buyer_address),
                'gas': settings.gas_limit,
                'gasPrice': w3.to_wei(settings.gas_price_gwei, 'gwei'),
                'nonce': w3.eth.get_transaction_count(buyer_address)
            })
            
            # Note: In production, this would be signed by the buyer's wallet
            signed_txn = self.blockchain_service.account.sign_transaction(transaction)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            receipt = await self.blockchain_service._wait_for_confirmation(w3, tx_hash)
            
            result = {
                "token_id": token_id,
                "buyer": buyer_address,
                "transaction_hash": receipt['transactionHash'].hex(),
                "block_number": receipt['blockNumber'],
                "network": network,
                "status": "purchased" if receipt['status'] == 1 else "failed"
            }
            
            logger.info(f"NFT purchased: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to buy NFT: {e}")
            raise NFTMarketplaceError(f"NFT purchase failed: {e}")
    
    async def place_bid(
        self,
        token_id: int,
        bidder_address: str,
        bid_amount: Decimal,
        network: str = None
    ) -> Dict[str, Any]:
        """Place a bid on an NFT."""
        network = network or settings.default_network
        
        try:
            w3 = self.blockchain_service.get_network(network)
            contract_address = self.blockchain_service._get_contract_address(network, "nft")
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.nft_contract_abi
            )
            
            bid_wei = w3.to_wei(bid_amount, 'ether')
            
            transaction = contract.functions.placeBid(
                token_id,
                bid_wei
            ).build_transaction({
                'from': to_checksum_address(bidder_address),
                'value': bid_wei,
                'gas': settings.gas_limit,
                'gasPrice': w3.to_wei(settings.gas_price_gwei, 'gwei'),
                'nonce': w3.eth.get_transaction_count(bidder_address)
            })
            
            signed_txn = self.blockchain_service.account.sign_transaction(transaction)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            receipt = await self.blockchain_service._wait_for_confirmation(w3, tx_hash)
            
            result = {
                "token_id": token_id,
                "bidder": bidder_address,
                "bid_amount": str(bid_amount),
                "transaction_hash": receipt['transactionHash'].hex(),
                "block_number": receipt['blockNumber'],
                "network": network,
                "status": "bid_placed" if receipt['status'] == 1 else "failed"
            }
            
            logger.info(f"NFT bid placed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to place bid: {e}")
            raise NFTMarketplaceError(f"Bid placement failed: {e}")
    
    async def get_nft_history(
        self,
        token_id: int,
        network: str = None
    ) -> List[Dict[str, Any]]:
        """Get complete history of NFT transactions."""
        network = network or settings.default_network
        
        try:
            w3 = self.blockchain_service.get_network(network)
            contract_address = self.blockchain_service._get_contract_address(network, "nft")
            
            # Get Transfer events for this token
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.nft_contract_abi
            )
            
            # Get all Transfer events for this token ID
            transfer_filter = contract.events.Transfer.create_filter(
                fromBlock=0,
                argument_filters={'tokenId': token_id}
            )
            
            transfers = transfer_filter.get_all_entries()
            
            history = []
            for transfer in transfers:
                event_data = {
                    "event_type": "transfer",
                    "from_address": transfer['args']['from'],
                    "to_address": transfer['args']['to'],
                    "token_id": transfer['args']['tokenId'],
                    "transaction_hash": transfer['transactionHash'].hex(),
                    "block_number": transfer['blockNumber'],
                    "timestamp": self._get_block_timestamp(w3, transfer['blockNumber'])
                }
                history.append(event_data)
            
            # Get marketplace events (listings, sales, bids)
            try:
                # NFTListed events
                listed_filter = contract.events.NFTListed.create_filter(
                    fromBlock=0,
                    argument_filters={'tokenId': token_id}
                )
                
                listings = listed_filter.get_all_entries()
                for listing in listings:
                    event_data = {
                        "event_type": "listed",
                        "seller": listing['args']['seller'],
                        "price": str(w3.from_wei(listing['args']['price'], 'ether')),
                        "token_id": listing['args']['tokenId'],
                        "transaction_hash": listing['transactionHash'].hex(),
                        "block_number": listing['blockNumber'],
                        "timestamp": self._get_block_timestamp(w3, listing['blockNumber'])
                    }
                    history.append(event_data)
                
                # NFTSold events
                sold_filter = contract.events.NFTSold.create_filter(
                    fromBlock=0,
                    argument_filters={'tokenId': token_id}
                )
                
                sales = sold_filter.get_all_entries()
                for sale in sales:
                    event_data = {
                        "event_type": "sold",
                        "buyer": sale['args']['buyer'],
                        "seller": sale['args']['seller'],
                        "price": str(w3.from_wei(sale['args']['price'], 'ether')),
                        "token_id": sale['args']['tokenId'],
                        "transaction_hash": sale['transactionHash'].hex(),
                        "block_number": sale['blockNumber'],
                        "timestamp": self._get_block_timestamp(w3, sale['blockNumber'])
                    }
                    history.append(event_data)
                    
            except Exception as e:
                logger.warning(f"Failed to get marketplace events: {e}")
            
            # Sort by block number
            history.sort(key=lambda x: x['block_number'])
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get NFT history: {e}")
            raise NFTError(f"NFT history retrieval failed: {e}")
    
    def _get_block_timestamp(self, w3: Web3, block_number: int) -> str:
        """Get timestamp for a block."""
        try:
            block = w3.eth.get_block(block_number)
            return datetime.fromtimestamp(block['timestamp'], tz=timezone.utc).isoformat()
        except Exception:
            return datetime.now(timezone.utc).isoformat()
    
    async def batch_mint_nfts(
        self,
        mint_requests: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Batch mint multiple NFTs."""
        results = []
        
        # Process in batches to avoid overwhelming the network
        batch_size = 5
        for i in range(0, len(mint_requests), batch_size):
            batch = mint_requests[i:i + batch_size]
            
            # Process batch concurrently
            tasks = []
            for request in batch:
                task = self.mint_nft(
                    request['asset_id'],
                    request['recipient_address'],
                    request['nft_properties'],
                    request.get('network')
                )
                tasks.append(task)
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions in results
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    results.append({
                        "asset_id": batch[j]['asset_id'],
                        "error": str(result),
                        "status": "failed"
                    })
                else:
                    results.append(result)
            
            # Add delay between batches to respect rate limits
            if i + batch_size < len(mint_requests):
                await asyncio.sleep(2)
        
        return results
    
    async def get_collection_stats(
        self,
        collection_name: str,
        network: str = None
    ) -> Dict[str, Any]:
        """Get statistics for an NFT collection."""
        # This would normally query multiple NFTs from the same collection
        # For now, return placeholder statistics
        stats = {
            "collection_name": collection_name,
            "network": network or settings.default_network,
            "total_supply": 0,
            "owners": 0,
            "floor_price": "0.0",
            "volume_traded": "0.0",
            "average_price": "0.0",
            "listings": 0,
            "sales_24h": 0,
            "volume_24h": "0.0",
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
        return stats
    
    async def search_nfts(
        self,
        criteria: Dict[str, Any],
        network: str = None
    ) -> List[Dict[str, Any]]:
        """Search NFTs based on various criteria."""
        # This would normally integrate with a comprehensive NFT indexing service
        # For now, return placeholder search functionality
        
        search_results = []
        
        # Example search criteria:
        # - owner_address
        # - collection
        # - traits/attributes
        # - price_range
        # - rarity
        
        return search_results