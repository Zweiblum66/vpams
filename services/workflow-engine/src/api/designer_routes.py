"""
Visual Workflow Designer API Routes

This module provides endpoints for the visual workflow designer, including:
- Node-based workflow construction
- Visual workflow validation
- Workflow export/import capabilities
- Template management for the designer
- Real-time preview functionality
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, WebSocket, WebSocketDisconnect
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import json
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
import structlog

from ..db.base import get_db
from ..models.schemas import (
    WorkflowDesignerNode, WorkflowDesignerConnection, WorkflowDesignerLayout,
    WorkflowDesignerState, WorkflowDesignerValidation, WorkflowDesignerExport,
    WorkflowDesignerImport, WorkflowDesignerTemplate, WorkflowDesignerPreview,
    NodeType, ConnectionType, ValidationResult
)
from ..services.workflow_designer_service import WorkflowDesignerService
from ..services.node_library_service import NodeLibraryService
from ..services.designer_validation_service import DesignerValidationService
from ..core.exceptions import (
    WorkflowDesignerError, WorkflowValidationError, WorkflowNotFoundError
)

logger = structlog.get_logger()
router = APIRouter(prefix="/designer", tags=["workflow-designer"])


# Node Library Endpoints

@router.get("/nodes", response_model=Dict[str, Any])
async def get_available_nodes(
    category: Optional[str] = Query(None, description="Filter by node category"),
    search: Optional[str] = Query(None, description="Search nodes by name or description"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get available workflow nodes for the designer
    
    Returns a categorized list of available nodes that can be used
    in the visual workflow designer.
    """
    try:
        service = NodeLibraryService(db)
        nodes = await service.get_available_nodes(category=category, search=search)
        
        # Group nodes by category
        categorized_nodes = {}
        for node in nodes:
            if node.category not in categorized_nodes:
                categorized_nodes[node.category] = []
            categorized_nodes[node.category].append({
                "node_type": node.node_type,
                "name": node.name,
                "description": node.description,
                "icon": node.icon,
                "color": node.color,
                "input_ports": node.input_ports,
                "output_ports": node.output_ports,
                "parameters": node.parameters,
                "examples": node.examples
            })
        
        return {
            "categories": categorized_nodes,
            "total_nodes": len(nodes)
        }
        
    except Exception as e:
        logger.error("Failed to get available nodes", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get available nodes")


@router.get("/nodes/{node_type}", response_model=Dict[str, Any])
async def get_node_details(
    node_type: str = Path(..., description="Node type identifier"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get detailed information about a specific node type
    
    Returns comprehensive details about a node including:
    - Configuration options
    - Input/output specifications
    - Examples and documentation
    """
    try:
        service = NodeLibraryService(db)
        node = await service.get_node_details(node_type)
        
        if not node:
            raise HTTPException(status_code=404, detail="Node type not found")
        
        return {
            "node_type": node.node_type,
            "name": node.name,
            "description": node.description,
            "category": node.category,
            "icon": node.icon,
            "color": node.color,
            "input_ports": node.input_ports,
            "output_ports": node.output_ports,
            "parameters": node.parameters,
            "configuration_schema": node.configuration_schema,
            "examples": node.examples,
            "documentation": node.documentation,
            "version": node.version,
            "dependencies": node.dependencies
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get node details", node_type=node_type, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get node details")


# Workflow Designer State Management

@router.post("/workflows", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_designer_workflow(
    request: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Create a new workflow in the visual designer
    
    Creates a new workflow with initial designer state including:
    - Basic workflow metadata
    - Initial canvas layout
    - Default nodes and connections
    """
    try:
        service = WorkflowDesignerService(db)
        
        workflow = await service.create_designer_workflow(
            name=request["name"],
            description=request.get("description", ""),
            category=request.get("category", "custom"),
            tags=request.get("tags", []),
            initial_nodes=request.get("initial_nodes", []),
            created_by=request.get("created_by", "user")
        )
        
        return {
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "description": workflow.description,
            "designer_state": workflow.designer_state,
            "created_at": workflow.created_at,
            "message": "Workflow created successfully"
        }
        
    except WorkflowDesignerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to create designer workflow", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create designer workflow")


@router.get("/workflows/{workflow_id}", response_model=WorkflowDesignerState)
async def get_designer_workflow(
    workflow_id: str = Path(..., description="Workflow ID"),
    db: AsyncSession = Depends(get_db)
) -> WorkflowDesignerState:
    """
    Get workflow designer state
    
    Returns the complete visual designer state for a workflow including:
    - Node positions and configurations
    - Connection paths
    - Canvas layout settings
    - Validation status
    """
    try:
        service = WorkflowDesignerService(db)
        state = await service.get_designer_state(workflow_id)
        
        if not state:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        return state
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get designer workflow", workflow_id=workflow_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get designer workflow")


@router.patch("/workflows/{workflow_id}/state", response_model=Dict[str, Any])
async def update_designer_state(
    workflow_id: str = Path(..., description="Workflow ID"),
    state: WorkflowDesignerState,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update workflow designer state
    
    Updates the visual designer state with new node positions,
    connections, and configuration changes.
    """
    try:
        service = WorkflowDesignerService(db)
        
        updated_state = await service.update_designer_state(workflow_id, state)
        
        return {
            "workflow_id": workflow_id,
            "state": updated_state,
            "updated_at": datetime.utcnow(),
            "message": "Designer state updated successfully"
        }
        
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow not found")
    except WorkflowDesignerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to update designer state", workflow_id=workflow_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update designer state")


# Node Operations

@router.post("/workflows/{workflow_id}/nodes", response_model=Dict[str, Any])
async def add_node(
    workflow_id: str = Path(..., description="Workflow ID"),
    node: WorkflowDesignerNode,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Add a node to the workflow designer
    
    Adds a new node to the visual workflow with specified position
    and configuration.
    """
    try:
        service = WorkflowDesignerService(db)
        
        node_id = await service.add_node(workflow_id, node)
        
        return {
            "node_id": node_id,
            "workflow_id": workflow_id,
            "message": "Node added successfully"
        }
        
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow not found")
    except WorkflowDesignerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to add node", workflow_id=workflow_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to add node")


@router.patch("/workflows/{workflow_id}/nodes/{node_id}", response_model=Dict[str, Any])
async def update_node(
    workflow_id: str = Path(..., description="Workflow ID"),
    node_id: str = Path(..., description="Node ID"),
    node_update: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update a node in the workflow designer
    
    Updates node configuration, position, or other properties.
    """
    try:
        service = WorkflowDesignerService(db)
        
        await service.update_node(workflow_id, node_id, node_update)
        
        return {
            "node_id": node_id,
            "workflow_id": workflow_id,
            "message": "Node updated successfully"
        }
        
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow or node not found")
    except WorkflowDesignerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to update node", workflow_id=workflow_id, node_id=node_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update node")


@router.delete("/workflows/{workflow_id}/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node(
    workflow_id: str = Path(..., description="Workflow ID"),
    node_id: str = Path(..., description="Node ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a node from the workflow designer
    
    Removes a node and all its connections from the workflow.
    """
    try:
        service = WorkflowDesignerService(db)
        
        await service.delete_node(workflow_id, node_id)
        
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow or node not found")
    except WorkflowDesignerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to delete node", workflow_id=workflow_id, node_id=node_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete node")


# Connection Operations

@router.post("/workflows/{workflow_id}/connections", response_model=Dict[str, Any])
async def create_connection(
    workflow_id: str = Path(..., description="Workflow ID"),
    connection: WorkflowDesignerConnection,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Create a connection between nodes
    
    Creates a new connection between two nodes in the workflow.
    """
    try:
        service = WorkflowDesignerService(db)
        
        connection_id = await service.create_connection(workflow_id, connection)
        
        return {
            "connection_id": connection_id,
            "workflow_id": workflow_id,
            "message": "Connection created successfully"
        }
        
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow not found")
    except WorkflowDesignerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to create connection", workflow_id=workflow_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create connection")


@router.delete("/workflows/{workflow_id}/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    workflow_id: str = Path(..., description="Workflow ID"),
    connection_id: str = Path(..., description="Connection ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a connection between nodes
    
    Removes a connection from the workflow.
    """
    try:
        service = WorkflowDesignerService(db)
        
        await service.delete_connection(workflow_id, connection_id)
        
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow or connection not found")
    except WorkflowDesignerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to delete connection", workflow_id=workflow_id, connection_id=connection_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete connection")


# Validation

@router.post("/workflows/{workflow_id}/validate", response_model=WorkflowDesignerValidation)
async def validate_workflow(
    workflow_id: str = Path(..., description="Workflow ID"),
    db: AsyncSession = Depends(get_db)
) -> WorkflowDesignerValidation:
    """
    Validate workflow design
    
    Performs comprehensive validation of the workflow design including:
    - Node configuration validation
    - Connection validation
    - Data flow validation
    - Logic validation
    """
    try:
        service = DesignerValidationService(db)
        
        validation = await service.validate_workflow(workflow_id)
        
        return validation
        
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow not found")
    except Exception as e:
        logger.error("Failed to validate workflow", workflow_id=workflow_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to validate workflow")


@router.post("/workflows/{workflow_id}/validate/realtime", response_model=Dict[str, Any])
async def validate_realtime(
    workflow_id: str = Path(..., description="Workflow ID"),
    state: WorkflowDesignerState,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Perform real-time validation of workflow state
    
    Validates the current designer state without saving changes.
    Used for real-time feedback in the designer UI.
    """
    try:
        service = DesignerValidationService(db)
        
        validation = await service.validate_state(workflow_id, state)
        
        return {
            "valid": validation.is_valid,
            "errors": validation.errors,
            "warnings": validation.warnings,
            "suggestions": validation.suggestions,
            "validation_time": validation.validation_time
        }
        
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow not found")
    except Exception as e:
        logger.error("Failed to validate realtime", workflow_id=workflow_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to validate workflow state")


# Export/Import

@router.post("/workflows/{workflow_id}/export", response_model=WorkflowDesignerExport)
async def export_workflow(
    workflow_id: str = Path(..., description="Workflow ID"),
    export_options: Dict[str, Any] = {},
    db: AsyncSession = Depends(get_db)
) -> WorkflowDesignerExport:
    """
    Export workflow design
    
    Exports the workflow design in various formats:
    - JSON format for backup/sharing
    - Template format for reuse
    - Execution format for workflow engine
    """
    try:
        service = WorkflowDesignerService(db)
        
        export = await service.export_workflow(
            workflow_id,
            format=export_options.get("format", "json"),
            include_metadata=export_options.get("include_metadata", True),
            include_layout=export_options.get("include_layout", True),
            minify=export_options.get("minify", False)
        )
        
        return export
        
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow not found")
    except Exception as e:
        logger.error("Failed to export workflow", workflow_id=workflow_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to export workflow")


@router.post("/workflows/import", response_model=Dict[str, Any])
async def import_workflow(
    import_data: WorkflowDesignerImport,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Import workflow design
    
    Imports a workflow design from various formats:
    - JSON format from exports
    - Template format
    - Third-party workflow formats
    """
    try:
        service = WorkflowDesignerService(db)
        
        workflow_id = await service.import_workflow(import_data)
        
        return {
            "workflow_id": workflow_id,
            "message": "Workflow imported successfully"
        }
        
    except WorkflowDesignerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to import workflow", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to import workflow")


# Templates

@router.get("/templates", response_model=Dict[str, Any])
async def get_designer_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    search: Optional[str] = Query(None, description="Search templates"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get workflow designer templates
    
    Returns a list of available workflow templates for the designer.
    """
    try:
        service = WorkflowDesignerService(db)
        
        templates, total = await service.get_designer_templates(
            category=category,
            tag=tag,
            search=search,
            page=page,
            page_size=page_size
        )
        
        return {
            "templates": templates,
            "total": total,
            "page": page,
            "page_size": page_size
        }
        
    except Exception as e:
        logger.error("Failed to get designer templates", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get designer templates")


@router.post("/templates", response_model=Dict[str, Any])
async def create_designer_template(
    template: WorkflowDesignerTemplate,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Create a designer template from workflow
    
    Creates a reusable template from an existing workflow design.
    """
    try:
        service = WorkflowDesignerService(db)
        
        template_id = await service.create_designer_template(template)
        
        return {
            "template_id": template_id,
            "message": "Template created successfully"
        }
        
    except WorkflowDesignerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to create designer template", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create designer template")


# Preview and Testing

@router.post("/workflows/{workflow_id}/preview", response_model=WorkflowDesignerPreview)
async def preview_workflow(
    workflow_id: str = Path(..., description="Workflow ID"),
    preview_options: Dict[str, Any] = {},
    db: AsyncSession = Depends(get_db)
) -> WorkflowDesignerPreview:
    """
    Preview workflow execution
    
    Generates a preview of how the workflow would execute with
    sample data, without actually running it.
    """
    try:
        service = WorkflowDesignerService(db)
        
        preview = await service.preview_workflow(
            workflow_id,
            sample_data=preview_options.get("sample_data", {}),
            include_steps=preview_options.get("include_steps", True),
            include_outputs=preview_options.get("include_outputs", True)
        )
        
        return preview
        
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow not found")
    except Exception as e:
        logger.error("Failed to preview workflow", workflow_id=workflow_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to preview workflow")


@router.post("/workflows/{workflow_id}/test", response_model=Dict[str, Any])
async def test_workflow(
    workflow_id: str = Path(..., description="Workflow ID"),
    test_data: Dict[str, Any] = {},
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Test workflow with sample data
    
    Executes the workflow with test data to verify it works correctly.
    This is a safe execution that doesn't affect production data.
    """
    try:
        service = WorkflowDesignerService(db)
        
        result = await service.test_workflow(
            workflow_id,
            test_data=test_data,
            dry_run=True
        )
        
        return {
            "test_result": result,
            "message": "Workflow test completed"
        }
        
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow not found")
    except WorkflowDesignerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to test workflow", workflow_id=workflow_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to test workflow")


# Real-time Collaboration (WebSocket)

@router.websocket("/workflows/{workflow_id}/collaborate")
async def collaborate_on_workflow(
    websocket: WebSocket,
    workflow_id: str = Path(..., description="Workflow ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Real-time collaboration on workflow design
    
    WebSocket endpoint for real-time collaborative editing of workflows.
    Multiple users can edit the same workflow simultaneously.
    """
    await websocket.accept()
    
    try:
        service = WorkflowDesignerService(db)
        
        # Register client for collaboration
        client_id = await service.register_collaboration_client(workflow_id, websocket)
        
        try:
            while True:
                # Receive client messages
                data = await websocket.receive_json()
                
                # Process collaboration event
                await service.handle_collaboration_event(
                    workflow_id, 
                    client_id, 
                    data
                )
                
        except WebSocketDisconnect:
            # Client disconnected
            await service.unregister_collaboration_client(workflow_id, client_id)
            
    except Exception as e:
        logger.error("WebSocket collaboration error", workflow_id=workflow_id, error=str(e))
        await websocket.close(code=1011, reason="Internal server error")


# Workflow Conversion

@router.post("/workflows/{workflow_id}/convert", response_model=Dict[str, Any])
async def convert_to_executable(
    workflow_id: str = Path(..., description="Workflow ID"),
    conversion_options: Dict[str, Any] = {},
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Convert designer workflow to executable format
    
    Converts the visual workflow design into an executable workflow
    that can be run by the workflow engine.
    """
    try:
        service = WorkflowDesignerService(db)
        
        executable_workflow = await service.convert_to_executable(
            workflow_id,
            validate=conversion_options.get("validate", True),
            optimize=conversion_options.get("optimize", True)
        )
        
        return {
            "executable_workflow": executable_workflow,
            "workflow_id": workflow_id,
            "message": "Workflow converted to executable format"
        }
        
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow not found")
    except WorkflowDesignerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to convert workflow", workflow_id=workflow_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to convert workflow")


# Designer Settings

@router.get("/settings", response_model=Dict[str, Any])
async def get_designer_settings(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get workflow designer settings
    
    Returns global settings for the workflow designer including:
    - Default node positions
    - Grid settings
    - Theme settings
    - Keyboard shortcuts
    """
    try:
        service = WorkflowDesignerService(db)
        
        settings = await service.get_designer_settings()
        
        return settings
        
    except Exception as e:
        logger.error("Failed to get designer settings", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get designer settings")


@router.patch("/settings", response_model=Dict[str, Any])
async def update_designer_settings(
    settings: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update workflow designer settings
    
    Updates global settings for the workflow designer.
    """
    try:
        service = WorkflowDesignerService(db)
        
        updated_settings = await service.update_designer_settings(settings)
        
        return {
            "settings": updated_settings,
            "message": "Designer settings updated successfully"
        }
        
    except Exception as e:
        logger.error("Failed to update designer settings", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update designer settings")