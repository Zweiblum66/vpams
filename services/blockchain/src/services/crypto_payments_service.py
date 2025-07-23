"""
Comprehensive cryptocurrency payment processing service.
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
from eth_utils import to_checksum_address, to_wei, from_wei
import structlog

from ..core.config import settings
from ..db.models import NetworkType, TransactionStatus
from .blockchain_service import BlockchainService
from .ipfs_service import IPFSService

logger = structlog.get_logger()


@dataclass
class PaymentRequest:
    """Payment request data structure."""
    recipient: str
    amount: Decimal
    currency: str
    description: str
    invoice_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    expires_at: Optional[str] = None


@dataclass
class SubscriptionPlan:
    """Subscription plan data structure."""
    plan_id: str
    name: str
    description: str
    amount: Decimal
    currency: str
    interval: str  # "monthly", "yearly", "weekly"
    max_subscriptions: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EscrowDetails:
    """Escrow transaction details."""
    buyer: str
    seller: str
    amount: Decimal
    currency: str
    description: str
    conditions: List[str]
    arbitrator: Optional[str] = None
    timeout_hours: int = 72
    metadata: Optional[Dict[str, Any]] = None


class CryptoPaymentsError(Exception):
    """Base exception for crypto payment operations."""
    pass


class PaymentValidationError(CryptoPaymentsError):
    """Raised when payment validation fails."""
    pass


class InsufficientFundsError(CryptoPaymentsError):
    """Raised when account has insufficient funds."""
    pass


class CryptoPaymentsService:
    """Comprehensive cryptocurrency payment processing service."""
    
    def __init__(self):
        self.blockchain_service = BlockchainService()
        self.ipfs_service = IPFSService()
        self.payments_contract_abi = self._load_payments_contract_abi()
    
    def _load_payments_contract_abi(self) -> List[Dict]:
        """Load CryptoPayments contract ABI."""
        return [
            {
                "inputs": [
                    {"name": "recipient", "type": "address"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "currency", "type": "string"},
                    {"name": "description", "type": "string"},
                    {"name": "metadata", "type": "string"}
                ],
                "name": "processPayment",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "planId", "type": "string"},
                    {"name": "name", "type": "string"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "interval", "type": "uint256"},
                    {"name": "maxSubscriptions", "type": "uint256"}
                ],
                "name": "createSubscriptionPlan",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "planId", "type": "string"}
                ],
                "name": "subscribe",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "subscriptionId", "type": "uint256"}
                ],
                "name": "cancelSubscription",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "invoiceId", "type": "string"},
                    {"name": "recipient", "type": "address"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "dueDate", "type": "uint256"},
                    {"name": "description", "type": "string"}
                ],
                "name": "createInvoice",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "invoiceId", "type": "string"}
                ],
                "name": "payInvoice",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "escrowId", "type": "string"},
                    {"name": "seller", "type": "address"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "timeoutHours", "type": "uint256"},
                    {"name": "conditions", "type": "string"}
                ],
                "name": "createEscrow",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "escrowId", "type": "string"}
                ],
                "name": "releaseEscrow",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "escrowId", "type": "string"}
                ],
                "name": "refundEscrow",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "amount", "type": "uint256"}
                ],
                "name": "withdrawFunds",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "paymentId", "type": "uint256"}
                ],
                "name": "payments",
                "outputs": [
                    {"name": "id", "type": "uint256"},
                    {"name": "sender", "type": "address"},
                    {"name": "recipient", "type": "address"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "currency", "type": "string"},
                    {"name": "status", "type": "uint8"},
                    {"name": "timestamp", "type": "uint256"},
                    {"name": "description", "type": "string"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "user", "type": "address"}
                ],
                "name": "getUserBalance",
                "outputs": [
                    {"name": "", "type": "uint256"}
                ],
                "stateMutability": "view",
                "type": "function"
            }
        ]
    
    async def process_payment(
        self,
        payment_request: PaymentRequest,
        sender_address: str,
        network: str = None
    ) -> Dict[str, Any]:
        """Process a cryptocurrency payment."""
        network = network or settings.default_network
        
        try:
            # Validate payment request
            await self._validate_payment_request(payment_request, sender_address, network)
            
            # Upload payment metadata to IPFS
            payment_metadata = {
                "recipient": payment_request.recipient,
                "amount": str(payment_request.amount),
                "currency": payment_request.currency,
                "description": payment_request.description,
                "invoice_id": payment_request.invoice_id,
                "metadata": payment_request.metadata or {},
                "created_at": datetime.now(timezone.utc).isoformat(),
                "sender": sender_address
            }
            
            metadata_result = await self.ipfs_service.upload_json(
                payment_metadata,
                content_type="payment_metadata",
                pin=True
            )
            
            # Get blockchain network and contract
            w3 = self.blockchain_service.get_network(network)
            contract_address = self.blockchain_service._get_contract_address(network, "payments")
            
            if not contract_address:
                raise CryptoPaymentsError(f"No payments contract deployed on {network}")
            
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.payments_contract_abi
            )
            
            # Convert amount to wei (assuming ETH-based networks)
            amount_wei = to_wei(payment_request.amount, 'ether')
            
            # Build transaction
            transaction = contract.functions.processPayment(
                to_checksum_address(payment_request.recipient),
                amount_wei,
                payment_request.currency,
                payment_request.description,
                metadata_result["gateway_url"]
            ).build_transaction({
                'from': to_checksum_address(sender_address),
                'value': amount_wei,
                'gas': settings.gas_limit,
                'gasPrice': w3.to_wei(settings.gas_price_gwei, 'gwei'),
                'nonce': w3.eth.get_transaction_count(to_checksum_address(sender_address))
            })
            
            # Sign and send transaction
            signed_txn = self.blockchain_service.account.sign_transaction(transaction)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for confirmation
            receipt = await self.blockchain_service._wait_for_confirmation(w3, tx_hash)
            
            # Extract payment ID from logs
            payment_id = None
            for log in receipt['logs']:
                try:
                    decoded_log = contract.events.PaymentProcessed().processLog(log)
                    payment_id = decoded_log['args']['paymentId']
                    break
                except:
                    continue
            
            result = {
                "payment_id": payment_id,
                "transaction_hash": receipt['transactionHash'].hex(),
                "block_number": receipt['blockNumber'],
                "sender": sender_address,
                "recipient": payment_request.recipient,
                "amount": str(payment_request.amount),
                "currency": payment_request.currency,
                "status": "completed",
                "metadata_uri": metadata_result["gateway_url"],
                "ipfs_hash": metadata_result["ipfs_hash"],
                "network": network,
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Payment processed: {payment_id} - {payment_request.amount} {payment_request.currency}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process payment: {e}")
            raise CryptoPaymentsError(f"Payment processing failed: {e}")
    
    async def create_subscription_plan(
        self,
        plan: SubscriptionPlan,
        creator_address: str,
        network: str = None
    ) -> Dict[str, Any]:
        """Create a subscription plan."""
        network = network or settings.default_network
        
        try:
            # Upload plan metadata to IPFS
            plan_metadata = asdict(plan)
            plan_metadata["creator"] = creator_address
            plan_metadata["created_at"] = datetime.now(timezone.utc).isoformat()
            
            metadata_result = await self.ipfs_service.upload_json(
                plan_metadata,
                content_type="subscription_plan",
                pin=True
            )
            
            # Get contract
            w3 = self.blockchain_service.get_network(network)
            contract_address = self.blockchain_service._get_contract_address(network, "payments")
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.payments_contract_abi
            )
            
            # Convert interval to seconds
            interval_seconds = self._convert_interval_to_seconds(plan.interval)
            amount_wei = to_wei(plan.amount, 'ether')
            max_subs = plan.max_subscriptions or 0
            
            # Create subscription plan on blockchain
            transaction = contract.functions.createSubscriptionPlan(
                plan.plan_id,
                plan.name,
                amount_wei,
                interval_seconds,
                max_subs
            ).build_transaction({
                'from': to_checksum_address(creator_address),
                'gas': settings.gas_limit,
                'gasPrice': w3.to_wei(settings.gas_price_gwei, 'gwei'),
                'nonce': w3.eth.get_transaction_count(to_checksum_address(creator_address))
            })
            
            signed_txn = self.blockchain_service.account.sign_transaction(transaction)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            receipt = await self.blockchain_service._wait_for_confirmation(w3, tx_hash)
            
            result = {
                "plan_id": plan.plan_id,
                "name": plan.name,
                "amount": str(plan.amount),
                "currency": plan.currency,
                "interval": plan.interval,
                "max_subscriptions": plan.max_subscriptions,
                "creator": creator_address,
                "transaction_hash": receipt['transactionHash'].hex(),
                "block_number": receipt['blockNumber'],
                "metadata_uri": metadata_result["gateway_url"],
                "ipfs_hash": metadata_result["ipfs_hash"],
                "network": network,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Subscription plan created: {plan.plan_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create subscription plan: {e}")
            raise CryptoPaymentsError(f"Subscription plan creation failed: {e}")
    
    async def subscribe_to_plan(
        self,
        plan_id: str,
        subscriber_address: str,
        network: str = None
    ) -> Dict[str, Any]:
        """Subscribe to a subscription plan."""
        network = network or settings.default_network
        
        try:
            # Get plan details first
            plan_info = await self.get_subscription_plan(plan_id, network)
            
            # Get contract
            w3 = self.blockchain_service.get_network(network)
            contract_address = self.blockchain_service._get_contract_address(network, "payments")
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.payments_contract_abi
            )
            
            # Subscribe to plan
            amount_wei = to_wei(Decimal(plan_info["amount"]), 'ether')
            
            transaction = contract.functions.subscribe(
                plan_id
            ).build_transaction({
                'from': to_checksum_address(subscriber_address),
                'value': amount_wei,
                'gas': settings.gas_limit,
                'gasPrice': w3.to_wei(settings.gas_price_gwei, 'gwei'),
                'nonce': w3.eth.get_transaction_count(to_checksum_address(subscriber_address))
            })
            
            signed_txn = self.blockchain_service.account.sign_transaction(transaction)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            receipt = await self.blockchain_service._wait_for_confirmation(w3, tx_hash)
            
            # Extract subscription ID from logs
            subscription_id = None
            for log in receipt['logs']:
                try:
                    decoded_log = contract.events.SubscriptionCreated().processLog(log)
                    subscription_id = decoded_log['args']['subscriptionId']
                    break
                except:
                    continue
            
            result = {
                "subscription_id": subscription_id,
                "plan_id": plan_id,
                "subscriber": subscriber_address,
                "amount": plan_info["amount"],
                "transaction_hash": receipt['transactionHash'].hex(),
                "block_number": receipt['blockNumber'],
                "network": network,
                "subscribed_at": datetime.now(timezone.utc).isoformat(),
                "next_payment_due": self._calculate_next_payment_date(plan_info["interval"])
            }
            
            logger.info(f"Subscription created: {subscription_id} for plan {plan_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to subscribe to plan: {e}")
            raise CryptoPaymentsError(f"Subscription failed: {e}")
    
    async def cancel_subscription(
        self,
        subscription_id: int,
        subscriber_address: str,
        network: str = None
    ) -> Dict[str, Any]:
        """Cancel a subscription."""
        network = network or settings.default_network
        
        try:
            # Get contract
            w3 = self.blockchain_service.get_network(network)
            contract_address = self.blockchain_service._get_contract_address(network, "payments")
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.payments_contract_abi
            )
            
            # Cancel subscription
            transaction = contract.functions.cancelSubscription(
                subscription_id
            ).build_transaction({
                'from': to_checksum_address(subscriber_address),
                'gas': settings.gas_limit,
                'gasPrice': w3.to_wei(settings.gas_price_gwei, 'gwei'),
                'nonce': w3.eth.get_transaction_count(to_checksum_address(subscriber_address))
            })
            
            signed_txn = self.blockchain_service.account.sign_transaction(transaction)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            receipt = await self.blockchain_service._wait_for_confirmation(w3, tx_hash)
            
            result = {
                "subscription_id": subscription_id,
                "subscriber": subscriber_address,
                "status": "cancelled",
                "transaction_hash": receipt['transactionHash'].hex(),
                "block_number": receipt['blockNumber'],
                "network": network,
                "cancelled_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Subscription cancelled: {subscription_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to cancel subscription: {e}")
            raise CryptoPaymentsError(f"Subscription cancellation failed: {e}")
    
    async def create_invoice(
        self,
        invoice_id: str,
        recipient_address: str,
        amount: Decimal,
        currency: str,
        description: str,
        due_date: datetime,
        issuer_address: str,
        network: str = None
    ) -> Dict[str, Any]:
        """Create an invoice."""
        network = network or settings.default_network
        
        try:
            # Upload invoice metadata to IPFS
            invoice_metadata = {
                "invoice_id": invoice_id,
                "recipient": recipient_address,
                "amount": str(amount),
                "currency": currency,
                "description": description,
                "due_date": due_date.isoformat(),
                "issuer": issuer_address,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "pending"
            }
            
            metadata_result = await self.ipfs_service.upload_json(
                invoice_metadata,
                content_type="invoice",
                pin=True
            )
            
            # Get contract
            w3 = self.blockchain_service.get_network(network)
            contract_address = self.blockchain_service._get_contract_address(network, "payments")
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.payments_contract_abi
            )
            
            # Create invoice on blockchain
            amount_wei = to_wei(amount, 'ether')
            due_timestamp = int(due_date.timestamp())
            
            transaction = contract.functions.createInvoice(
                invoice_id,
                to_checksum_address(recipient_address),
                amount_wei,
                due_timestamp,
                description
            ).build_transaction({
                'from': to_checksum_address(issuer_address),
                'gas': settings.gas_limit,
                'gasPrice': w3.to_wei(settings.gas_price_gwei, 'gwei'),
                'nonce': w3.eth.get_transaction_count(to_checksum_address(issuer_address))
            })
            
            signed_txn = self.blockchain_service.account.sign_transaction(transaction)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            receipt = await self.blockchain_service._wait_for_confirmation(w3, tx_hash)
            
            result = {
                "invoice_id": invoice_id,
                "recipient": recipient_address,
                "amount": str(amount),
                "currency": currency,
                "description": description,
                "due_date": due_date.isoformat(),
                "issuer": issuer_address,
                "status": "pending",
                "transaction_hash": receipt['transactionHash'].hex(),
                "block_number": receipt['blockNumber'],
                "metadata_uri": metadata_result["gateway_url"],
                "ipfs_hash": metadata_result["ipfs_hash"],
                "network": network,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Invoice created: {invoice_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create invoice: {e}")
            raise CryptoPaymentsError(f"Invoice creation failed: {e}")
    
    async def pay_invoice(
        self,
        invoice_id: str,
        payer_address: str,
        network: str = None
    ) -> Dict[str, Any]:
        """Pay an invoice."""
        network = network or settings.default_network
        
        try:
            # Get invoice details first
            invoice_info = await self.get_invoice(invoice_id, network)
            
            # Get contract
            w3 = self.blockchain_service.get_network(network)
            contract_address = self.blockchain_service._get_contract_address(network, "payments")
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.payments_contract_abi
            )
            
            # Pay invoice
            amount_wei = to_wei(Decimal(invoice_info["amount"]), 'ether')
            
            transaction = contract.functions.payInvoice(
                invoice_id
            ).build_transaction({
                'from': to_checksum_address(payer_address),
                'value': amount_wei,
                'gas': settings.gas_limit,
                'gasPrice': w3.to_wei(settings.gas_price_gwei, 'gwei'),
                'nonce': w3.eth.get_transaction_count(to_checksum_address(payer_address))
            })
            
            signed_txn = self.blockchain_service.account.sign_transaction(transaction)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            receipt = await self.blockchain_service._wait_for_confirmation(w3, tx_hash)
            
            result = {
                "invoice_id": invoice_id,
                "payer": payer_address,
                "amount": invoice_info["amount"],
                "status": "paid",
                "transaction_hash": receipt['transactionHash'].hex(),
                "block_number": receipt['blockNumber'],
                "network": network,
                "paid_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Invoice paid: {invoice_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to pay invoice: {e}")
            raise CryptoPaymentsError(f"Invoice payment failed: {e}")
    
    async def create_escrow(
        self,
        escrow_details: EscrowDetails,
        escrow_id: str,
        network: str = None
    ) -> Dict[str, Any]:
        """Create an escrow transaction."""
        network = network or settings.default_network
        
        try:
            # Upload escrow metadata to IPFS
            escrow_metadata = asdict(escrow_details)
            escrow_metadata["escrow_id"] = escrow_id
            escrow_metadata["created_at"] = datetime.now(timezone.utc).isoformat()
            escrow_metadata["status"] = "active"
            
            metadata_result = await self.ipfs_service.upload_json(
                escrow_metadata,
                content_type="escrow",
                pin=True
            )
            
            # Get contract
            w3 = self.blockchain_service.get_network(network)
            contract_address = self.blockchain_service._get_contract_address(network, "payments")
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.payments_contract_abi
            )
            
            # Create escrow on blockchain
            amount_wei = to_wei(escrow_details.amount, 'ether')
            conditions_json = json.dumps(escrow_details.conditions)
            
            transaction = contract.functions.createEscrow(
                escrow_id,
                to_checksum_address(escrow_details.seller),
                amount_wei,
                escrow_details.timeout_hours,
                conditions_json
            ).build_transaction({
                'from': to_checksum_address(escrow_details.buyer),
                'value': amount_wei,
                'gas': settings.gas_limit,
                'gasPrice': w3.to_wei(settings.gas_price_gwei, 'gwei'),
                'nonce': w3.eth.get_transaction_count(to_checksum_address(escrow_details.buyer))
            })
            
            signed_txn = self.blockchain_service.account.sign_transaction(transaction)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            receipt = await self.blockchain_service._wait_for_confirmation(w3, tx_hash)
            
            result = {
                "escrow_id": escrow_id,
                "buyer": escrow_details.buyer,
                "seller": escrow_details.seller,
                "amount": str(escrow_details.amount),
                "currency": escrow_details.currency,
                "description": escrow_details.description,
                "conditions": escrow_details.conditions,
                "arbitrator": escrow_details.arbitrator,
                "timeout_hours": escrow_details.timeout_hours,
                "status": "active",
                "transaction_hash": receipt['transactionHash'].hex(),
                "block_number": receipt['blockNumber'],
                "metadata_uri": metadata_result["gateway_url"],
                "ipfs_hash": metadata_result["ipfs_hash"],
                "network": network,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(hours=escrow_details.timeout_hours)).isoformat()
            }
            
            logger.info(f"Escrow created: {escrow_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create escrow: {e}")
            raise CryptoPaymentsError(f"Escrow creation failed: {e}")
    
    async def release_escrow(
        self,
        escrow_id: str,
        releaser_address: str,
        network: str = None
    ) -> Dict[str, Any]:
        """Release funds from escrow to seller."""
        network = network or settings.default_network
        
        try:
            # Get contract
            w3 = self.blockchain_service.get_network(network)
            contract_address = self.blockchain_service._get_contract_address(network, "payments")
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.payments_contract_abi
            )
            
            # Release escrow
            transaction = contract.functions.releaseEscrow(
                escrow_id
            ).build_transaction({
                'from': to_checksum_address(releaser_address),
                'gas': settings.gas_limit,
                'gasPrice': w3.to_wei(settings.gas_price_gwei, 'gwei'),
                'nonce': w3.eth.get_transaction_count(to_checksum_address(releaser_address))
            })
            
            signed_txn = self.blockchain_service.account.sign_transaction(transaction)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            receipt = await self.blockchain_service._wait_for_confirmation(w3, tx_hash)
            
            result = {
                "escrow_id": escrow_id,
                "releaser": releaser_address,
                "status": "released",
                "transaction_hash": receipt['transactionHash'].hex(),
                "block_number": receipt['blockNumber'],
                "network": network,
                "released_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Escrow released: {escrow_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to release escrow: {e}")
            raise CryptoPaymentsError(f"Escrow release failed: {e}")
    
    async def refund_escrow(
        self,
        escrow_id: str,
        refunder_address: str,
        network: str = None
    ) -> Dict[str, Any]:
        """Refund escrow to buyer."""
        network = network or settings.default_network
        
        try:
            # Get contract
            w3 = self.blockchain_service.get_network(network)
            contract_address = self.blockchain_service._get_contract_address(network, "payments")
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.payments_contract_abi
            )
            
            # Refund escrow
            transaction = contract.functions.refundEscrow(
                escrow_id
            ).build_transaction({
                'from': to_checksum_address(refunder_address),
                'gas': settings.gas_limit,
                'gasPrice': w3.to_wei(settings.gas_price_gwei, 'gwei'),
                'nonce': w3.eth.get_transaction_count(to_checksum_address(refunder_address))
            })
            
            signed_txn = self.blockchain_service.account.sign_transaction(transaction)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            receipt = await self.blockchain_service._wait_for_confirmation(w3, tx_hash)
            
            result = {
                "escrow_id": escrow_id,
                "refunder": refunder_address,
                "status": "refunded",
                "transaction_hash": receipt['transactionHash'].hex(),
                "block_number": receipt['blockNumber'],
                "network": network,
                "refunded_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Escrow refunded: {escrow_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to refund escrow: {e}")
            raise CryptoPaymentsError(f"Escrow refund failed: {e}")
    
    async def get_payment_info(
        self,
        payment_id: int,
        network: str = None
    ) -> Dict[str, Any]:
        """Get payment information from blockchain."""
        network = network or settings.default_network
        
        try:
            w3 = self.blockchain_service.get_network(network)
            contract_address = self.blockchain_service._get_contract_address(network, "payments")
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.payments_contract_abi
            )
            
            # Get payment data
            payment_data = contract.functions.payments(payment_id).call()
            
            payment_info = {
                "payment_id": payment_data[0],
                "sender": payment_data[1],
                "recipient": payment_data[2],
                "amount": str(from_wei(payment_data[3], 'ether')),
                "currency": payment_data[4],
                "status": payment_data[5],  # Convert enum to string
                "timestamp": datetime.fromtimestamp(payment_data[6], tz=timezone.utc).isoformat(),
                "description": payment_data[7],
                "network": network
            }
            
            return payment_info
            
        except Exception as e:
            logger.error(f"Failed to get payment info: {e}")
            raise CryptoPaymentsError(f"Payment info retrieval failed: {e}")
    
    async def get_user_balance(
        self,
        user_address: str,
        network: str = None
    ) -> Dict[str, Any]:
        """Get user balance from payments contract."""
        network = network or settings.default_network
        
        try:
            w3 = self.blockchain_service.get_network(network)
            contract_address = self.blockchain_service._get_contract_address(network, "payments")
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.payments_contract_abi
            )
            
            # Get user balance from contract
            contract_balance_wei = contract.functions.getUserBalance(to_checksum_address(user_address)).call()
            contract_balance = from_wei(contract_balance_wei, 'ether')
            
            # Get native token balance
            native_balance_wei = w3.eth.get_balance(to_checksum_address(user_address))
            native_balance = from_wei(native_balance_wei, 'ether')
            
            return {
                "user_address": user_address,
                "contract_balance": str(contract_balance),
                "native_balance": str(native_balance),
                "total_balance": str(contract_balance + native_balance),
                "network": network,
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get user balance: {e}")
            raise CryptoPaymentsError(f"Balance retrieval failed: {e}")
    
    async def withdraw_funds(
        self,
        amount: Decimal,
        user_address: str,
        network: str = None
    ) -> Dict[str, Any]:
        """Withdraw funds from payments contract."""
        network = network or settings.default_network
        
        try:
            # Get contract
            w3 = self.blockchain_service.get_network(network)
            contract_address = self.blockchain_service._get_contract_address(network, "payments")
            contract = w3.eth.contract(
                address=contract_address,
                abi=self.payments_contract_abi
            )
            
            # Withdraw funds
            amount_wei = to_wei(amount, 'ether')
            
            transaction = contract.functions.withdrawFunds(
                amount_wei
            ).build_transaction({
                'from': to_checksum_address(user_address),
                'gas': settings.gas_limit,
                'gasPrice': w3.to_wei(settings.gas_price_gwei, 'gwei'),
                'nonce': w3.eth.get_transaction_count(to_checksum_address(user_address))
            })
            
            signed_txn = self.blockchain_service.account.sign_transaction(transaction)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            receipt = await self.blockchain_service._wait_for_confirmation(w3, tx_hash)
            
            result = {
                "user_address": user_address,
                "amount": str(amount),
                "transaction_hash": receipt['transactionHash'].hex(),
                "block_number": receipt['blockNumber'],
                "network": network,
                "withdrawn_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Funds withdrawn: {amount} for {user_address}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to withdraw funds: {e}")
            raise CryptoPaymentsError(f"Fund withdrawal failed: {e}")
    
    async def _validate_payment_request(
        self,
        payment_request: PaymentRequest,
        sender_address: str,
        network: str
    ) -> None:
        """Validate a payment request."""
        # Check recipient address format
        if not payment_request.recipient.startswith("0x") or len(payment_request.recipient) != 42:
            raise PaymentValidationError("Invalid recipient address format")
        
        # Check amount
        if payment_request.amount <= 0:
            raise PaymentValidationError("Payment amount must be greater than 0")
        
        # Check sender balance
        balance_info = await self.get_user_balance(sender_address, network)
        if Decimal(balance_info["native_balance"]) < payment_request.amount:
            raise InsufficientFundsError("Insufficient balance for payment")
        
        # Check expiration
        if payment_request.expires_at:
            expires_at = datetime.fromisoformat(payment_request.expires_at.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > expires_at:
                raise PaymentValidationError("Payment request has expired")
    
    def _convert_interval_to_seconds(self, interval: str) -> int:
        """Convert interval string to seconds."""
        intervals = {
            "daily": 86400,
            "weekly": 604800,
            "monthly": 2592000,  # 30 days
            "yearly": 31536000   # 365 days
        }
        return intervals.get(interval.lower(), 2592000)  # Default to monthly
    
    def _calculate_next_payment_date(self, interval: str) -> str:
        """Calculate next payment due date."""
        interval_seconds = self._convert_interval_to_seconds(interval)
        next_payment = datetime.now(timezone.utc) + timedelta(seconds=interval_seconds)
        return next_payment.isoformat()
    
    async def get_subscription_plan(self, plan_id: str, network: str = None) -> Dict[str, Any]:
        """Get subscription plan details."""
        # This would interact with the blockchain to get plan details
        # For now, return a mock implementation
        return {
            "plan_id": plan_id,
            "name": "Mock Plan",
            "amount": "10.0",
            "interval": "monthly",
            "network": network or settings.default_network
        }
    
    async def get_invoice(self, invoice_id: str, network: str = None) -> Dict[str, Any]:
        """Get invoice details."""
        # This would interact with the blockchain to get invoice details
        # For now, return a mock implementation
        return {
            "invoice_id": invoice_id,
            "amount": "5.0",
            "currency": "ETH",
            "status": "pending",
            "network": network or settings.default_network
        }