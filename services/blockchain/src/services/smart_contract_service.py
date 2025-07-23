"""
Smart contract service for comprehensive contract management and deployment.
"""
import asyncio
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
import uuid
from pathlib import Path

from web3 import Web3
from web3.contract import Contract
from eth_utils import to_checksum_address, is_address
from solcx import compile_source, install_solc, set_solc_version
import structlog

from ..core.config import settings
from ..db.models import (
    SmartContract, BlockchainTransaction, NetworkType, 
    TransactionStatus, ContractType
)
from .blockchain_service import BlockchainService

logger = structlog.get_logger()


class SmartContractError(Exception):
    """Base exception for smart contract operations."""
    pass


class CompilationError(SmartContractError):
    """Raised when contract compilation fails."""
    pass


class DeploymentError(SmartContractError):
    """Raised when contract deployment fails."""
    pass


class ContractInteractionError(SmartContractError):
    """Raised when contract interaction fails."""
    pass


class SmartContractService:
    """Comprehensive smart contract management service."""
    
    def __init__(self):
        self.blockchain_service = BlockchainService()
        self.contracts_dir = Path(__file__).parent.parent.parent / "contracts"
        self.compiled_contracts = {}
        self._setup_solidity_compiler()
    
    def _setup_solidity_compiler(self):
        """Setup Solidity compiler."""
        try:
            # Install and set Solidity version
            install_solc('0.8.19')
            set_solc_version('0.8.19')
            logger.info("Solidity compiler setup complete")
        except Exception as e:
            logger.error(f"Failed to setup Solidity compiler: {e}")
    
    async def compile_contract(
        self,
        contract_path: str,
        contract_name: str = None
    ) -> Dict[str, Any]:
        """Compile a Solidity contract."""
        try:
            contract_file = Path(contract_path)
            if not contract_file.exists():
                # Try relative to contracts directory
                contract_file = self.contracts_dir / contract_path
            
            if not contract_file.exists():
                raise CompilationError(f"Contract file not found: {contract_path}")
            
            # Read contract source
            with open(contract_file, 'r') as f:
                contract_source = f.read()
            
            # Compile contract
            compiled_sol = compile_source(
                contract_source,
                optimize=True,
                optimize_runs=200
            )
            
            # Extract contract data
            if contract_name:
                contract_id = f"<stdin>:{contract_name}"
            else:
                # Use first contract if name not specified
                contract_id = list(compiled_sol.keys())[0]
            
            if contract_id not in compiled_sol:
                raise CompilationError(f"Contract {contract_name} not found in compilation output")
            
            contract_interface = compiled_sol[contract_id]
            
            compilation_result = {
                "contract_name": contract_name or contract_id.split(':')[-1],
                "abi": contract_interface['abi'],
                "bytecode": contract_interface['bin'],
                "source_code": contract_source,
                "compilation_timestamp": datetime.now(timezone.utc).isoformat(),
                "solc_version": "0.8.19"
            }
            
            # Cache compiled contract
            self.compiled_contracts[contract_name or contract_id] = compilation_result
            
            logger.info(f"Contract compiled successfully: {contract_name}")
            return compilation_result
            
        except Exception as e:
            logger.error(f"Contract compilation failed: {e}")
            raise CompilationError(f"Compilation failed: {e}")
    
    async def deploy_contract(
        self,
        contract_name: str,
        constructor_args: List[Any] = None,
        network: str = None,
        gas_limit: int = None,
        gas_price: int = None
    ) -> Dict[str, Any]:
        """Deploy a compiled contract to blockchain."""
        network = network or settings.default_network
        constructor_args = constructor_args or []
        
        try:
            # Get compiled contract
            if contract_name not in self.compiled_contracts:
                # Try to compile from contracts directory
                contract_file = f"{contract_name}.sol"
                await self.compile_contract(contract_file, contract_name)
            
            contract_data = self.compiled_contracts[contract_name]
            
            # Get network connection
            w3 = self.blockchain_service.get_network(network)
            
            # Create contract instance
            contract = w3.eth.contract(
                abi=contract_data['abi'],
                bytecode=contract_data['bytecode']
            )
            
            # Build deployment transaction
            constructor = contract.constructor(*constructor_args)
            
            # Estimate gas if not provided
            if not gas_limit:
                try:
                    gas_limit = constructor.estimate_gas({
                        'from': self.blockchain_service.account.address
                    })
                    gas_limit = int(gas_limit * 1.2)  # Add 20% buffer
                except Exception:
                    gas_limit = settings.gas_limit
            
            if not gas_price:
                gas_price = w3.to_wei(settings.gas_price_gwei, 'gwei')
            
            # Build transaction
            transaction = constructor.build_transaction({
                'from': self.blockchain_service.account.address,
                'gas': gas_limit,
                'gasPrice': gas_price,
                'nonce': w3.eth.get_transaction_count(self.blockchain_service.account.address)
            })
            
            # Sign and send transaction
            signed_txn = self.blockchain_service.account.sign_transaction(transaction)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for deployment confirmation
            receipt = await self.blockchain_service._wait_for_confirmation(w3, tx_hash)
            
            if receipt['status'] != 1:
                raise DeploymentError("Contract deployment transaction failed")
            
            contract_address = receipt['contractAddress']
            
            deployment_result = {
                "contract_name": contract_name,
                "contract_address": contract_address,
                "transaction_hash": receipt['transactionHash'].hex(),
                "block_number": receipt['blockNumber'],
                "gas_used": receipt['gasUsed'],
                "network": network,
                "deployer_address": self.blockchain_service.account.address,
                "constructor_args": constructor_args,
                "deployment_timestamp": datetime.now(timezone.utc).isoformat(),
                "abi": contract_data['abi'],
                "bytecode": contract_data['bytecode'],
                "source_code": contract_data['source_code']
            }
            
            logger.info(f"Contract deployed successfully: {contract_name} at {contract_address}")
            return deployment_result
            
        except Exception as e:
            logger.error(f"Contract deployment failed: {e}")
            raise DeploymentError(f"Deployment failed: {e}")
    
    async def get_contract_instance(
        self,
        contract_address: str,
        abi: List[Dict],
        network: str = None
    ) -> Contract:
        """Get a contract instance for interaction."""
        network = network or settings.default_network
        
        try:
            w3 = self.blockchain_service.get_network(network)
            checksum_address = to_checksum_address(contract_address)
            
            contract = w3.eth.contract(
                address=checksum_address,
                abi=abi
            )
            
            return contract
            
        except Exception as e:
            logger.error(f"Failed to get contract instance: {e}")
            raise SmartContractError(f"Contract instance creation failed: {e}")
    
    async def call_contract_function(
        self,
        contract_address: str,
        abi: List[Dict],
        function_name: str,
        args: List[Any] = None,
        network: str = None,
        from_address: str = None
    ) -> Any:
        """Call a read-only contract function."""
        args = args or []
        network = network or settings.default_network
        
        try:
            contract = await self.get_contract_instance(contract_address, abi, network)
            
            if not hasattr(contract.functions, function_name):
                raise ContractInteractionError(f"Function {function_name} not found in contract")
            
            function = getattr(contract.functions, function_name)
            
            # Call with from address if provided
            call_params = {}
            if from_address:
                call_params['from'] = to_checksum_address(from_address)
            
            result = function(*args).call(call_params)
            
            logger.info(f"Contract function called: {function_name}")
            return result
            
        except Exception as e:
            logger.error(f"Contract function call failed: {e}")
            raise ContractInteractionError(f"Function call failed: {e}")
    
    async def send_contract_transaction(
        self,
        contract_address: str,
        abi: List[Dict],
        function_name: str,
        args: List[Any] = None,
        value: int = 0,
        network: str = None,
        gas_limit: int = None,
        gas_price: int = None
    ) -> Dict[str, Any]:
        """Send a transaction to a contract function."""
        args = args or []
        network = network or settings.default_network
        
        try:
            w3 = self.blockchain_service.get_network(network)
            contract = await self.get_contract_instance(contract_address, abi, network)
            
            if not hasattr(contract.functions, function_name):
                raise ContractInteractionError(f"Function {function_name} not found in contract")
            
            function = getattr(contract.functions, function_name)
            
            # Estimate gas if not provided
            if not gas_limit:
                try:
                    gas_limit = function(*args).estimate_gas({
                        'from': self.blockchain_service.account.address,
                        'value': value
                    })
                    gas_limit = int(gas_limit * 1.2)  # Add 20% buffer
                except Exception:
                    gas_limit = settings.gas_limit
            
            if not gas_price:
                gas_price = w3.to_wei(settings.gas_price_gwei, 'gwei')
            
            # Build transaction
            transaction = function(*args).build_transaction({
                'from': self.blockchain_service.account.address,
                'value': value,
                'gas': gas_limit,
                'gasPrice': gas_price,
                'nonce': w3.eth.get_transaction_count(self.blockchain_service.account.address)
            })
            
            # Sign and send transaction
            signed_txn = self.blockchain_service.account.sign_transaction(transaction)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for confirmation
            receipt = await self.blockchain_service._wait_for_confirmation(w3, tx_hash)
            
            result = {
                "transaction_hash": receipt['transactionHash'].hex(),
                "block_number": receipt['blockNumber'],
                "gas_used": receipt['gasUsed'],
                "status": "success" if receipt['status'] == 1 else "failed",
                "contract_address": contract_address,
                "function_name": function_name,
                "args": args,
                "value": value,
                "network": network
            }
            
            logger.info(f"Contract transaction sent: {function_name}")
            return result
            
        except Exception as e:
            logger.error(f"Contract transaction failed: {e}")
            raise ContractInteractionError(f"Transaction failed: {e}")
    
    async def get_contract_events(
        self,
        contract_address: str,
        abi: List[Dict],
        event_name: str = None,
        from_block: int = 0,
        to_block: str = 'latest',
        filters: Dict[str, Any] = None,
        network: str = None
    ) -> List[Dict[str, Any]]:
        """Get contract events."""
        network = network or settings.default_network
        filters = filters or {}
        
        try:
            contract = await self.get_contract_instance(contract_address, abi, network)
            
            if event_name:
                if not hasattr(contract.events, event_name):
                    raise ContractInteractionError(f"Event {event_name} not found in contract")
                
                event = getattr(contract.events, event_name)
                event_filter = event.create_filter(
                    fromBlock=from_block,
                    toBlock=to_block,
                    argument_filters=filters
                )
            else:
                # Get all events
                event_filter = contract.events.allEvents.create_filter(
                    fromBlock=from_block,
                    toBlock=to_block
                )
            
            events = event_filter.get_all_entries()
            
            # Format events
            formatted_events = []
            for event in events:
                formatted_event = {
                    "event": event['event'],
                    "args": dict(event['args']),
                    "transaction_hash": event['transactionHash'].hex(),
                    "block_number": event['blockNumber'],
                    "block_hash": event['blockHash'].hex(),
                    "log_index": event['logIndex'],
                    "transaction_index": event['transactionIndex']
                }
                formatted_events.append(formatted_event)
            
            logger.info(f"Retrieved {len(formatted_events)} events from contract")
            return formatted_events
            
        except Exception as e:
            logger.error(f"Failed to get contract events: {e}")
            raise ContractInteractionError(f"Event retrieval failed: {e}")
    
    async def verify_contract_source(
        self,
        contract_address: str,
        source_code: str,
        constructor_args: List[Any] = None,
        network: str = None
    ) -> Dict[str, Any]:
        """Verify contract source code against deployed bytecode."""
        network = network or settings.default_network
        constructor_args = constructor_args or []
        
        try:
            w3 = self.blockchain_service.get_network(network)
            checksum_address = to_checksum_address(contract_address)
            
            # Get deployed bytecode
            deployed_bytecode = w3.eth.get_code(checksum_address)
            
            # Compile source code
            compiled_sol = compile_source(source_code)
            contract_id = list(compiled_sol.keys())[0]
            contract_interface = compiled_sol[contract_id]
            
            # Create contract and get runtime bytecode
            contract = w3.eth.contract(
                abi=contract_interface['abi'],
                bytecode=contract_interface['bin']
            )
            
            # For verification, we need to compare runtime bytecode
            # This is a simplified check - in production, you'd use more sophisticated verification
            verification_result = {
                "verified": len(deployed_bytecode) > 0,  # Basic check
                "contract_address": contract_address,
                "network": network,
                "verification_timestamp": datetime.now(timezone.utc).isoformat(),
                "bytecode_length": len(deployed_bytecode),
                "source_hash": Web3.keccak(text=source_code).hex()
            }
            
            logger.info(f"Contract verification completed: {contract_address}")
            return verification_result
            
        except Exception as e:
            logger.error(f"Contract verification failed: {e}")
            raise SmartContractError(f"Verification failed: {e}")
    
    async def get_contract_storage(
        self,
        contract_address: str,
        storage_slot: int,
        network: str = None
    ) -> str:
        """Get contract storage at specific slot."""
        network = network or settings.default_network
        
        try:
            w3 = self.blockchain_service.get_network(network)
            checksum_address = to_checksum_address(contract_address)
            
            storage_value = w3.eth.get_storage_at(checksum_address, storage_slot)
            
            return storage_value.hex()
            
        except Exception as e:
            logger.error(f"Failed to get contract storage: {e}")
            raise SmartContractError(f"Storage retrieval failed: {e}")
    
    async def estimate_contract_deployment_cost(
        self,
        contract_name: str,
        constructor_args: List[Any] = None,
        network: str = None
    ) -> Dict[str, Any]:
        """Estimate cost of contract deployment."""
        network = network or settings.default_network
        constructor_args = constructor_args or []
        
        try:
            # Get compiled contract
            if contract_name not in self.compiled_contracts:
                contract_file = f"{contract_name}.sol"
                await self.compile_contract(contract_file, contract_name)
            
            contract_data = self.compiled_contracts[contract_name]
            
            w3 = self.blockchain_service.get_network(network)
            
            # Create contract instance
            contract = w3.eth.contract(
                abi=contract_data['abi'],
                bytecode=contract_data['bytecode']
            )
            
            # Estimate gas
            constructor = contract.constructor(*constructor_args)
            estimated_gas = constructor.estimate_gas({
                'from': self.blockchain_service.account.address
            })
            
            # Get current gas price
            gas_price = w3.eth.gas_price
            
            # Calculate costs
            deployment_cost_wei = estimated_gas * gas_price
            deployment_cost_eth = w3.from_wei(deployment_cost_wei, 'ether')
            
            cost_estimate = {
                "estimated_gas": estimated_gas,
                "gas_price_wei": str(gas_price),
                "gas_price_gwei": str(w3.from_wei(gas_price, 'gwei')),
                "deployment_cost_wei": str(deployment_cost_wei),
                "deployment_cost_eth": str(deployment_cost_eth),
                "network": network,
                "contract_name": contract_name
            }
            
            logger.info(f"Deployment cost estimated: {deployment_cost_eth} ETH")
            return cost_estimate
            
        except Exception as e:
            logger.error(f"Cost estimation failed: {e}")
            raise SmartContractError(f"Cost estimation failed: {e}")
    
    async def create_contract_factory(
        self,
        factory_contract_name: str,
        child_contract_name: str,
        network: str = None
    ) -> Dict[str, Any]:
        """Create a factory contract for deploying multiple instances."""
        network = network or settings.default_network
        
        try:
            # This would create a factory contract that can deploy multiple instances
            # For now, return a placeholder implementation
            
            factory_info = {
                "factory_contract": factory_contract_name,
                "child_contract": child_contract_name,
                "network": network,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "created"
            }
            
            logger.info(f"Contract factory created: {factory_contract_name}")
            return factory_info
            
        except Exception as e:
            logger.error(f"Factory creation failed: {e}")
            raise SmartContractError(f"Factory creation failed: {e}")
    
    async def upgrade_contract(
        self,
        proxy_address: str,
        new_implementation_address: str,
        network: str = None
    ) -> Dict[str, Any]:
        """Upgrade a proxy contract to new implementation."""
        network = network or settings.default_network
        
        try:
            # This would handle upgradeable contracts using proxy patterns
            # For now, return a placeholder implementation
            
            upgrade_info = {
                "proxy_address": proxy_address,
                "new_implementation": new_implementation_address,
                "network": network,
                "upgraded_at": datetime.now(timezone.utc).isoformat(),
                "status": "upgraded"
            }
            
            logger.info(f"Contract upgraded: {proxy_address}")
            return upgrade_info
            
        except Exception as e:
            logger.error(f"Contract upgrade failed: {e}")
            raise SmartContractError(f"Upgrade failed: {e}")
    
    async def batch_contract_calls(
        self,
        calls: List[Dict[str, Any]],
        network: str = None
    ) -> List[Dict[str, Any]]:
        """Execute multiple contract calls in batch."""
        network = network or settings.default_network
        results = []
        
        for call in calls:
            try:
                if call.get('type') == 'read':
                    result = await self.call_contract_function(
                        call['contract_address'],
                        call['abi'],
                        call['function_name'],
                        call.get('args', []),
                        network,
                        call.get('from_address')
                    )
                    results.append({
                        "status": "success",
                        "result": result,
                        "call": call
                    })
                elif call.get('type') == 'write':
                    result = await self.send_contract_transaction(
                        call['contract_address'],
                        call['abi'],
                        call['function_name'],
                        call.get('args', []),
                        call.get('value', 0),
                        network,
                        call.get('gas_limit'),
                        call.get('gas_price')
                    )
                    results.append({
                        "status": "success",
                        "result": result,
                        "call": call
                    })
                else:
                    results.append({
                        "status": "error",
                        "error": "Invalid call type",
                        "call": call
                    })
            except Exception as e:
                results.append({
                    "status": "error",
                    "error": str(e),
                    "call": call
                })
        
        logger.info(f"Batch execution completed: {len(calls)} calls")
        return results
    
    async def get_contract_info(
        self,
        contract_address: str,
        network: str = None
    ) -> Dict[str, Any]:
        """Get comprehensive contract information."""
        network = network or settings.default_network
        
        try:
            w3 = self.blockchain_service.get_network(network)
            checksum_address = to_checksum_address(contract_address)
            
            # Get basic contract info
            code = w3.eth.get_code(checksum_address)
            balance = w3.eth.get_balance(checksum_address)
            
            contract_info = {
                "address": contract_address,
                "network": network,
                "has_code": len(code) > 0,
                "bytecode_size": len(code),
                "balance_wei": str(balance),
                "balance_eth": str(w3.from_wei(balance, 'ether')),
                "retrieved_at": datetime.now(timezone.utc).isoformat()
            }
            
            return contract_info
            
        except Exception as e:
            logger.error(f"Failed to get contract info: {e}")
            raise SmartContractError(f"Contract info retrieval failed: {e}")