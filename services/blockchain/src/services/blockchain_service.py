"""
Core blockchain service for distributed ledger technology implementation.
"""
import asyncio
import json
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import uuid

from web3 import Web3
from web3.exceptions import TransactionNotFound, BlockNotFound
from eth_utils import to_checksum_address, is_address
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization
import structlog

from ..core.config import settings
from ..db.models import (
    BlockchainAsset, MediaRights, RightsLicense, BlockchainTransaction,
    RoyaltyPayment, SmartContract, IPFSHash, RightsAuditLog,
    NetworkType, TransactionStatus, RightsType, LicenseStatus, PaymentStatus
)

logger = structlog.get_logger()


class BlockchainError(Exception):
    """Base exception for blockchain operations."""
    pass


class InsufficientFundsError(BlockchainError):
    """Raised when account has insufficient funds."""
    pass


class TransactionFailedError(BlockchainError):
    """Raised when transaction fails."""
    pass


class NetworkError(BlockchainError):
    """Raised when network is unavailable."""
    pass


class BlockchainService:
    """Core blockchain service for DLT rights management."""
    
    def __init__(self):
        self.networks = self._initialize_networks()
        self.contract_abis = self._load_contract_abis()
        self.account = None
        self._initialize_account()
    
    def _initialize_networks(self) -> Dict[str, Web3]:
        """Initialize Web3 connections for all supported networks."""
        networks = {}
        
        network_configs = {
            NetworkType.ETHEREUM: settings.ethereum_rpc_url,
            NetworkType.POLYGON: settings.polygon_rpc_url,
            NetworkType.AVALANCHE: settings.avalanche_rpc_url,
            NetworkType.BSC: settings.bsc_rpc_url,
        }
        
        for network, rpc_url in network_configs.items():
            try:
                w3 = Web3(Web3.HTTPProvider(rpc_url))
                if w3.is_connected():
                    networks[network.value] = w3
                    logger.info(f"Connected to {network.value} network")
                else:
                    logger.error(f"Failed to connect to {network.value} network")
            except Exception as e:
                logger.error(f"Error connecting to {network.value}: {e}")
        
        return networks
    
    def _load_contract_abis(self) -> Dict[str, List]:
        """Load smart contract ABIs."""
        # This would typically load from JSON files
        # For now, we'll define basic ABIs inline
        return {
            "rights": [
                {
                    "inputs": [
                        {"name": "tokenId", "type": "uint256"},
                        {"name": "rightsHash", "type": "bytes32"},
                        {"name": "metadata", "type": "string"}
                    ],
                    "name": "mintRights",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                },
                {
                    "inputs": [
                        {"name": "tokenId", "type": "uint256"},
                        {"name": "licensee", "type": "address"},
                        {"name": "terms", "type": "string"}
                    ],
                    "name": "createLicense",
                    "outputs": [],
                    "stateMutability": "payable",
                    "type": "function"
                },
                {
                    "inputs": [{"name": "tokenId", "type": "uint256"}],
                    "name": "getRightsInfo",
                    "outputs": [
                        {"name": "owner", "type": "address"},
                        {"name": "rightsHash", "type": "bytes32"},
                        {"name": "metadata", "type": "string"}
                    ],
                    "stateMutability": "view",
                    "type": "function"
                }
            ]
        }
    
    def _initialize_account(self):
        """Initialize the blockchain account."""
        try:
            # Create account from private key
            for network_name, w3 in self.networks.items():
                account = w3.eth.account.from_key(settings.private_key)
                self.account = account
                logger.info(f"Initialized account: {account.address}")
                break
        except Exception as e:
            logger.error(f"Failed to initialize account: {e}")
            raise BlockchainError(f"Account initialization failed: {e}")
    
    def get_network(self, network: str) -> Web3:
        """Get Web3 instance for specified network."""
        if network not in self.networks:
            raise NetworkError(f"Network {network} not available")
        return self.networks[network]
    
    async def get_balance(self, address: str, network: str = None) -> Dict[str, Any]:
        """Get balance for an address across networks."""
        if network:
            networks = [network]
        else:
            networks = list(self.networks.keys())
        
        balances = {}
        
        for net in networks:
            try:
                w3 = self.get_network(net)
                checksum_address = to_checksum_address(address)
                balance_wei = w3.eth.get_balance(checksum_address)
                balance_eth = w3.from_wei(balance_wei, 'ether')
                
                balances[net] = {
                    "balance_wei": str(balance_wei),
                    "balance_eth": str(balance_eth),
                    "balance_formatted": f"{balance_eth:.6f} ETH"
                }
            except Exception as e:
                logger.error(f"Failed to get balance for {address} on {net}: {e}")
                balances[net] = {"error": str(e)}
        
        return balances
    
    async def create_rights_hash(self, asset_data: Dict[str, Any]) -> str:
        """Create a unique hash for media rights."""
        # Create deterministic hash from asset data
        hash_input = {
            "asset_id": str(asset_data.get("asset_id")),
            "creator": asset_data.get("creator"),
            "title": asset_data.get("title"),
            "created_at": asset_data.get("created_at"),
            "rights_type": asset_data.get("rights_type"),
            "terms": asset_data.get("terms", {})
        }
        
        # Sort keys for consistent hashing
        sorted_data = json.dumps(hash_input, sort_keys=True)
        rights_hash = hashlib.sha256(sorted_data.encode()).hexdigest()
        
        logger.info(f"Created rights hash: {rights_hash}")
        return rights_hash
    
    async def mint_rights_nft(
        self,
        asset_id: uuid.UUID,
        owner_address: str,
        rights_data: Dict[str, Any],
        network: str = None
    ) -> Dict[str, Any]:
        """Mint an NFT representing media rights."""
        network = network or settings.default_network
        w3 = self.get_network(network)
        
        try:
            # Create rights hash
            rights_hash = await self.create_rights_hash(rights_data)
            
            # Get contract address for network
            contract_address = self._get_contract_address(network, "rights")
            if not contract_address:
                raise BlockchainError(f"No rights contract deployed on {network}")
            
            # Create contract instance
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.contract_abis["rights"]
            )
            
            # Generate token ID
            token_id = int(str(asset_id).replace("-", ""), 16) % (2**256)
            
            # Prepare transaction
            checksum_owner = to_checksum_address(owner_address)
            metadata_uri = f"ipfs://{rights_data.get('ipfs_hash', '')}"
            
            # Build transaction
            transaction = contract.functions.mintRights(
                token_id,
                Web3.to_bytes(hexstr=rights_hash),
                metadata_uri
            ).build_transaction({
                'from': self.account.address,
                'gas': settings.gas_limit,
                'gasPrice': w3.to_wei(settings.gas_price_gwei, 'gwei'),
                'nonce': w3.eth.get_transaction_count(self.account.address)
            })
            
            # Sign and send transaction
            signed_txn = self.account.sign_transaction(transaction)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for confirmation
            receipt = await self._wait_for_confirmation(w3, tx_hash)
            
            result = {
                "transaction_hash": receipt['transactionHash'].hex(),
                "block_number": receipt['blockNumber'],
                "token_id": token_id,
                "rights_hash": rights_hash,
                "contract_address": contract_address,
                "network": network,
                "gas_used": receipt['gasUsed'],
                "status": "success" if receipt['status'] == 1 else "failed"
            }
            
            logger.info(f"Minted rights NFT: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to mint rights NFT: {e}")
            raise TransactionFailedError(f"NFT minting failed: {e}")
    
    async def create_license(
        self,
        asset_id: uuid.UUID,
        licensee_address: str,
        license_terms: Dict[str, Any],
        license_fee: Decimal,
        network: str = None
    ) -> Dict[str, Any]:
        """Create a license for media rights."""
        network = network or settings.default_network
        w3 = self.get_network(network)
        
        try:
            # Get contract
            contract_address = self._get_contract_address(network, "rights")
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.contract_abis["rights"]
            )
            
            # Generate token ID from asset ID
            token_id = int(str(asset_id).replace("-", ""), 16) % (2**256)
            
            # Prepare license terms as JSON string
            terms_json = json.dumps(license_terms)
            
            # Convert license fee to wei
            fee_wei = w3.to_wei(license_fee, 'ether')
            
            # Build transaction
            transaction = contract.functions.createLicense(
                token_id,
                to_checksum_address(licensee_address),
                terms_json
            ).build_transaction({
                'from': self.account.address,
                'value': fee_wei,
                'gas': settings.gas_limit,
                'gasPrice': w3.to_wei(settings.gas_price_gwei, 'gwei'),
                'nonce': w3.eth.get_transaction_count(self.account.address)
            })
            
            # Sign and send transaction
            signed_txn = self.account.sign_transaction(transaction)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for confirmation
            receipt = await self._wait_for_confirmation(w3, tx_hash)
            
            # Create license hash
            license_hash = hashlib.sha256(
                f"{asset_id}{licensee_address}{terms_json}".encode()
            ).hexdigest()
            
            result = {
                "transaction_hash": receipt['transactionHash'].hex(),
                "block_number": receipt['blockNumber'],
                "license_hash": license_hash,
                "token_id": token_id,
                "licensee": licensee_address,
                "license_fee": str(license_fee),
                "network": network,
                "gas_used": receipt['gasUsed'],
                "status": "success" if receipt['status'] == 1 else "failed"
            }
            
            logger.info(f"Created license: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create license: {e}")
            raise TransactionFailedError(f"License creation failed: {e}")
    
    async def transfer_rights(
        self,
        asset_id: uuid.UUID,
        from_address: str,
        to_address: str,
        network: str = None
    ) -> Dict[str, Any]:
        """Transfer rights ownership."""
        network = network or settings.default_network
        w3 = self.get_network(network)
        
        try:
            # Get contract
            contract_address = self._get_contract_address(network, "rights")
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.contract_abis["rights"]
            )
            
            # Generate token ID
            token_id = int(str(asset_id).replace("-", ""), 16) % (2**256)
            
            # Build transfer transaction (assuming ERC721 interface)
            transaction = contract.functions.transferFrom(
                to_checksum_address(from_address),
                to_checksum_address(to_address),
                token_id
            ).build_transaction({
                'from': self.account.address,
                'gas': settings.gas_limit,
                'gasPrice': w3.to_wei(settings.gas_price_gwei, 'gwei'),
                'nonce': w3.eth.get_transaction_count(self.account.address)
            })
            
            # Sign and send transaction
            signed_txn = self.account.sign_transaction(transaction)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for confirmation
            receipt = await self._wait_for_confirmation(w3, tx_hash)
            
            result = {
                "transaction_hash": receipt['transactionHash'].hex(),
                "block_number": receipt['blockNumber'],
                "token_id": token_id,
                "from_address": from_address,
                "to_address": to_address,
                "network": network,
                "gas_used": receipt['gasUsed'],
                "status": "success" if receipt['status'] == 1 else "failed"
            }
            
            logger.info(f"Transferred rights: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to transfer rights: {e}")
            raise TransactionFailedError(f"Rights transfer failed: {e}")
    
    async def verify_rights_ownership(
        self,
        asset_id: uuid.UUID,
        owner_address: str,
        network: str = None
    ) -> Dict[str, Any]:
        """Verify rights ownership on blockchain."""
        network = network or settings.default_network
        w3 = self.get_network(network)
        
        try:
            # Get contract
            contract_address = self._get_contract_address(network, "rights")
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.contract_abis["rights"]
            )
            
            # Generate token ID
            token_id = int(str(asset_id).replace("-", ""), 16) % (2**256)
            
            # Get rights info from contract
            rights_info = contract.functions.getRightsInfo(token_id).call()
            owner, rights_hash, metadata = rights_info
            
            # Verify ownership
            is_owner = owner.lower() == owner_address.lower()
            
            result = {
                "asset_id": str(asset_id),
                "token_id": token_id,
                "current_owner": owner,
                "claimed_owner": owner_address,
                "is_owner": is_owner,
                "rights_hash": rights_hash.hex(),
                "metadata": metadata,
                "network": network,
                "verified_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Verified rights ownership: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to verify rights ownership: {e}")
            return {
                "asset_id": str(asset_id),
                "error": str(e),
                "is_owner": False,
                "verified_at": datetime.now(timezone.utc).isoformat()
            }
    
    async def get_transaction_status(
        self,
        transaction_hash: str,
        network: str = None
    ) -> Dict[str, Any]:
        """Get status of a blockchain transaction."""
        network = network or settings.default_network
        w3 = self.get_network(network)
        
        try:
            # Get transaction receipt
            receipt = w3.eth.get_transaction_receipt(transaction_hash)
            
            # Get transaction details
            transaction = w3.eth.get_transaction(transaction_hash)
            
            # Get current block for confirmation count
            current_block = w3.eth.block_number
            confirmations = current_block - receipt['blockNumber'] + 1
            
            status = {
                "transaction_hash": transaction_hash,
                "block_number": receipt['blockNumber'],
                "block_hash": receipt['blockHash'].hex(),
                "status": "success" if receipt['status'] == 1 else "failed",
                "confirmations": confirmations,
                "gas_used": receipt['gasUsed'],
                "gas_price": transaction['gasPrice'],
                "from_address": transaction['from'],
                "to_address": transaction['to'],
                "value": str(transaction['value']),
                "network": network,
                "confirmed": confirmations >= settings.confirmation_blocks
            }
            
            return status
            
        except TransactionNotFound:
            return {
                "transaction_hash": transaction_hash,
                "status": "not_found",
                "network": network,
                "error": "Transaction not found"
            }
        except Exception as e:
            logger.error(f"Failed to get transaction status: {e}")
            return {
                "transaction_hash": transaction_hash,
                "status": "error",
                "network": network,
                "error": str(e)
            }
    
    async def calculate_royalty_payment(
        self,
        license_fee: Decimal,
        royalty_percentage: Decimal,
        usage_count: int = 1
    ) -> Dict[str, Any]:
        """Calculate royalty payment amount."""
        try:
            base_royalty = (license_fee * royalty_percentage / 100)
            total_royalty = base_royalty * usage_count
            
            # Calculate gas fee estimate
            network = settings.default_network
            w3 = self.get_network(network)
            gas_price = w3.to_wei(settings.gas_price_gwei, 'gwei')
            estimated_gas_fee = w3.from_wei(gas_price * settings.gas_limit, 'ether')
            
            calculation = {
                "license_fee": str(license_fee),
                "royalty_percentage": str(royalty_percentage),
                "usage_count": usage_count,
                "base_royalty": str(base_royalty),
                "total_royalty": str(total_royalty),
                "estimated_gas_fee": str(estimated_gas_fee),
                "net_payment": str(total_royalty - estimated_gas_fee),
                "calculated_at": datetime.now(timezone.utc).isoformat()
            }
            
            return calculation
            
        except Exception as e:
            logger.error(f"Failed to calculate royalty: {e}")
            raise BlockchainError(f"Royalty calculation failed: {e}")
    
    async def send_royalty_payment(
        self,
        recipient_address: str,
        amount: Decimal,
        license_id: uuid.UUID,
        network: str = None
    ) -> Dict[str, Any]:
        """Send royalty payment."""
        network = network or settings.default_network
        w3 = self.get_network(network)
        
        try:
            # Check balance
            balance = w3.eth.get_balance(self.account.address)
            amount_wei = w3.to_wei(amount, 'ether')
            gas_cost = w3.to_wei(settings.gas_price_gwei, 'gwei') * settings.gas_limit
            
            if balance < (amount_wei + gas_cost):
                raise InsufficientFundsError("Insufficient funds for payment and gas")
            
            # Build transaction
            transaction = {
                'to': to_checksum_address(recipient_address),
                'value': amount_wei,
                'gas': settings.gas_limit,
                'gasPrice': w3.to_wei(settings.gas_price_gwei, 'gwei'),
                'nonce': w3.eth.get_transaction_count(self.account.address)
            }
            
            # Sign and send transaction
            signed_txn = self.account.sign_transaction(transaction)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for confirmation
            receipt = await self._wait_for_confirmation(w3, tx_hash)
            
            result = {
                "transaction_hash": receipt['transactionHash'].hex(),
                "block_number": receipt['blockNumber'],
                "recipient": recipient_address,
                "amount": str(amount),
                "license_id": str(license_id),
                "network": network,
                "gas_used": receipt['gasUsed'],
                "status": "success" if receipt['status'] == 1 else "failed"
            }
            
            logger.info(f"Sent royalty payment: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to send royalty payment: {e}")
            raise TransactionFailedError(f"Royalty payment failed: {e}")
    
    async def _wait_for_confirmation(
        self,
        w3: Web3,
        tx_hash: bytes,
        timeout: int = None
    ) -> Dict[str, Any]:
        """Wait for transaction confirmation."""
        timeout = timeout or settings.transaction_timeout
        
        try:
            receipt = w3.eth.wait_for_transaction_receipt(
                tx_hash,
                timeout=timeout
            )
            return receipt
        except Exception as e:
            logger.error(f"Transaction confirmation failed: {e}")
            raise TransactionFailedError(f"Transaction confirmation failed: {e}")
    
    def _get_contract_address(self, network: str, contract_type: str) -> Optional[str]:
        """Get contract address for network and type."""
        contract_mapping = {
            NetworkType.ETHEREUM.value: {
                "rights": settings.rights_contract_ethereum
            },
            NetworkType.POLYGON.value: {
                "rights": settings.rights_contract_polygon
            },
            NetworkType.AVALANCHE.value: {
                "rights": settings.rights_contract_avalanche
            },
            NetworkType.BSC.value: {
                "rights": settings.rights_contract_bsc
            }
        }
        
        return contract_mapping.get(network, {}).get(contract_type)
    
    async def get_network_stats(self) -> Dict[str, Any]:
        """Get statistics for all connected networks."""
        stats = {}
        
        for network_name, w3 in self.networks.items():
            try:
                latest_block = w3.eth.get_block('latest')
                gas_price = w3.eth.gas_price
                
                stats[network_name] = {
                    "connected": True,
                    "latest_block": latest_block['number'],
                    "block_time": latest_block['timestamp'],
                    "gas_price_gwei": w3.from_wei(gas_price, 'gwei'),
                    "chain_id": w3.eth.chain_id
                }
            except Exception as e:
                stats[network_name] = {
                    "connected": False,
                    "error": str(e)
                }
        
        return stats
    
    async def batch_verify_ownership(
        self,
        ownership_requests: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Batch verify multiple ownership claims."""
        results = []
        
        # Process in batches to avoid overwhelming the network
        batch_size = 10
        for i in range(0, len(ownership_requests), batch_size):
            batch = ownership_requests[i:i + batch_size]
            
            # Process batch concurrently
            tasks = []
            for request in batch:
                task = self.verify_rights_ownership(
                    request['asset_id'],
                    request['owner_address'],
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
                        "is_owner": False
                    })
                else:
                    results.append(result)
        
        return results