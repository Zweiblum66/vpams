#!/usr/bin/env python3
"""
Smart contract deployment and management script for MAMS Blockchain Service.
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.smart_contract_service import SmartContractService
from services.blockchain_service import BlockchainService
from core.config import settings


class ContractDeployer:
    """Contract deployment and management class."""
    
    def __init__(self):
        self.smart_contract_service = SmartContractService()
        self.blockchain_service = BlockchainService()
        self.deployment_results = {}
    
    async def deploy_all_contracts(self, network: str = "polygon") -> Dict[str, Any]:
        """Deploy all MAMS smart contracts."""
        print(f"🚀 Starting contract deployment on {network} network...")
        
        contracts_to_deploy = [
            {
                "name": "MediaRights",
                "constructor_args": [self.blockchain_service.account.address],  # Platform fee recipient
                "description": "Media rights management contract"
            },
            {
                "name": "MediaNFT",
                "constructor_args": [
                    "MAMS Media NFT",  # name
                    "MAMS",           # symbol
                    self.blockchain_service.account.address,  # marketplace fee recipient
                    0                 # max supply (0 = unlimited)
                ],
                "description": "NFT contract for media assets"
            },
            {
                "name": "CryptoPayments",
                "constructor_args": [self.blockchain_service.account.address],  # Platform fee recipient
                "description": "Crypto payment processing contract"
            },
            {
                "name": "ProvenanceTracker",
                "constructor_args": [],  # No constructor args
                "description": "Digital asset provenance tracking contract"
            }
        ]
        
        deployment_summary = {
            "network": network,
            "deployer": self.blockchain_service.account.address,
            "deployed_contracts": [],
            "failed_deployments": [],
            "total_gas_used": 0,
            "total_deployment_cost": "0"
        }
        
        for contract_info in contracts_to_deploy:
            try:
                print(f"\n📋 Deploying {contract_info['name']}...")
                
                # First, compile the contract
                print(f"   ⚙️  Compiling {contract_info['name']}.sol...")
                compilation_result = await self.smart_contract_service.compile_contract(
                    f"{contract_info['name']}.sol",
                    contract_info['name']
                )
                print(f"   ✅ Compilation successful")
                
                # Estimate deployment cost
                print(f"   💰 Estimating deployment cost...")
                cost_estimate = await self.smart_contract_service.estimate_contract_deployment_cost(
                    contract_info['name'],
                    contract_info['constructor_args'],
                    network
                )
                print(f"   💰 Estimated cost: {cost_estimate['deployment_cost_eth']} ETH")
                print(f"   ⛽ Estimated gas: {cost_estimate['estimated_gas']}")
                
                # Deploy the contract
                print(f"   🚀 Deploying to {network}...")
                deployment_result = await self.smart_contract_service.deploy_contract(
                    contract_info['name'],
                    contract_info['constructor_args'],
                    network
                )
                
                contract_summary = {
                    "name": contract_info['name'],
                    "address": deployment_result['contract_address'],
                    "transaction_hash": deployment_result['transaction_hash'],
                    "block_number": deployment_result['block_number'],
                    "gas_used": deployment_result['gas_used'],
                    "constructor_args": contract_info['constructor_args'],
                    "description": contract_info['description']
                }
                
                deployment_summary["deployed_contracts"].append(contract_summary)
                deployment_summary["total_gas_used"] += deployment_result['gas_used']
                
                self.deployment_results[contract_info['name']] = deployment_result
                
                print(f"   ✅ {contract_info['name']} deployed successfully!")
                print(f"   📍 Address: {deployment_result['contract_address']}")
                print(f"   🧾 Transaction: {deployment_result['transaction_hash']}")
                print(f"   ⛽ Gas used: {deployment_result['gas_used']}")
                
            except Exception as e:
                print(f"   ❌ Failed to deploy {contract_info['name']}: {e}")
                deployment_summary["failed_deployments"].append({
                    "name": contract_info['name'],
                    "error": str(e)
                })
        
        # Save deployment summary
        await self.save_deployment_summary(deployment_summary, network)
        
        print(f"\n🎉 Deployment complete!")
        print(f"✅ Successfully deployed: {len(deployment_summary['deployed_contracts'])} contracts")
        print(f"❌ Failed deployments: {len(deployment_summary['failed_deployments'])}")
        print(f"⛽ Total gas used: {deployment_summary['total_gas_used']}")
        
        return deployment_summary
    
    async def verify_contracts(self, network: str = "polygon") -> Dict[str, Any]:
        """Verify deployed contracts."""
        print(f"\n🔍 Verifying deployed contracts on {network}...")
        
        verification_results = {
            "network": network,
            "verified_contracts": [],
            "verification_failures": []
        }
        
        for contract_name, deployment_result in self.deployment_results.items():
            try:
                print(f"\n   🔍 Verifying {contract_name}...")
                
                # Get source code
                contracts_dir = Path(__file__).parent.parent / "contracts"
                contract_file = contracts_dir / f"{contract_name}.sol"
                
                with open(contract_file, 'r') as f:
                    source_code = f.read()
                
                # Verify contract
                verification_result = await self.smart_contract_service.verify_contract_source(
                    deployment_result['contract_address'],
                    source_code,
                    deployment_result['constructor_args'],
                    network
                )
                
                verification_results["verified_contracts"].append({
                    "name": contract_name,
                    "address": deployment_result['contract_address'],
                    "verified": verification_result['verified'],
                    "verification_timestamp": verification_result['verification_timestamp']
                })
                
                status = "✅ VERIFIED" if verification_result['verified'] else "❌ FAILED"
                print(f"   {status} {contract_name}")
                
            except Exception as e:
                print(f"   ❌ Verification failed for {contract_name}: {e}")
                verification_results["verification_failures"].append({
                    "name": contract_name,
                    "error": str(e)
                })
        
        return verification_results
    
    async def test_contract_interactions(self, network: str = "polygon") -> Dict[str, Any]:
        """Test basic contract interactions."""
        print(f"\n🧪 Testing contract interactions on {network}...")
        
        test_results = {
            "network": network,
            "successful_tests": [],
            "failed_tests": []
        }
        
        # Test MediaRights contract
        if "MediaRights" in self.deployment_results:
            try:
                print("\n   🧪 Testing MediaRights contract...")
                media_rights = self.deployment_results["MediaRights"]
                
                # Test getting current token ID
                result = await self.smart_contract_service.call_contract_function(
                    media_rights['contract_address'],
                    media_rights['abi'],
                    "getCurrentTokenId",
                    [],
                    network
                )
                
                print(f"   ✅ Current token ID: {result}")
                test_results["successful_tests"].append({
                    "contract": "MediaRights",
                    "function": "getCurrentTokenId",
                    "result": result
                })
                
            except Exception as e:
                print(f"   ❌ MediaRights test failed: {e}")
                test_results["failed_tests"].append({
                    "contract": "MediaRights",
                    "error": str(e)
                })
        
        # Test MediaNFT contract
        if "MediaNFT" in self.deployment_results:
            try:
                print("\n   🧪 Testing MediaNFT contract...")
                media_nft = self.deployment_results["MediaNFT"]
                
                # Test getting current token ID
                result = await self.smart_contract_service.call_contract_function(
                    media_nft['contract_address'],
                    media_nft['abi'],
                    "getCurrentTokenId",
                    [],
                    network
                )
                
                print(f"   ✅ Current NFT token ID: {result}")
                test_results["successful_tests"].append({
                    "contract": "MediaNFT",
                    "function": "getCurrentTokenId",
                    "result": result
                })
                
            except Exception as e:
                print(f"   ❌ MediaNFT test failed: {e}")
                test_results["failed_tests"].append({
                    "contract": "MediaNFT",
                    "error": str(e)
                })
        
        # Test ProvenanceTracker contract
        if "ProvenanceTracker" in self.deployment_results:
            try:
                print("\n   🧪 Testing ProvenanceTracker contract...")
                provenance = self.deployment_results["ProvenanceTracker"]
                
                # Test getting current asset count
                result = await self.smart_contract_service.call_contract_function(
                    provenance['contract_address'],
                    provenance['abi'],
                    "getCurrentAssetCount",
                    [],
                    network
                )
                
                print(f"   ✅ Current asset count: {result}")
                test_results["successful_tests"].append({
                    "contract": "ProvenanceTracker",
                    "function": "getCurrentAssetCount",
                    "result": result
                })
                
            except Exception as e:
                print(f"   ❌ ProvenanceTracker test failed: {e}")
                test_results["failed_tests"].append({
                    "contract": "ProvenanceTracker",
                    "error": str(e)
                })
        
        return test_results
    
    async def save_deployment_summary(self, summary: Dict[str, Any], network: str):
        """Save deployment summary to file."""
        output_dir = Path(__file__).parent.parent / "deployments"
        output_dir.mkdir(exist_ok=True)
        
        filename = f"deployment_summary_{network}_{summary.get('timestamp', 'latest')}.json"
        output_file = output_dir / filename
        
        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        print(f"\n📄 Deployment summary saved to: {output_file}")
    
    async def show_contract_addresses(self):
        """Display all deployed contract addresses."""
        print("\n📋 Deployed Contract Addresses:")
        print("=" * 50)
        
        for contract_name, deployment_result in self.deployment_results.items():
            print(f"{contract_name:20}: {deployment_result['contract_address']}")
        
        print("=" * 50)


async def main():
    """Main deployment script."""
    print("🌟 MAMS Smart Contract Deployment Script")
    print("=" * 50)
    
    # Check if we have the required environment
    if not settings.private_key:
        print("❌ No private key configured. Please set BLOCKCHAIN_PRIVATE_KEY environment variable.")
        return
    
    if not settings.polygon_rpc_url:
        print("❌ No Polygon RPC URL configured. Please set POLYGON_RPC_URL environment variable.")
        return
    
    deployer = ContractDeployer()
    
    try:
        # Deploy contracts
        deployment_summary = await deployer.deploy_all_contracts("polygon")
        
        # Verify contracts if deployment was successful
        if deployment_summary["deployed_contracts"]:
            verification_results = await deployer.verify_contracts("polygon")
            
            # Test contract interactions
            test_results = await deployer.test_contract_interactions("polygon")
            
            # Show final summary
            await deployer.show_contract_addresses()
            
            print(f"\n🎉 All operations completed successfully!")
            print(f"📊 Summary:")
            print(f"   • Deployed: {len(deployment_summary['deployed_contracts'])} contracts")
            print(f"   • Verified: {len(verification_results['verified_contracts'])} contracts")
            print(f"   • Tests passed: {len(test_results['successful_tests'])}")
            print(f"   • Total gas used: {deployment_summary['total_gas_used']}")
        
    except Exception as e:
        print(f"\n❌ Deployment script failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())