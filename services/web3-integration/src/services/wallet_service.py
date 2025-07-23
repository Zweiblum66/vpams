"""Wallet management service"""

import logging
from typing import Optional, List
from web3 import Web3

from ..services.web3_connector import Web3ConnectorService

logger = logging.getLogger(__name__)

class WalletService:
    """Service for wallet operations"""
    
    def __init__(self):
        self.connector = Web3ConnectorService()
    
    async def get_native_balance(self, chain: str, address: str) -> Optional[int]:
        """Get native token balance for a wallet"""
        try:
            await self.connector.initialize()
            balance = await self.connector.get_balance(chain, address)
            await self.connector.cleanup()
            return balance
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return None
    
    async def derive_addresses_from_mnemonic(
        self, 
        mnemonic: str, 
        count: int = 10
    ) -> List[str]:
        """Derive addresses from mnemonic"""
        # TODO: Implement HD wallet derivation
        return []
    
    async def get_address_from_private_key(self, private_key: str) -> str:
        """Get address from private key"""
        try:
            account = Web3().eth.account.from_key(private_key)
            return account.address
        except Exception as e:
            logger.error(f"Error getting address from private key: {e}")
            raise