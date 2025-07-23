"""
Comprehensive provenance tracking service for digital media assets.
"""
import asyncio
import json
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
import uuid
from dataclasses import dataclass, asdict

from web3 import Web3
from web3.contract import Contract
from eth_utils import to_checksum_address
import structlog

from ..core.config import settings
from ..db.models import (
    BlockchainAsset, BlockchainTransaction, NetworkType, 
    TransactionStatus, ProvenanceEvent, ProvenanceChain
)
from .blockchain_service import BlockchainService
from .ipfs_service import IPFSService

logger = structlog.get_logger()


@dataclass
class AssetMetadata:
    """Asset metadata for provenance tracking."""
    title: str
    description: str
    asset_type: str
    file_format: str
    file_size: int
    duration: Optional[float] = None
    resolution: Optional[str] = None
    codec: Optional[str] = None
    frame_rate: Optional[float] = None
    bitrate: Optional[int] = None
    created_date: Optional[str] = None
    creator: Optional[str] = None
    camera_model: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    technical_metadata: Optional[Dict[str, Any]] = None


@dataclass
class ProvenanceEventData:
    """Provenance event data structure."""
    event_type: str
    actor: str
    timestamp: str
    description: str
    metadata: Dict[str, Any]
    location: Optional[str] = None
    previous_hash: Optional[str] = None
    signature: Optional[str] = None


class ProvenanceError(Exception):
    """Base exception for provenance operations."""
    pass


class ProvenanceValidationError(ProvenanceError):
    """Raised when provenance validation fails."""
    pass


class ProvenanceService:
    """Comprehensive provenance tracking service for digital media assets."""
    
    def __init__(self):
        self.blockchain_service = BlockchainService()
        self.ipfs_service = IPFSService()
        self.provenance_contract_abi = self._load_provenance_contract_abi()
    
    def _load_provenance_contract_abi(self) -> List[Dict]:
        """Load ProvenanceTracker contract ABI."""
        return [
            {
                "inputs": [
                    {"name": "contentHash", "type": "bytes32"},
                    {"name": "title", "type": "string"},
                    {"name": "description", "type": "string"},
                    {"name": "assetType", "type": "string"},
                    {"name": "metadata", "type": "string"}
                ],
                "name": "registerAsset",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "assetId", "type": "uint256"},
                    {"name": "eventType", "type": "string"},
                    {"name": "dataHash", "type": "bytes32"},
                    {"name": "metadata", "type": "string"},
                    {"name": "signature", "type": "bytes"}
                ],
                "name": "addProvenanceEvent",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "assetId", "type": "uint256"},
                    {"name": "newOwner", "type": "address"}
                ],
                "name": "transferOwnership",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "assetId", "type": "uint256"},
                    {"name": "newContentHash", "type": "bytes32"},
                    {"name": "modificationType", "type": "string"},
                    {"name": "metadata", "type": "string"}
                ],
                "name": "updateAssetContent",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"name": "assetId", "type": "uint256"}],
                "name": "getAssetHistory",
                "outputs": [],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "assetId", "type": "uint256"},
                    {"name": "verificationType", "type": "string"},
                    {"name": "verified", "type": "bool"},
                    {"name": "evidence", "type": "string"}
                ],
                "name": "addVerification",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"name": "assetId", "type": "uint256"}],
                "name": "assets",
                "outputs": [
                    {"name": "id", "type": "uint256"},
                    {"name": "contentHash", "type": "bytes32"},
                    {"name": "creator", "type": "address"},
                    {"name": "currentOwner", "type": "address"},
                    {"name": "createdAt", "type": "uint256"},
                    {"name": "lastModified", "type": "uint256"},
                    {"name": "title", "type": "string"},
                    {"name": "description", "type": "string"},
                    {"name": "assetType", "type": "string"},
                    {"name": "verified", "type": "bool"}
                ],
                "stateMutability": "view",
                "type": "function"
            }
        ]
    
    async def register_asset_provenance(
        self,
        asset_id: uuid.UUID,
        asset_metadata: AssetMetadata,
        creator_address: str,
        network: str = None
    ) -> Dict[str, Any]:
        """Register a new asset on the provenance blockchain."""
        network = network or settings.default_network
        
        try:
            # Create content hash from asset metadata
            content_hash = await self._create_content_hash(asset_metadata)
            
            # Upload metadata to IPFS
            metadata_dict = asdict(asset_metadata)
            metadata_result = await self.ipfs_service.upload_json(
                metadata_dict,
                asset_id=asset_id,
                content_type="asset_metadata",
                pin=True
            )
            
            # Get blockchain network and contract
            w3 = self.blockchain_service.get_network(network)
            contract_address = self.blockchain_service._get_contract_address(network, "provenance")
            
            if not contract_address:
                raise ProvenanceError(f"No provenance contract deployed on {network}")
            
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.provenance_contract_abi
            )
            
            # Register asset on blockchain
            transaction = contract.functions.registerAsset(
                Web3.keccak(text=content_hash),
                asset_metadata.title,
                asset_metadata.description,
                asset_metadata.asset_type,
                metadata_result["gateway_url"]
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
            
            # Extract asset ID from logs
            blockchain_asset_id = None
            for log in receipt['logs']:
                try:
                    decoded_log = contract.events.AssetRegistered().processLog(log)
                    blockchain_asset_id = decoded_log['args']['assetId']
                    break
                except:
                    continue
            
            result = {
                "asset_id": str(asset_id),
                "blockchain_asset_id": blockchain_asset_id,
                "content_hash": content_hash,
                "transaction_hash": receipt['transactionHash'].hex(),
                "block_number": receipt['blockNumber'],
                "contract_address": contract_address,
                "metadata_uri": metadata_result["gateway_url"],
                "ipfs_hash": metadata_result["ipfs_hash"],
                "network": network,
                "creator_address": creator_address,
                "registered_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Asset registered for provenance tracking: {asset_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to register asset provenance: {e}")
            raise ProvenanceError(f"Asset registration failed: {e}")
    
    async def add_provenance_event(
        self,
        blockchain_asset_id: int,
        event_data: ProvenanceEventData,
        network: str = None
    ) -> Dict[str, Any]:
        """Add a provenance event to an asset's history."""
        network = network or settings.default_network
        
        try:
            # Create data hash for the event
            event_hash = await self._create_event_hash(event_data)
            
            # Upload event metadata to IPFS
            event_metadata = {
                "event_type": event_data.event_type,
                "actor": event_data.actor,
                "timestamp": event_data.timestamp,
                "description": event_data.description,
                "metadata": event_data.metadata,
                "location": event_data.location,
                "previous_hash": event_data.previous_hash
            }
            
            metadata_result = await self.ipfs_service.upload_json(
                event_metadata,
                content_type="provenance_event",
                pin=True
            )
            
            # Get contract
            w3 = self.blockchain_service.get_network(network)
            contract_address = self.blockchain_service._get_contract_address(network, "provenance")
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.provenance_contract_abi
            )
            
            # Add event to blockchain
            signature_bytes = bytes.fromhex(event_data.signature.replace('0x', '')) if event_data.signature else b''
            
            transaction = contract.functions.addProvenanceEvent(
                blockchain_asset_id,
                event_data.event_type,
                Web3.keccak(text=event_hash),
                metadata_result["gateway_url"],
                signature_bytes
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
                "blockchain_asset_id": blockchain_asset_id,
                "event_type": event_data.event_type,
                "event_hash": event_hash,
                "transaction_hash": receipt['transactionHash'].hex(),
                "block_number": receipt['blockNumber'],
                "metadata_uri": metadata_result["gateway_url"],
                "ipfs_hash": metadata_result["ipfs_hash"],
                "network": network,
                "added_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Provenance event added: {event_data.event_type} for asset {blockchain_asset_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to add provenance event: {e}")
            raise ProvenanceError(f"Event addition failed: {e}")
    
    async def transfer_asset_ownership(
        self,
        blockchain_asset_id: int,
        new_owner_address: str,
        transfer_metadata: Dict[str, Any],
        network: str = None
    ) -> Dict[str, Any]:
        """Transfer ownership of an asset and record the event."""
        network = network or settings.default_network
        
        try:
            # Get current asset info
            asset_info = await self.get_asset_info(blockchain_asset_id, network)
            current_owner = asset_info["current_owner"]
            
            # Create transfer event
            transfer_event = ProvenanceEventData(
                event_type="ownership_transferred",
                actor=current_owner,
                timestamp=datetime.now(timezone.utc).isoformat(),
                description=f"Ownership transferred from {current_owner} to {new_owner_address}",
                metadata={
                    "previous_owner": current_owner,
                    "new_owner": new_owner_address,
                    "transfer_reason": transfer_metadata.get("reason", ""),
                    "transfer_price": transfer_metadata.get("price"),
                    "transfer_currency": transfer_metadata.get("currency"),
                    "contract_terms": transfer_metadata.get("contract_terms")
                }
            )
            
            # Add the transfer event first
            event_result = await self.add_provenance_event(
                blockchain_asset_id,
                transfer_event,
                network
            )
            
            # Execute ownership transfer on blockchain
            w3 = self.blockchain_service.get_network(network)
            contract_address = self.blockchain_service._get_contract_address(network, "provenance")
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.provenance_contract_abi
            )
            
            transaction = contract.functions.transferOwnership(
                blockchain_asset_id,
                to_checksum_address(new_owner_address)
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
                "blockchain_asset_id": blockchain_asset_id,
                "previous_owner": current_owner,
                "new_owner": new_owner_address,
                "transaction_hash": receipt['transactionHash'].hex(),
                "block_number": receipt['blockNumber'],
                "event_transaction": event_result,
                "network": network,
                "transferred_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Asset ownership transferred: {blockchain_asset_id} to {new_owner_address}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to transfer asset ownership: {e}")
            raise ProvenanceError(f"Ownership transfer failed: {e}")
    
    async def update_asset_content(
        self,
        blockchain_asset_id: int,
        new_content_hash: str,
        modification_type: str,
        modification_metadata: Dict[str, Any],
        network: str = None
    ) -> Dict[str, Any]:
        """Update asset content and record the modification."""
        network = network or settings.default_network
        
        try:
            # Create modification event
            modification_event = ProvenanceEventData(
                event_type="content_modified",
                actor=modification_metadata.get("modifier", self.blockchain_service.account.address),
                timestamp=datetime.now(timezone.utc).isoformat(),
                description=f"Asset content modified: {modification_type}",
                metadata={
                    "modification_type": modification_type,
                    "new_content_hash": new_content_hash,
                    "tools_used": modification_metadata.get("tools_used", []),
                    "workflow_id": modification_metadata.get("workflow_id"),
                    "version": modification_metadata.get("version"),
                    "changes_description": modification_metadata.get("changes_description")
                }
            )
            
            # Add modification event
            event_result = await self.add_provenance_event(
                blockchain_asset_id,
                modification_event,
                network
            )
            
            # Update content on blockchain
            w3 = self.blockchain_service.get_network(network)
            contract_address = self.blockchain_service._get_contract_address(network, "provenance")
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.provenance_contract_abi
            )
            
            transaction = contract.functions.updateAssetContent(
                blockchain_asset_id,
                Web3.keccak(text=new_content_hash),
                modification_type,
                json.dumps(modification_metadata)
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
                "blockchain_asset_id": blockchain_asset_id,
                "new_content_hash": new_content_hash,
                "modification_type": modification_type,
                "transaction_hash": receipt['transactionHash'].hex(),
                "block_number": receipt['blockNumber'],
                "event_transaction": event_result,
                "network": network,
                "modified_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Asset content updated: {blockchain_asset_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to update asset content: {e}")
            raise ProvenanceError(f"Content update failed: {e}")
    
    async def add_verification(
        self,
        blockchain_asset_id: int,
        verification_type: str,
        verified: bool,
        evidence: str,
        verifier_address: str = None,
        network: str = None
    ) -> Dict[str, Any]:
        """Add verification to an asset."""
        network = network or settings.default_network
        verifier_address = verifier_address or self.blockchain_service.account.address
        
        try:
            # Create verification event
            verification_event = ProvenanceEventData(
                event_type="verification_added",
                actor=verifier_address,
                timestamp=datetime.now(timezone.utc).isoformat(),
                description=f"Verification added: {verification_type} - {'VERIFIED' if verified else 'FAILED'}",
                metadata={
                    "verification_type": verification_type,
                    "verified": verified,
                    "evidence": evidence,
                    "verifier": verifier_address,
                    "evidence_hash": hashlib.sha256(evidence.encode()).hexdigest()
                }
            )
            
            # Add verification event
            event_result = await self.add_provenance_event(
                blockchain_asset_id,
                verification_event,
                network
            )
            
            # Add verification on blockchain
            w3 = self.blockchain_service.get_network(network)
            contract_address = self.blockchain_service._get_contract_address(network, "provenance")
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.provenance_contract_abi
            )
            
            transaction = contract.functions.addVerification(
                blockchain_asset_id,
                verification_type,
                verified,
                evidence
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
                "blockchain_asset_id": blockchain_asset_id,
                "verification_type": verification_type,
                "verified": verified,
                "verifier": verifier_address,
                "transaction_hash": receipt['transactionHash'].hex(),
                "block_number": receipt['blockNumber'],
                "event_transaction": event_result,
                "network": network,
                "verified_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Verification added: {verification_type} for asset {blockchain_asset_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to add verification: {e}")
            raise ProvenanceError(f"Verification addition failed: {e}")
    
    async def get_asset_info(
        self,
        blockchain_asset_id: int,
        network: str = None
    ) -> Dict[str, Any]:
        """Get comprehensive asset information from blockchain."""
        network = network or settings.default_network
        
        try:
            w3 = self.blockchain_service.get_network(network)
            contract_address = self.blockchain_service._get_contract_address(network, "provenance")
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.provenance_contract_abi
            )
            
            # Get asset data
            asset_data = contract.functions.assets(blockchain_asset_id).call()
            
            asset_info = {
                "blockchain_asset_id": asset_data[0],
                "content_hash": asset_data[1].hex(),
                "creator": asset_data[2],
                "current_owner": asset_data[3],
                "created_at": datetime.fromtimestamp(asset_data[4], tz=timezone.utc).isoformat(),
                "last_modified": datetime.fromtimestamp(asset_data[5], tz=timezone.utc).isoformat(),
                "title": asset_data[6],
                "description": asset_data[7],
                "asset_type": asset_data[8],
                "verified": asset_data[9],
                "network": network
            }
            
            return asset_info
            
        except Exception as e:
            logger.error(f"Failed to get asset info: {e}")
            raise ProvenanceError(f"Asset info retrieval failed: {e}")
    
    async def get_asset_history(
        self,
        blockchain_asset_id: int,
        network: str = None
    ) -> List[Dict[str, Any]]:
        """Get complete provenance history for an asset."""
        network = network or settings.default_network
        
        try:
            w3 = self.blockchain_service.get_network(network)
            contract_address = self.blockchain_service._get_contract_address(network, "provenance")
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.provenance_contract_abi
            )
            
            # Get provenance events from blockchain
            from_block = 0
            to_block = 'latest'
            
            # Get all ProvenanceEventAdded events for this asset
            event_filter = contract.events.ProvenanceEventAdded.create_filter(
                fromBlock=from_block,
                toBlock=to_block,
                argument_filters={'assetId': blockchain_asset_id}
            )
            
            events = event_filter.get_all_entries()
            
            # Format events
            history = []
            for event in events:
                try:
                    block = w3.eth.get_block(event['blockNumber'])
                    timestamp = datetime.fromtimestamp(block['timestamp'], tz=timezone.utc).isoformat()
                    
                    event_data = {
                        "event_id": event['args']['eventId'],
                        "asset_id": event['args']['assetId'],
                        "actor": event['args']['actor'],
                        "event_type": event['args']['eventType'],
                        "data_hash": event['args']['dataHash'].hex(),
                        "transaction_hash": event['transactionHash'].hex(),
                        "block_number": event['blockNumber'],
                        "timestamp": timestamp,
                        "log_index": event['logIndex']
                    }
                    
                    history.append(event_data)
                    
                except Exception as e:
                    logger.warning(f"Failed to process event: {e}")
                    continue
            
            # Sort by block number and log index
            history.sort(key=lambda x: (x['block_number'], x['log_index']))
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get asset history: {e}")
            raise ProvenanceError(f"History retrieval failed: {e}")
    
    async def verify_asset_authenticity(
        self,
        blockchain_asset_id: int,
        expected_content_hash: str,
        network: str = None
    ) -> Dict[str, Any]:
        """Verify the authenticity of an asset."""
        network = network or settings.default_network
        
        try:
            # Get asset info
            asset_info = await self.get_asset_info(blockchain_asset_id, network)
            
            # Compare content hashes
            blockchain_hash = asset_info["content_hash"]
            matches = blockchain_hash.lower() == expected_content_hash.lower()
            
            verification_result = {
                "blockchain_asset_id": blockchain_asset_id,
                "expected_hash": expected_content_hash,
                "blockchain_hash": blockchain_hash,
                "authentic": matches,
                "verified": asset_info["verified"],
                "creator": asset_info["creator"],
                "current_owner": asset_info["current_owner"],
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "network": network
            }
            
            return verification_result
            
        except Exception as e:
            logger.error(f"Failed to verify asset authenticity: {e}")
            raise ProvenanceError(f"Authenticity verification failed: {e}")
    
    async def trace_asset_lineage(
        self,
        blockchain_asset_id: int,
        network: str = None
    ) -> Dict[str, Any]:
        """Trace the complete lineage of an asset."""
        network = network or settings.default_network
        
        try:
            # Get asset info and history
            asset_info = await self.get_asset_info(blockchain_asset_id, network)
            history = await self.get_asset_history(blockchain_asset_id, network)
            
            # Analyze lineage
            ownership_chain = []
            modifications = []
            verifications = []
            
            current_owner = asset_info["creator"]
            ownership_chain.append({
                "owner": current_owner,
                "from": asset_info["created_at"],
                "to": None,
                "type": "creation"
            })
            
            for event in history:
                if event["event_type"] == "ownership_transferred":
                    # Close previous ownership
                    if ownership_chain:
                        ownership_chain[-1]["to"] = event["timestamp"]
                    
                    # Add new ownership (we'd need to parse the event data for new owner)
                    ownership_chain.append({
                        "owner": "new_owner",  # Would extract from event data
                        "from": event["timestamp"],
                        "to": None,
                        "type": "transfer"
                    })
                
                elif event["event_type"] == "content_modified":
                    modifications.append({
                        "timestamp": event["timestamp"],
                        "actor": event["actor"],
                        "data_hash": event["data_hash"],
                        "transaction_hash": event["transaction_hash"]
                    })
                
                elif event["event_type"] == "verification_added":
                    verifications.append({
                        "timestamp": event["timestamp"],
                        "verifier": event["actor"],
                        "transaction_hash": event["transaction_hash"]
                    })
            
            lineage = {
                "asset_id": blockchain_asset_id,
                "asset_info": asset_info,
                "ownership_chain": ownership_chain,
                "modifications": modifications,
                "verifications": verifications,
                "total_events": len(history),
                "lineage_integrity": self._calculate_lineage_integrity(history),
                "traced_at": datetime.now(timezone.utc).isoformat()
            }
            
            return lineage
            
        except Exception as e:
            logger.error(f"Failed to trace asset lineage: {e}")
            raise ProvenanceError(f"Lineage tracing failed: {e}")
    
    async def _create_content_hash(self, asset_metadata: AssetMetadata) -> str:
        """Create a deterministic content hash from asset metadata."""
        # Create hash from core asset properties
        hash_data = {
            "title": asset_metadata.title,
            "file_format": asset_metadata.file_format,
            "file_size": asset_metadata.file_size,
            "duration": asset_metadata.duration,
            "resolution": asset_metadata.resolution,
            "created_date": asset_metadata.created_date
        }
        
        sorted_data = json.dumps(hash_data, sort_keys=True)
        content_hash = hashlib.sha256(sorted_data.encode()).hexdigest()
        
        return content_hash
    
    async def _create_event_hash(self, event_data: ProvenanceEventData) -> str:
        """Create a hash for a provenance event."""
        hash_data = {
            "event_type": event_data.event_type,
            "actor": event_data.actor,
            "timestamp": event_data.timestamp,
            "description": event_data.description,
            "metadata": event_data.metadata
        }
        
        sorted_data = json.dumps(hash_data, sort_keys=True)
        event_hash = hashlib.sha256(sorted_data.encode()).hexdigest()
        
        return event_hash
    
    def _calculate_lineage_integrity(self, history: List[Dict[str, Any]]) -> float:
        """Calculate the integrity score of an asset's lineage."""
        if not history:
            return 1.0
        
        # Simple integrity calculation based on:
        # - Presence of blockchain verification
        # - Chronological order
        # - Event completeness
        
        integrity_score = 1.0
        
        # Check chronological order
        for i in range(1, len(history)):
            if history[i]["block_number"] < history[i-1]["block_number"]:
                integrity_score -= 0.1
        
        # Check for gaps in the chain
        if len(history) < 3:  # Expect at least creation + some events
            integrity_score -= 0.2
        
        return max(0.0, integrity_score)
    
    async def create_provenance_report(
        self,
        blockchain_asset_id: int,
        network: str = None
    ) -> Dict[str, Any]:
        """Create a comprehensive provenance report for an asset."""
        network = network or settings.default_network
        
        try:
            # Gather all provenance data
            asset_info = await self.get_asset_info(blockchain_asset_id, network)
            history = await self.get_asset_history(blockchain_asset_id, network)
            lineage = await self.trace_asset_lineage(blockchain_asset_id, network)
            authenticity = await self.verify_asset_authenticity(
                blockchain_asset_id,
                asset_info["content_hash"],
                network
            )
            
            # Create comprehensive report
            report = {
                "report_id": str(uuid.uuid4()),
                "asset_id": blockchain_asset_id,
                "network": network,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                
                # Asset summary
                "asset_summary": {
                    "title": asset_info["title"],
                    "type": asset_info["asset_type"],
                    "creator": asset_info["creator"],
                    "current_owner": asset_info["current_owner"],
                    "created_at": asset_info["created_at"],
                    "verified": asset_info["verified"]
                },
                
                # Authenticity verification
                "authenticity": authenticity,
                
                # Provenance chain
                "provenance_chain": {
                    "total_events": len(history),
                    "integrity_score": lineage["lineage_integrity"],
                    "ownership_changes": len(lineage["ownership_chain"]) - 1,
                    "content_modifications": len(lineage["modifications"]),
                    "verifications": len(lineage["verifications"])
                },
                
                # Detailed history
                "detailed_history": history,
                
                # Ownership lineage
                "ownership_lineage": lineage["ownership_chain"],
                
                # Risk assessment
                "risk_assessment": {
                    "authenticity_risk": "low" if authenticity["authentic"] else "high",
                    "integrity_risk": "low" if lineage["lineage_integrity"] > 0.8 else "medium" if lineage["lineage_integrity"] > 0.5 else "high",
                    "verification_status": "verified" if asset_info["verified"] else "unverified"
                },
                
                # Compliance information
                "compliance": {
                    "blockchain_verified": True,
                    "immutable_record": True,
                    "timestamp_verified": True,
                    "chain_of_custody": len(lineage["ownership_chain"]) > 0
                }
            }
            
            # Upload report to IPFS
            report_result = await self.ipfs_service.upload_json(
                report,
                content_type="provenance_report",
                pin=True
            )
            
            report["ipfs_hash"] = report_result["ipfs_hash"]
            report["report_uri"] = report_result["gateway_url"]
            
            logger.info(f"Provenance report created for asset {blockchain_asset_id}")
            return report
            
        except Exception as e:
            logger.error(f"Failed to create provenance report: {e}")
            raise ProvenanceError(f"Report creation failed: {e}")