#!/usr/bin/env python3
"""
Basic usage examples for MAMS Python SDK
"""

import os
import asyncio
from pathlib import Path
from mams import MAMSClient, AsyncMAMSClient
from mams.auth import APIKeyAuth, JWTAuth, OAuth2Provider
from mams.exceptions import MAMSError, NotFoundError, ValidationError


def basic_sync_example():
    """Basic synchronous SDK usage"""
    print("=== Basic Synchronous Usage ===")
    
    # Initialize client with API key authentication
    client = MAMSClient(
        auth=APIKeyAuth(os.getenv("MAMS_API_KEY", "your-api-key")),
        base_url=os.getenv("MAMS_BASE_URL", "https://api.mams.io")
    )
    
    try:
        # List assets
        print("\\n1. Listing assets...")
        assets = client.assets.list(limit=5)
        print(f"Found {len(assets)} assets:")
        for asset in assets:
            print(f"  - {asset.name} ({asset.type}) - {asset.id}")
        
        # Create a project
        print("\\n2. Creating a project...")
        project = client.projects.create(
            name="SDK Demo Project",
            description="A project created using the MAMS Python SDK",
            frame_rate=25.0,
            resolution="1920x1080"
        )
        print(f"Created project: {project.name} (ID: {project.id})")
        
        # Upload an asset (if file exists)
        sample_file = Path("sample_video.mp4")
        if sample_file.exists():
            print("\\n3. Uploading asset...")
            with open(sample_file, "rb") as f:
                asset = client.assets.upload(
                    file=f,
                    name=sample_file.name,
                    type="video",
                    project_id=project.id,
                    metadata={
                        "uploaded_by": "sdk_demo",
                        "source": "demo_script"
                    }
                )
            print(f"Uploaded asset: {asset.name} (ID: {asset.id})")
            
            # Add asset to project
            print("\\n4. Adding asset to project...")
            client.projects.add_asset(project.id, asset.id)
            print("Asset added to project successfully")
        
        # Search assets
        print("\\n5. Searching assets...")
        search_results = client.assets.search("demo", limit=10)
        print(f"Search returned {len(search_results)} results")
        
        # Get current user
        print("\\n6. Getting current user...")
        current_user = client.users.get_current()
        print(f"Current user: {current_user.username} ({current_user.email})")
        
    except NotFoundError as e:
        print(f"Resource not found: {e}")
    except ValidationError as e:
        print(f"Validation error: {e}")
        print(f"Errors: {e.errors}")
    except MAMSError as e:
        print(f"MAMS API error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


async def basic_async_example():
    """Basic asynchronous SDK usage"""
    print("\\n\\n=== Basic Asynchronous Usage ===")
    
    # Initialize async client
    client = AsyncMAMSClient(
        auth=APIKeyAuth(os.getenv("MAMS_API_KEY", "your-api-key")),
        base_url=os.getenv("MAMS_BASE_URL", "https://api.mams.io")
    )
    
    try:
        # Async operations
        print("\\n1. Listing assets asynchronously...")
        assets = await client.assets.list(limit=5)
        print(f"Found {len(assets)} assets")
        
        # Concurrent operations
        print("\\n2. Running concurrent operations...")
        user_task = client.users.get_current()
        projects_task = client.projects.list(limit=3)
        workflows_task = client.workflows.list(limit=3)
        
        user, projects, workflows = await asyncio.gather(
            user_task,
            projects_task,
            workflows_task,
            return_exceptions=True
        )
        
        print(f"User: {user.username if not isinstance(user, Exception) else 'Error'}")
        print(f"Projects: {len(projects) if not isinstance(projects, Exception) else 'Error'}")
        print(f"Workflows: {len(workflows) if not isinstance(workflows, Exception) else 'Error'}")
        
    except MAMSError as e:
        print(f"MAMS API error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    finally:
        await client.close()


def authentication_examples():
    """Examples of different authentication methods"""
    print("\\n\\n=== Authentication Examples ===")
    
    # API Key Authentication
    print("\\n1. API Key Authentication")
    api_key_client = MAMSClient(
        auth=APIKeyAuth("your-api-key"),
        base_url="https://api.mams.io"
    )
    print("API Key client created")
    
    # JWT Authentication
    print("\\n2. JWT Authentication")
    jwt_client = MAMSClient(
        auth=JWTAuth("your-jwt-token"),
        base_url="https://api.mams.io"
    )
    print("JWT client created")
    
    # OAuth2 Authentication
    print("\\n3. OAuth2 Authentication")
    oauth2_provider = OAuth2Provider(
        client_id="your-client-id",
        client_secret="your-client-secret",
        redirect_uri="http://localhost:8000/callback"
    )
    
    # Get authorization URL
    auth_url = oauth2_provider.get_authorization_url(state="demo-state")
    print(f"OAuth2 authorization URL: {auth_url}")
    
    # In a real application, you would redirect the user to this URL
    # and handle the callback to exchange the code for tokens
    print("(In real usage, redirect user to this URL and handle callback)")


def file_operations_example():
    """Examples of file operations"""
    print("\\n\\n=== File Operations Examples ===")
    
    client = MAMSClient(
        auth=APIKeyAuth(os.getenv("MAMS_API_KEY", "your-api-key")),
        base_url=os.getenv("MAMS_BASE_URL", "https://api.mams.io")
    )
    
    try:
        # Upload from file path
        sample_file = Path("sample_image.jpg")
        if sample_file.exists():
            print("\\n1. Uploading from file path...")
            asset = client.assets.upload_from_path(
                str(sample_file),
                metadata={"source": "demo"}
            )
            print(f"Uploaded: {asset.name}")
            
            # Get metadata
            print("\\n2. Getting asset metadata...")
            metadata = client.assets.get_metadata(asset.id)
            print(f"Metadata: {metadata}")
            
            # Update metadata
            print("\\n3. Updating metadata...")
            updated_metadata = client.assets.update_metadata(
                asset.id,
                {"processed": True, "demo_flag": True}
            )
            print("Metadata updated")
            
            # Get proxy URL
            print("\\n4. Getting proxy URL...")
            proxy_url = client.assets.get_proxy(asset.id, quality="medium")
            print(f"Proxy URL: {proxy_url}")
            
            # Download asset
            print("\\n5. Downloading asset...")
            download_path = client.assets.download(asset.id, "downloaded_asset.jpg")
            print(f"Downloaded to: {download_path}")
        
    except Exception as e:
        print(f"File operations error: {e}")


def workflow_example():
    """Example of workflow operations"""
    print("\\n\\n=== Workflow Operations ===")
    
    client = MAMSClient(
        auth=APIKeyAuth(os.getenv("MAMS_API_KEY", "your-api-key")),
        base_url=os.getenv("MAMS_BASE_URL", "https://api.mams.io")
    )
    
    try:
        # List workflows
        print("\\n1. Listing workflows...")
        workflows = client.workflows.list(limit=5)
        print(f"Found {len(workflows)} workflows")
        
        if workflows:
            workflow = workflows[0]
            print(f"Using workflow: {workflow.name}")
            
            # Start workflow execution
            print("\\n2. Starting workflow execution...")
            execution = client.workflows.start_workflow(
                workflow.id,
                context={
                    "asset_id": "sample-asset-id",
                    "action": "process",
                    "priority": "normal"
                }
            )
            print(f"Started execution: {execution['id']}")
            
            # Get execution status
            print("\\n3. Checking execution status...")
            status = client.workflows.get_execution(execution["id"])
            print(f"Status: {status['status']}")
            
            # Get execution steps
            print("\\n4. Getting execution steps...")
            steps = client.workflows.get_steps(execution["id"])
            print(f"Found {len(steps)} steps")
            
            for step in steps:
                print(f"  - {step['name']}: {step['status']}")
        
    except Exception as e:
        print(f"Workflow error: {e}")


def integration_example():
    """Example of integration operations"""
    print("\\n\\n=== Integration Operations ===")
    
    client = MAMSClient(
        auth=APIKeyAuth(os.getenv("MAMS_API_KEY", "your-api-key")),
        base_url=os.getenv("MAMS_BASE_URL", "https://api.mams.io")
    )
    
    try:
        # List integration types
        print("\\n1. Getting integration types...")
        types = client.integrations.get_types()
        print(f"Available types: {[t['name'] for t in types]}")
        
        # List integrations
        print("\\n2. Listing integrations...")
        integrations = client.integrations.list()
        print(f"Found {len(integrations)} integrations")
        
        if integrations:
            integration = integrations[0]
            print(f"Using integration: {integration.name}")
            
            # Test connection
            print("\\n3. Testing connection...")
            test_result = client.integrations.test_connection(integration.id)
            print(f"Connection test: {test_result['status']}")
            
            # Get webhooks
            print("\\n4. Getting webhooks...")
            webhooks = client.integrations.get_webhooks(integration.id)
            print(f"Found {len(webhooks)} webhooks")
            
            # Get logs
            print("\\n5. Getting integration logs...")
            logs = client.integrations.get_logs(integration.id, limit=5)
            print(f"Retrieved {len(logs)} log entries")
        
    except Exception as e:
        print(f"Integration error: {e}")


def search_example():
    """Example of search operations"""
    print("\\n\\n=== Search Operations ===")
    
    client = MAMSClient(
        auth=APIKeyAuth(os.getenv("MAMS_API_KEY", "your-api-key")),
        base_url=os.getenv("MAMS_BASE_URL", "https://api.mams.io")
    )
    
    try:
        # Basic search
        print("\\n1. Basic search...")
        results = client.search.search_assets("video", limit=5)
        print(f"Found {results.get('total', 0)} assets")
        
        # Semantic search
        print("\\n2. Semantic search...")
        semantic_results = client.search.semantic_search(
            "nature documentary footage",
            similarity_threshold=0.7
        )
        print(f"Semantic search found {len(semantic_results.get('hits', []))} results")
        
        # Get search suggestions
        print("\\n3. Getting search suggestions...")
        suggestions = client.search.get_suggestions("doc", limit=5)
        print(f"Suggestions: {suggestions}")
        
        # Get facets
        print("\\n4. Getting search facets...")
        facets = client.search.get_facets("*", facet_fields=["type", "status"])
        print(f"Available facets: {list(facets.keys())}")
        
    except Exception as e:
        print(f"Search error: {e}")


def main():
    """Run all examples"""
    print("MAMS Python SDK Examples")
    print("=" * 50)
    
    # Check for API key
    if not os.getenv("MAMS_API_KEY"):
        print("Warning: MAMS_API_KEY environment variable not set")
        print("Using placeholder API key for demonstration")
    
    # Run examples
    try:
        authentication_examples()
        basic_sync_example()
        asyncio.run(basic_async_example())
        file_operations_example()
        workflow_example()
        integration_example()
        search_example()
        
    except KeyboardInterrupt:
        print("\\n\\nExecution interrupted by user")
    except Exception as e:
        print(f"\\n\\nUnexpected error: {e}")
    
    print("\\n\\nExamples completed!")


if __name__ == "__main__":
    main()