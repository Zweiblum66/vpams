"""Web3 Connector Service for blockchain interactions"""

import asyncio
import logging
from typing import Dict, Optional, Any, List
from web3 import Web3, AsyncWeb3
from web3.middleware import geth_poa_middleware
from eth_account import Account
from eth_typing import Address, ChecksumAddress
import aiohttp

from ..core.config import settings
from ..models.web3_models import ChainType

logger = logging.getLogger(__name__)

class Web3ConnectorService:
    """Service for managing Web3 connections across multiple chains"""
    
    def __init__(self):
        self.connections: Dict[str, AsyncWeb3] = {}
        self.chain_configs = {
            ChainType.ETHEREUM: {
                "rpc_url": settings.ETHEREUM_RPC_URL,
                "chain_id": 1,
                "name": "Ethereum Mainnet",
                "currency": "ETH",
                "explorer": "https://etherscan.io"
            },
            ChainType.POLYGON: {
                "rpc_url": settings.POLYGON_RPC_URL,
                "chain_id": 137,
                "name": "Polygon",
                "currency": "MATIC",
                "explorer": "https://polygonscan.com"
            },
            ChainType.ARBITRUM: {
                "rpc_url": settings.ARBITRUM_RPC_URL,
                "chain_id": 42161,
                "name": "Arbitrum One",
                "currency": "ETH",
                "explorer": "https://arbiscan.io"
            },
            ChainType.OPTIMISM: {
                "rpc_url": settings.OPTIMISM_RPC_URL,
                "chain_id": 10,
                "name": "Optimism",
                "currency": "ETH",
                "explorer": "https://optimistic.etherscan.io"
            },
            ChainType.AVALANCHE: {
                "rpc_url": settings.AVALANCHE_RPC_URL,
                "chain_id": 43114,
                "name": "Avalanche C-Chain",
                "currency": "AVAX",
                "explorer": "https://snowtrace.io"
            },
            ChainType.BSC: {
                "rpc_url": settings.BSC_RPC_URL,
                "chain_id": 56,
                "name": "BNB Smart Chain",
                "currency": "BNB",
                "explorer": "https://bscscan.com"
            }
        }
    
    async def initialize(self):
        """Initialize Web3 connections for all configured chains"""
        for chain_type, config in self.chain_configs.items():
            try:
                # Create async Web3 instance
                w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(config["rpc_url"]))
                
                # Add POA middleware for chains that need it (BSC, Polygon)
                if chain_type in [ChainType.BSC, ChainType.POLYGON]:
                    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                
                # Test connection
                if await w3.is_connected():
                    self.connections[chain_type.value] = w3
                    logger.info(f"Connected to {config['name']}")
                else:
                    logger.error(f"Failed to connect to {config['name']}")
                    
            except Exception as e:
                logger.error(f"Error connecting to {config['name']}: {e}")
    
    async def cleanup(self):
        """Cleanup connections"""
        # AsyncWeb3 doesn't need explicit cleanup
        self.connections.clear()
        logger.info("Web3 connections cleaned up")
    
    def get_connection(self, chain: str) -> Optional[AsyncWeb3]:
        """Get Web3 connection for a specific chain"""
        return self.connections.get(chain)
    
    async def check_connection(self, chain: str) -> bool:
        """Check if connection to chain is active"""
        w3 = self.get_connection(chain)
        if w3:
            try:
                return await w3.is_connected()
            except:
                return False
        return False
    
    async def get_block_number(self, chain: str) -> Optional[int]:
        """Get current block number for a chain"""
        w3 = self.get_connection(chain)
        if w3:
            try:
                return await w3.eth.block_number
            except Exception as e:
                logger.error(f"Error getting block number for {chain}: {e}")
        return None
    
    async def get_balance(self, chain: str, address: str) -> Optional[int]:
        """Get ETH/native token balance for an address"""
        w3 = self.get_connection(chain)
        if w3:
            try:
                checksum_address = Web3.to_checksum_address(address)
                return await w3.eth.get_balance(checksum_address)
            except Exception as e:
                logger.error(f"Error getting balance: {e}")
        return None
    
    async def get_transaction(self, chain: str, tx_hash: str) -> Optional[Dict]:
        """Get transaction details"""
        w3 = self.get_connection(chain)
        if w3:
            try:
                tx = await w3.eth.get_transaction(tx_hash)
                return dict(tx)
            except Exception as e:
                logger.error(f"Error getting transaction: {e}")
        return None
    
    async def get_transaction_receipt(self, chain: str, tx_hash: str) -> Optional[Dict]:
        """Get transaction receipt"""
        w3 = self.get_connection(chain)
        if w3:
            try:
                receipt = await w3.eth.get_transaction_receipt(tx_hash)
                return dict(receipt)
            except Exception as e:
                logger.error(f"Error getting transaction receipt: {e}")
        return None
    
    async def estimate_gas(self, chain: str, transaction: Dict) -> Optional[int]:
        """Estimate gas for a transaction"""
        w3 = self.get_connection(chain)
        if w3:
            try:
                return await w3.eth.estimate_gas(transaction)
            except Exception as e:
                logger.error(f"Error estimating gas: {e}")
        return None
    
    async def get_gas_price(self, chain: str) -> Optional[Dict[str, int]]:
        """Get current gas prices"""
        w3 = self.get_connection(chain)
        if w3:
            try:
                gas_price = await w3.eth.gas_price
                
                # Calculate different speed options
                return {
                    "slow": int(gas_price * 0.8),
                    "standard": int(gas_price),
                    "fast": int(gas_price * 1.2),
                    "instant": int(gas_price * 1.5)
                }
            except Exception as e:
                logger.error(f"Error getting gas price: {e}")
        return None
    
    async def send_raw_transaction(self, chain: str, signed_tx: str) -> Optional[str]:
        """Send a signed transaction"""
        w3 = self.get_connection(chain)
        if w3:
            try:
                tx_hash = await w3.eth.send_raw_transaction(signed_tx)
                return tx_hash.hex()
            except Exception as e:
                logger.error(f"Error sending transaction: {e}")
        return None
    
    async def wait_for_transaction_receipt(
        self, 
        chain: str, 
        tx_hash: str, 
        timeout: int = 120
    ) -> Optional[Dict]:
        """Wait for transaction to be mined"""
        w3 = self.get_connection(chain)
        if w3:
            try:
                receipt = await w3.eth.wait_for_transaction_receipt(
                    tx_hash, 
                    timeout=timeout
                )
                return dict(receipt)
            except Exception as e:
                logger.error(f"Error waiting for transaction receipt: {e}")
        return None
    
    async def call_contract_function(
        self,
        chain: str,
        contract_address: str,
        abi: List[Dict],
        function_name: str,
        *args,
        **kwargs
    ) -> Any:
        """Call a contract function (read-only)"""
        w3 = self.get_connection(chain)
        if w3:
            try:
                checksum_address = Web3.to_checksum_address(contract_address)
                contract = w3.eth.contract(address=checksum_address, abi=abi)
                function = getattr(contract.functions, function_name)
                return await function(*args).call(**kwargs)
            except Exception as e:
                logger.error(f"Error calling contract function: {e}")
        return None
    
    async def build_contract_transaction(
        self,
        chain: str,
        contract_address: str,
        abi: List[Dict],
        function_name: str,
        from_address: str,
        *args,
        **kwargs
    ) -> Optional[Dict]:
        """Build a contract transaction"""
        w3 = self.get_connection(chain)
        if w3:
            try:
                checksum_address = Web3.to_checksum_address(contract_address)
                from_checksum = Web3.to_checksum_address(from_address)
                
                contract = w3.eth.contract(address=checksum_address, abi=abi)
                function = getattr(contract.functions, function_name)
                
                # Get nonce
                nonce = await w3.eth.get_transaction_count(from_checksum)
                
                # Build transaction
                tx = await function(*args).build_transaction({
                    'from': from_checksum,
                    'nonce': nonce,
                    'gas': kwargs.get('gas', 200000),
                    'gasPrice': kwargs.get('gasPrice', await w3.eth.gas_price),
                    'chainId': self.chain_configs[ChainType(chain)]['chain_id']
                })
                
                return tx
            except Exception as e:
                logger.error(f"Error building contract transaction: {e}")
        return None
    
    def sign_transaction(self, transaction: Dict, private_key: str) -> Optional[str]:
        """Sign a transaction with a private key"""
        try:
            account = Account.from_key(private_key)
            signed = account.sign_transaction(transaction)
            return signed.rawTransaction.hex()
        except Exception as e:
            logger.error(f"Error signing transaction: {e}")
        return None
    
    def recover_message_signer(self, message: str, signature: str) -> Optional[str]:
        """Recover the address that signed a message"""
        try:
            # Encode the message
            encoded_message = Web3.keccak(text=message)
            
            # Recover the address
            address = Account.recover_message(encoded_message, signature=signature)
            return address
        except Exception as e:
            logger.error(f"Error recovering message signer: {e}")
        return None
    
    async def get_ens_name(self, address: str) -> Optional[str]:
        """Resolve ENS name for an address"""
        w3 = self.get_connection(ChainType.ETHEREUM.value)
        if w3:
            try:
                checksum_address = Web3.to_checksum_address(address)
                ens_name = await w3.ens.name(checksum_address)
                return ens_name
            except Exception as e:
                logger.error(f"Error resolving ENS name: {e}")
        return None
    
    async def resolve_ens_address(self, ens_name: str) -> Optional[str]:
        """Resolve ENS name to address"""
        w3 = self.get_connection(ChainType.ETHEREUM.value)
        if w3:
            try:
                address = await w3.ens.address(ens_name)
                return address
            except Exception as e:
                logger.error(f"Error resolving ENS address: {e}")
        return None
    
    def is_valid_address(self, address: str) -> bool:
        """Check if an address is valid"""
        try:
            Web3.to_checksum_address(address)
            return True
        except:
            return False
    
    def to_wei(self, amount: float, unit: str = 'ether') -> int:
        """Convert amount to wei"""
        return Web3.to_wei(amount, unit)
    
    def from_wei(self, amount: int, unit: str = 'ether') -> float:
        """Convert wei to specified unit"""
        return Web3.from_wei(amount, unit)
    
    def get_chain_info(self, chain: str) -> Optional[Dict]:
        """Get chain configuration info"""
        chain_type = ChainType(chain)
        return self.chain_configs.get(chain_type)