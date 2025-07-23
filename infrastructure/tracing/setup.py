#!/usr/bin/env python3
"""
MAMS Distributed Tracing Setup Script

This script sets up the distributed tracing infrastructure for MAMS,
including index templates, lifecycle policies, and initial configuration.
"""

import os
import sys
import json
import time
import requests
from typing import Dict, Any, Optional
import urllib3
from requests.auth import HTTPBasicAuth

# Disable SSL warnings for development
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class TracingSetup:
    """Setup class for MAMS distributed tracing infrastructure."""
    
    def __init__(self, opensearch_url: str = "https://localhost:9200"):
        self.opensearch_url = opensearch_url
        self.auth = HTTPBasicAuth("admin", "OpenSearch123!")
        self.session = requests.Session()
        self.session.verify = False
        self.session.auth = self.auth
        
    def wait_for_opensearch(self, timeout: int = 120) -> bool:
        """Wait for OpenSearch to be ready."""
        print("Waiting for OpenSearch to be ready...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = self.session.get(f"{self.opensearch_url}/_cluster/health")
                if response.status_code == 200:
                    health = response.json()
                    if health["status"] in ["green", "yellow"]:
                        print(f"OpenSearch is ready (status: {health['status']})")
                        return True
            except Exception as e:
                print(f"Waiting for OpenSearch: {e}")
            
            time.sleep(5)
        
        print("Timeout waiting for OpenSearch")
        return False
    
    def create_index_template(self, template_name: str, template_config: Dict[str, Any]) -> bool:
        """Create an index template in OpenSearch."""
        url = f"{self.opensearch_url}/_index_template/{template_name}"
        
        try:
            response = self.session.put(url, json=template_config)
            if response.status_code in [200, 201]:
                print(f"✓ Created index template: {template_name}")
                return True
            else:
                print(f"✗ Failed to create index template {template_name}: {response.text}")
                return False
        except Exception as e:
            print(f"✗ Error creating index template {template_name}: {e}")
            return False
    
    def create_lifecycle_policy(self, policy_name: str, policy_config: Dict[str, Any]) -> bool:
        """Create an index lifecycle policy."""
        url = f"{self.opensearch_url}/_plugins/_ism/policies/{policy_name}"
        
        try:
            response = self.session.put(url, json=policy_config)
            if response.status_code in [200, 201]:
                print(f"✓ Created lifecycle policy: {policy_name}")
                return True
            else:
                print(f"✗ Failed to create lifecycle policy {policy_name}: {response.text}")
                return False
        except Exception as e:
            print(f"✗ Error creating lifecycle policy {policy_name}: {e}")
            return False
    
    def create_index_alias(self, alias_name: str, index_pattern: str) -> bool:
        """Create an index alias."""
        alias_config = {
            "actions": [
                {
                    "add": {
                        "index": index_pattern,
                        "alias": alias_name
                    }
                }
            ]
        }
        
        url = f"{self.opensearch_url}/_aliases"
        
        try:
            response = self.session.post(url, json=alias_config)
            if response.status_code == 200:
                print(f"✓ Created index alias: {alias_name}")
                return True
            else:
                print(f"✗ Failed to create index alias {alias_name}: {response.text}")
                return False
        except Exception as e:
            print(f"✗ Error creating index alias {alias_name}: {e}")
            return False
    
    def setup_jaeger_templates(self) -> bool:
        """Setup Jaeger index templates."""
        print("\n=== Setting up Jaeger index templates ===")
        
        # Load span template
        span_template_path = "./jaeger/index-templates/jaeger-span-template.json"
        if os.path.exists(span_template_path):
            with open(span_template_path, 'r') as f:
                span_template = json.load(f)
            
            if not self.create_index_template("mams-jaeger-span", span_template):
                return False
        else:
            print(f"✗ Span template file not found: {span_template_path}")
            return False
        
        # Load service template
        service_template_path = "./jaeger/index-templates/jaeger-service-template.json"
        if os.path.exists(service_template_path):
            with open(service_template_path, 'r') as f:
                service_template = json.load(f)
            
            if not self.create_index_template("mams-jaeger-service", service_template):
                return False
        else:
            print(f"✗ Service template file not found: {service_template_path}")
            return False
        
        return True
    
    def setup_lifecycle_policies(self) -> bool:
        """Setup index lifecycle policies for traces."""
        print("\n=== Setting up lifecycle policies ===")
        
        # Jaeger span policy
        span_policy = {
            "policy": {
                "description": "MAMS Jaeger spans lifecycle policy",
                "default_state": "hot",
                "states": [
                    {
                        "name": "hot",
                        "actions": [
                            {
                                "rollover": {
                                    "min_size": "5gb",
                                    "min_doc_count": 1000000,
                                    "min_index_age": "1d"
                                }
                            }
                        ],
                        "transitions": [
                            {
                                "state_name": "warm",
                                "conditions": {
                                    "min_index_age": "3d"
                                }
                            }
                        ]
                    },
                    {
                        "name": "warm",
                        "actions": [
                            {
                                "replica_count": {
                                    "number_of_replicas": 0
                                }
                            },
                            {
                                "force_merge": {
                                    "max_num_segments": 1
                                }
                            }
                        ],
                        "transitions": [
                            {
                                "state_name": "cold",
                                "conditions": {
                                    "min_index_age": "7d"
                                }
                            }
                        ]
                    },
                    {
                        "name": "cold",
                        "actions": [
                            {
                                "allocation": {
                                    "number_of_replicas": 0
                                }
                            }
                        ],
                        "transitions": [
                            {
                                "state_name": "delete",
                                "conditions": {
                                    "min_index_age": "30d"
                                }
                            }
                        ]
                    },
                    {
                        "name": "delete",
                        "actions": [
                            {
                                "delete": {}
                            }
                        ]
                    }
                ],
                "ism_template": [
                    {
                        "index_patterns": ["mams-jaeger-span-*"],
                        "priority": 100
                    }
                ]
            }
        }
        
        if not self.create_lifecycle_policy("mams-jaeger-policy", span_policy):
            return False
        
        # Jaeger service policy (shorter retention)
        service_policy = {
            "policy": {
                "description": "MAMS Jaeger services lifecycle policy",
                "default_state": "hot",
                "states": [
                    {
                        "name": "hot",
                        "actions": [
                            {
                                "rollover": {
                                    "min_size": "1gb",
                                    "min_doc_count": 100000,
                                    "min_index_age": "1d"
                                }
                            }
                        ],
                        "transitions": [
                            {
                                "state_name": "delete",
                                "conditions": {
                                    "min_index_age": "7d"
                                }
                            }
                        ]
                    },
                    {
                        "name": "delete",
                        "actions": [
                            {
                                "delete": {}
                            }
                        ]
                    }
                ],
                "ism_template": [
                    {
                        "index_patterns": ["mams-jaeger-service-*"],
                        "priority": 100
                    }
                ]
            }
        }
        
        if not self.create_lifecycle_policy("mams-jaeger-service-policy", service_policy):
            return False
        
        return True
    
    def setup_index_aliases(self) -> bool:
        """Setup index aliases for trace data."""
        print("\n=== Setting up index aliases ===")
        
        aliases = [
            ("mams-jaeger-spans", "mams-jaeger-span-*"),
            ("mams-jaeger-services", "mams-jaeger-service-*"),
            ("mams-traces", "mams-jaeger-span-*,mams-tempo-*"),
        ]
        
        for alias_name, index_pattern in aliases:
            if not self.create_index_alias(alias_name, index_pattern):
                return False
        
        return True
    
    def verify_setup(self) -> bool:
        """Verify the tracing setup."""
        print("\n=== Verifying setup ===")
        
        # Check cluster health
        try:
            response = self.session.get(f"{self.opensearch_url}/_cluster/health")
            health = response.json()
            print(f"✓ Cluster health: {health['status']}")
        except Exception as e:
            print(f"✗ Failed to check cluster health: {e}")
            return False
        
        # Check templates
        try:
            response = self.session.get(f"{self.opensearch_url}/_index_template")
            templates = response.json()["index_templates"]
            template_names = [t["name"] for t in templates if "mams-jaeger" in t["name"]]
            print(f"✓ Found {len(template_names)} MAMS Jaeger templates")
        except Exception as e:
            print(f"✗ Failed to check templates: {e}")
            return False
        
        # Check policies
        try:
            response = self.session.get(f"{self.opensearch_url}/_plugins/_ism/policies")
            policies = response.json()["policies"]
            policy_names = [p["_id"] for p in policies if "mams-jaeger" in p["_id"]]
            print(f"✓ Found {len(policy_names)} MAMS Jaeger policies")
        except Exception as e:
            print(f"✗ Failed to check policies: {e}")
            return False
        
        return True
    
    def run_setup(self) -> bool:
        """Run the complete tracing setup."""
        print("🚀 Starting MAMS Distributed Tracing Setup")
        print("=" * 50)
        
        # Wait for OpenSearch
        if not self.wait_for_opensearch():
            return False
        
        # Setup components
        steps = [
            self.setup_jaeger_templates,
            self.setup_lifecycle_policies,
            self.setup_index_aliases,
            self.verify_setup,
        ]
        
        for step in steps:
            if not step():
                print(f"\n❌ Setup failed at step: {step.__name__}")
                return False
        
        print("\n✅ MAMS Distributed Tracing setup completed successfully!")
        print("\nNext steps:")
        print("1. Start the tracing stack: docker-compose -f docker-compose.tracing.yml up -d")
        print("2. Access Jaeger UI: http://localhost:16686")
        print("3. Access Trace Analytics: http://localhost:5601")
        print("4. Instrument your services using shared/tracing/python_tracing.py")
        
        return True


def main():
    """Main function."""
    # Get OpenSearch URL from environment or use default
    opensearch_url = os.getenv("OPENSEARCH_URL", "https://localhost:9200")
    
    # Create setup instance
    setup = TracingSetup(opensearch_url)
    
    # Run setup
    success = setup.run_setup()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()