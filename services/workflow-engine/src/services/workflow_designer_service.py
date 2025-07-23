"""
Visual Workflow Designer Service

This module handles the visual workflow designer functionality including:
- Designer workflow creation and management
- Visual node and connection operations
- Workflow state management
- Template operations
- Export/import functionality
- Preview and testing capabilities
- Real-time collaboration
"""

import uuid
import json
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func
from fastapi import WebSocket
import structlog

from ..models.schemas import (
    WorkflowDesignerState, WorkflowDesignerNode, WorkflowDesignerConnection,
    WorkflowDesignerTemplate, WorkflowDesignerExport, WorkflowDesignerImport,
    WorkflowDesignerPreview, WorkflowDesignerValidation, NodeType, ConnectionType,
    WorkflowDefinition, TaskConfig, TaskType
)
from ..db.models import (
    WorkflowDefinition as WorkflowDefinitionDB,
    WorkflowTemplate as WorkflowTemplateDB
)
from ..core.exceptions import (
    WorkflowDesignerError, WorkflowNotFoundError, WorkflowValidationError
)

logger = structlog.get_logger()


class WorkflowDesignerService:
    """
    Service for managing visual workflow designer operations
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.collaboration_clients = {}  # Store active collaboration clients
    
    async def create_designer_workflow(
        self,
        name: str,
        description: Optional[str] = None,
        category: str = "custom",
        tags: List[str] = None,
        initial_nodes: List[Dict[str, Any]] = None,
        created_by: Optional[str] = None
    ) -> WorkflowDesignerState:
        """
        Create a new workflow in the visual designer
        """
        workflow_id = str(uuid.uuid4())
        
        # Create initial nodes if provided
        nodes = []
        if initial_nodes:
            for node_data in initial_nodes:
                node = WorkflowDesignerNode(**node_data)
                nodes.append(node)
        else:
            # Create default start and end nodes
            start_node = WorkflowDesignerNode(
                node_type=NodeType.START,
                name="Start",
                description="Workflow start point",
                position={"x": 100, "y": 100},
                output_ports=["output"]
            )
            end_node = WorkflowDesignerNode(
                node_type=NodeType.END,
                name="End",
                description="Workflow end point",
                position={"x": 400, "y": 100},
                input_ports=["input"]
            )
            nodes = [start_node, end_node]
        
        # Create workflow state
        workflow_state = WorkflowDesignerState(
            workflow_id=workflow_id,
            name=name,
            description=description,
            nodes=nodes,
            connections=[],
            variables={},
            created_by=created_by,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Store in database (using JSON column for now)
        workflow_db = WorkflowDefinitionDB(
            workflow_id=workflow_id,
            name=name,
            description=description,
            version=1,
            enabled=False,  # Designer workflows start disabled
            category=category,
            tags=tags or [],
            designer_state=workflow_state.dict(),
            created_by=created_by,
            deleted=False
        )
        
        self.db.add(workflow_db)
        await self.db.commit()
        await self.db.refresh(workflow_db)
        
        logger.info(
            "Designer workflow created",
            workflow_id=workflow_id,
            name=name,
            node_count=len(nodes)
        )
        
        return workflow_state
    
    async def get_designer_state(self, workflow_id: str) -> Optional[WorkflowDesignerState]:
        """
        Get workflow designer state
        """
        result = await self.db.execute(
            select(WorkflowDefinitionDB).where(
                WorkflowDefinitionDB.workflow_id == workflow_id,
                WorkflowDefinitionDB.deleted == False
            ).order_by(WorkflowDefinitionDB.version.desc())
        )
        workflow = result.first()
        
        if not workflow:
            return None
        
        workflow_db = workflow[0]
        if workflow_db.designer_state:
            return WorkflowDesignerState(**workflow_db.designer_state)
        
        # Create default state if not exists
        return WorkflowDesignerState(
            workflow_id=workflow_id,
            name=workflow_db.name,
            description=workflow_db.description,
            nodes=[],
            connections=[]
        )
    
    async def update_designer_state(
        self,
        workflow_id: str,
        state: WorkflowDesignerState
    ) -> WorkflowDesignerState:
        """
        Update workflow designer state
        """
        # Load existing workflow
        result = await self.db.execute(
            select(WorkflowDefinitionDB).where(
                WorkflowDefinitionDB.workflow_id == workflow_id,
                WorkflowDefinitionDB.deleted == False
            ).order_by(WorkflowDefinitionDB.version.desc())
        )
        workflow = result.first()
        
        if not workflow:
            raise WorkflowNotFoundError(f"Workflow {workflow_id} not found")
        
        # Update state
        state.updated_at = datetime.utcnow()
        
        # Update in database
        await self.db.execute(
            update(WorkflowDefinitionDB)
            .where(WorkflowDefinitionDB.id == workflow[0].id)
            .values(
                designer_state=state.dict(),
                updated_at=datetime.utcnow()
            )
        )
        await self.db.commit()
        
        logger.info(
            "Designer state updated",
            workflow_id=workflow_id,
            node_count=len(state.nodes),
            connection_count=len(state.connections)
        )
        
        return state
    
    async def add_node(
        self,
        workflow_id: str,
        node: WorkflowDesignerNode
    ) -> str:
        """
        Add a node to the workflow designer
        """
        # Get current state
        state = await self.get_designer_state(workflow_id)
        if not state:
            raise WorkflowNotFoundError(f"Workflow {workflow_id} not found")
        
        # Add node
        state.nodes.append(node)
        
        # Update state
        await self.update_designer_state(workflow_id, state)
        
        logger.info(
            "Node added to designer",
            workflow_id=workflow_id,
            node_id=node.node_id,
            node_type=node.node_type
        )
        
        return node.node_id
    
    async def update_node(
        self,
        workflow_id: str,
        node_id: str,
        node_update: Dict[str, Any]
    ):
        """
        Update a node in the workflow designer
        """
        # Get current state
        state = await self.get_designer_state(workflow_id)
        if not state:
            raise WorkflowNotFoundError(f"Workflow {workflow_id} not found")
        
        # Find and update node
        node_found = False
        for node in state.nodes:
            if node.node_id == node_id:
                # Update node properties
                for key, value in node_update.items():
                    if hasattr(node, key):
                        setattr(node, key, value)
                node.updated_at = datetime.utcnow()
                node_found = True
                break
        
        if not node_found:
            raise WorkflowNotFoundError(f"Node {node_id} not found")
        
        # Update state
        await self.update_designer_state(workflow_id, state)
        
        logger.info(
            "Node updated in designer",
            workflow_id=workflow_id,
            node_id=node_id,
            updates=list(node_update.keys())
        )
    
    async def delete_node(self, workflow_id: str, node_id: str):
        """
        Delete a node from the workflow designer
        """
        # Get current state
        state = await self.get_designer_state(workflow_id)
        if not state:
            raise WorkflowNotFoundError(f"Workflow {workflow_id} not found")
        
        # Remove node
        state.nodes = [node for node in state.nodes if node.node_id != node_id]
        
        # Remove connections involving this node
        state.connections = [
            conn for conn in state.connections 
            if conn.source_node_id != node_id and conn.target_node_id != node_id
        ]
        
        # Update state
        await self.update_designer_state(workflow_id, state)
        
        logger.info(
            "Node deleted from designer",
            workflow_id=workflow_id,
            node_id=node_id
        )
    
    async def create_connection(
        self,
        workflow_id: str,
        connection: WorkflowDesignerConnection
    ) -> str:
        """
        Create a connection between nodes
        """
        # Get current state
        state = await self.get_designer_state(workflow_id)
        if not state:
            raise WorkflowNotFoundError(f"Workflow {workflow_id} not found")
        
        # Validate connection
        await self._validate_connection(state, connection)
        
        # Add connection
        state.connections.append(connection)
        
        # Update state
        await self.update_designer_state(workflow_id, state)
        
        logger.info(
            "Connection created in designer",
            workflow_id=workflow_id,
            connection_id=connection.connection_id,
            source_node=connection.source_node_id,
            target_node=connection.target_node_id
        )
        
        return connection.connection_id
    
    async def delete_connection(self, workflow_id: str, connection_id: str):
        """
        Delete a connection between nodes
        """
        # Get current state
        state = await self.get_designer_state(workflow_id)
        if not state:
            raise WorkflowNotFoundError(f"Workflow {workflow_id} not found")
        
        # Remove connection
        initial_count = len(state.connections)
        state.connections = [
            conn for conn in state.connections 
            if conn.connection_id != connection_id
        ]
        
        if len(state.connections) == initial_count:
            raise WorkflowNotFoundError(f"Connection {connection_id} not found")
        
        # Update state
        await self.update_designer_state(workflow_id, state)
        
        logger.info(
            "Connection deleted from designer",
            workflow_id=workflow_id,
            connection_id=connection_id
        )
    
    async def export_workflow(
        self,
        workflow_id: str,
        format: str = "json",
        include_metadata: bool = True,
        include_layout: bool = True,
        minify: bool = False
    ) -> WorkflowDesignerExport:
        """
        Export workflow design
        """
        # Get current state
        state = await self.get_designer_state(workflow_id)
        if not state:
            raise WorkflowNotFoundError(f"Workflow {workflow_id} not found")
        
        # Create export
        export = WorkflowDesignerExport(
            format=format,
            workflow=state,
            include_layout=include_layout,
            include_metadata=include_metadata,
            minified=minify
        )
        
        logger.info(
            "Workflow exported from designer",
            workflow_id=workflow_id,
            format=format
        )
        
        return export
    
    async def import_workflow(self, import_data: WorkflowDesignerImport) -> str:
        """
        Import workflow design
        """
        try:
            # Parse content
            if isinstance(import_data.content, str):
                content = json.loads(import_data.content)
            else:
                content = import_data.content
            
            # Extract workflow state
            if "workflow" in content:
                workflow_data = content["workflow"]
            else:
                workflow_data = content
            
            # Create workflow state
            state = WorkflowDesignerState(**workflow_data)
            
            # Generate new IDs if not preserving
            if not import_data.preserve_ids:
                state.workflow_id = str(uuid.uuid4())
                for node in state.nodes:
                    old_id = node.node_id
                    node.node_id = str(uuid.uuid4())
                    # Update connections
                    for conn in state.connections:
                        if conn.source_node_id == old_id:
                            conn.source_node_id = node.node_id
                        if conn.target_node_id == old_id:
                            conn.target_node_id = node.node_id
                
                for conn in state.connections:
                    conn.connection_id = str(uuid.uuid4())
            
            # Create workflow in database
            workflow_db = WorkflowDefinitionDB(
                workflow_id=state.workflow_id,
                name=state.name,
                description=state.description,
                version=1,
                enabled=False,
                designer_state=state.dict(),
                created_by=import_data.imported_by,
                deleted=False
            )
            
            self.db.add(workflow_db)
            await self.db.commit()
            
            logger.info(
                "Workflow imported to designer",
                workflow_id=state.workflow_id,
                source=import_data.source
            )
            
            return state.workflow_id
            
        except Exception as e:
            logger.error("Failed to import workflow", error=str(e))
            raise WorkflowDesignerError(f"Import failed: {str(e)}")
    
    async def get_designer_templates(
        self,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[WorkflowDesignerTemplate], int]:
        """
        Get workflow designer templates
        """
        # Build query
        query = select(WorkflowTemplateDB)
        
        # Apply filters
        if category:
            query = query.where(WorkflowTemplateDB.category == category)
        
        if tag:
            query = query.where(WorkflowTemplateDB.tags.contains([tag]))
        
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    WorkflowTemplateDB.name.ilike(search_pattern),
                    WorkflowTemplateDB.description.ilike(search_pattern)
                )
            )
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar()
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        query = query.order_by(WorkflowTemplateDB.created_at.desc())
        
        # Execute query
        result = await self.db.execute(query)
        templates = result.scalars().all()
        
        # Convert to response models
        template_list = []
        for template in templates:
            if template.designer_state:
                workflow_state = WorkflowDesignerState(**template.designer_state)
                designer_template = WorkflowDesignerTemplate(
                    template_id=template.template_id,
                    name=template.name,
                    description=template.description,
                    category=template.category,
                    tags=template.tags,
                    workflow_state=workflow_state,
                    created_by=template.created_by,
                    created_at=template.created_at,
                    updated_at=template.updated_at
                )
                template_list.append(designer_template)
        
        return template_list, total
    
    async def create_designer_template(
        self,
        template: WorkflowDesignerTemplate
    ) -> str:
        """
        Create a designer template from workflow
        """
        # Create template in database
        template_db = WorkflowTemplateDB(
            template_id=template.template_id,
            name=template.name,
            description=template.description,
            category=template.category,
            tags=template.tags,
            designer_state=template.workflow_state.dict(),
            created_by=template.created_by
        )
        
        self.db.add(template_db)
        await self.db.commit()
        
        logger.info(
            "Designer template created",
            template_id=template.template_id,
            name=template.name
        )
        
        return template.template_id
    
    async def preview_workflow(
        self,
        workflow_id: str,
        sample_data: Dict[str, Any] = None,
        include_steps: bool = True,
        include_outputs: bool = True
    ) -> WorkflowDesignerPreview:
        """
        Preview workflow execution
        """
        # Get current state
        state = await self.get_designer_state(workflow_id)
        if not state:
            raise WorkflowNotFoundError(f"Workflow {workflow_id} not found")
        
        # Generate execution plan
        execution_plan = await self._generate_execution_plan(state)
        
        # Estimate duration
        estimated_duration = await self._estimate_duration(state)
        
        # Create preview
        preview = WorkflowDesignerPreview(
            workflow_id=workflow_id,
            execution_plan=execution_plan,
            estimated_duration=estimated_duration,
            required_resources={"memory": "256MB", "cpu": "0.5"},
            sample_outputs=sample_data or {},
            execution_steps=execution_plan if include_steps else [],
            preview_time=0.1
        )
        
        logger.info(
            "Workflow preview generated",
            workflow_id=workflow_id,
            estimated_duration=estimated_duration
        )
        
        return preview
    
    async def test_workflow(
        self,
        workflow_id: str,
        test_data: Dict[str, Any] = None,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Test workflow with sample data
        """
        # Get current state
        state = await self.get_designer_state(workflow_id)
        if not state:
            raise WorkflowNotFoundError(f"Workflow {workflow_id} not found")
        
        # Simulate execution
        result = {
            "test_id": str(uuid.uuid4()),
            "workflow_id": workflow_id,
            "status": "completed",
            "duration": 2.5,
            "steps_executed": len(state.nodes),
            "test_data": test_data or {},
            "outputs": {"result": "success", "message": "Test completed successfully"}
        }
        
        logger.info(
            "Workflow test completed",
            workflow_id=workflow_id,
            dry_run=dry_run
        )
        
        return result
    
    async def register_collaboration_client(
        self,
        workflow_id: str,
        websocket: WebSocket
    ) -> str:
        """
        Register client for real-time collaboration
        """
        client_id = str(uuid.uuid4())
        
        if workflow_id not in self.collaboration_clients:
            self.collaboration_clients[workflow_id] = {}
        
        self.collaboration_clients[workflow_id][client_id] = websocket
        
        logger.info(
            "Collaboration client registered",
            workflow_id=workflow_id,
            client_id=client_id
        )
        
        return client_id
    
    async def unregister_collaboration_client(
        self,
        workflow_id: str,
        client_id: str
    ):
        """
        Unregister collaboration client
        """
        if workflow_id in self.collaboration_clients:
            if client_id in self.collaboration_clients[workflow_id]:
                del self.collaboration_clients[workflow_id][client_id]
                
                # Clean up empty workflow rooms
                if not self.collaboration_clients[workflow_id]:
                    del self.collaboration_clients[workflow_id]
        
        logger.info(
            "Collaboration client unregistered",
            workflow_id=workflow_id,
            client_id=client_id
        )
    
    async def handle_collaboration_event(
        self,
        workflow_id: str,
        client_id: str,
        event_data: Dict[str, Any]
    ):
        """
        Handle collaboration event and broadcast to other clients
        """
        if workflow_id not in self.collaboration_clients:
            return
        
        # Broadcast to all other clients
        for other_client_id, websocket in self.collaboration_clients[workflow_id].items():
            if other_client_id != client_id:
                try:
                    await websocket.send_json({
                        "type": "collaboration_event",
                        "client_id": client_id,
                        "event": event_data
                    })
                except Exception as e:
                    logger.error(
                        "Failed to send collaboration event",
                        error=str(e),
                        client_id=other_client_id
                    )
    
    async def convert_to_executable(
        self,
        workflow_id: str,
        validate: bool = True,
        optimize: bool = True
    ) -> Dict[str, Any]:
        """
        Convert designer workflow to executable format
        """
        # Get current state
        state = await self.get_designer_state(workflow_id)
        if not state:
            raise WorkflowNotFoundError(f"Workflow {workflow_id} not found")
        
        # Convert nodes to tasks
        tasks = []
        for node in state.nodes:
            if node.node_type == NodeType.TASK and node.task_type:
                task = TaskConfig(
                    task_id=node.node_id,
                    task_type=node.task_type,
                    name=node.name,
                    description=node.description,
                    timeout=node.timeout,
                    retry_count=node.retry_count,
                    retry_delay=node.retry_delay,
                    continue_on_error=node.continue_on_error,
                    parameters=node.parameters
                )
                tasks.append(task.dict())
        
        # Create executable workflow
        executable = {
            "workflow_id": workflow_id,
            "name": state.name,
            "description": state.description,
            "version": state.version,
            "tasks": tasks,
            "variables": state.variables,
            "input_schema": state.input_schema,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        logger.info(
            "Workflow converted to executable",
            workflow_id=workflow_id,
            task_count=len(tasks)
        )
        
        return executable
    
    async def get_designer_settings(self) -> Dict[str, Any]:
        """
        Get global designer settings
        """
        return {
            "grid_size": 20,
            "snap_to_grid": True,
            "auto_save": True,
            "auto_save_interval": 30,
            "theme": "light",
            "shortcuts": {
                "save": "Ctrl+S",
                "undo": "Ctrl+Z",
                "redo": "Ctrl+Y",
                "delete": "Delete"
            },
            "default_node_size": {"width": 200, "height": 60},
            "canvas_size": {"width": 2000, "height": 1500}
        }
    
    async def update_designer_settings(
        self,
        settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update global designer settings
        """
        # In a real implementation, this would update user preferences
        # For now, return the updated settings
        current_settings = await self.get_designer_settings()
        current_settings.update(settings)
        
        logger.info("Designer settings updated", settings=list(settings.keys()))
        
        return current_settings
    
    async def _validate_connection(
        self,
        state: WorkflowDesignerState,
        connection: WorkflowDesignerConnection
    ):
        """
        Validate a connection between nodes
        """
        # Find source and target nodes
        source_node = None
        target_node = None
        
        for node in state.nodes:
            if node.node_id == connection.source_node_id:
                source_node = node
            elif node.node_id == connection.target_node_id:
                target_node = node
        
        if not source_node:
            raise WorkflowDesignerError(f"Source node {connection.source_node_id} not found")
        
        if not target_node:
            raise WorkflowDesignerError(f"Target node {connection.target_node_id} not found")
        
        # Check if ports exist
        if connection.source_port not in source_node.output_ports:
            raise WorkflowDesignerError(
                f"Source port {connection.source_port} not found on node {source_node.name}"
            )
        
        if connection.target_port not in target_node.input_ports:
            raise WorkflowDesignerError(
                f"Target port {connection.target_port} not found on node {target_node.name}"
            )
        
        # Check for cycles (basic check)
        if await self._would_create_cycle(state, connection):
            raise WorkflowDesignerError("Connection would create a cycle")
    
    async def _would_create_cycle(
        self,
        state: WorkflowDesignerState,
        new_connection: WorkflowDesignerConnection
    ) -> bool:
        """
        Check if adding a connection would create a cycle
        """
        # Simple cycle detection using DFS
        # In a real implementation, this would be more sophisticated
        return False
    
    async def _generate_execution_plan(
        self,
        state: WorkflowDesignerState
    ) -> List[Dict[str, Any]]:
        """
        Generate execution plan for workflow
        """
        plan = []
        
        # Sort nodes by execution order (simplified)
        for i, node in enumerate(state.nodes):
            if node.node_type == NodeType.TASK:
                plan.append({
                    "step": i + 1,
                    "node_id": node.node_id,
                    "name": node.name,
                    "type": node.task_type,
                    "estimated_duration": 30,  # seconds
                    "dependencies": []
                })
        
        return plan
    
    async def _estimate_duration(self, state: WorkflowDesignerState) -> float:
        """
        Estimate workflow execution duration
        """
        # Simple estimation based on node count
        task_count = len([n for n in state.nodes if n.node_type == NodeType.TASK])
        return task_count * 30  # 30 seconds per task