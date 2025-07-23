"""
Designer Validation Service

This module handles validation of visual workflow designs including:
- Node configuration validation
- Connection validation
- Data flow validation
- Workflow logic validation
- Performance and resource validation
- Best practices checking
"""

import time
from datetime import datetime
from typing import List, Optional, Dict, Any, Set, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from ..models.schemas import (
    WorkflowDesignerState, WorkflowDesignerNode, WorkflowDesignerConnection,
    WorkflowDesignerValidation, ValidationResult, NodeType, ConnectionType,
    TaskType
)
from ..services.node_library_service import NodeLibraryService
from ..core.exceptions import (
    WorkflowValidationError, NodeNotFoundError
)

logger = structlog.get_logger()


class DesignerValidationService:
    """
    Service for validating visual workflow designs
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.node_library_service = NodeLibraryService(db_session)
    
    async def validate_workflow(self, workflow_id: str) -> WorkflowDesignerValidation:
        """
        Perform comprehensive validation of workflow design
        """
        start_time = time.time()
        
        # Get workflow state (in a real implementation, this would fetch from DB)
        # For now, we'll create a mock state
        state = WorkflowDesignerState(
            workflow_id=workflow_id,
            name="Test Workflow",
            nodes=[],
            connections=[]
        )
        
        # Perform validation
        validation = await self.validate_state(workflow_id, state)
        validation.validation_time = time.time() - start_time
        
        return validation
    
    async def validate_state(
        self,
        workflow_id: str,
        state: WorkflowDesignerState
    ) -> WorkflowDesignerValidation:
        """
        Validate the current designer state
        """
        start_time = time.time()
        
        errors = []
        warnings = []
        suggestions = []
        node_validations = {}
        connection_validations = {}
        
        # Validate nodes
        for node in state.nodes:
            node_validation = await self._validate_node(node)
            node_validations[node.node_id] = node_validation
            
            if not node_validation.is_valid:
                errors.extend([
                    {
                        "type": "node_error",
                        "node_id": node.node_id,
                        "message": error
                    }
                    for error in node_validation.errors
                ])
            
            warnings.extend([
                {
                    "type": "node_warning",
                    "node_id": node.node_id,
                    "message": warning
                }
                for warning in node_validation.warnings
            ])
            
            suggestions.extend([
                {
                    "type": "node_suggestion",
                    "node_id": node.node_id,
                    "message": suggestion
                }
                for suggestion in node_validation.suggestions
            ])
        
        # Validate connections
        for connection in state.connections:
            connection_validation = await self._validate_connection(state, connection)
            connection_validations[connection.connection_id] = connection_validation
            
            if not connection_validation.is_valid:
                errors.extend([
                    {
                        "type": "connection_error",
                        "connection_id": connection.connection_id,
                        "message": error
                    }
                    for error in connection_validation.errors
                ])
            
            warnings.extend([
                {
                    "type": "connection_warning",
                    "connection_id": connection.connection_id,
                    "message": warning
                }
                for warning in connection_validation.warnings
            ])
        
        # Validate workflow flow
        flow_validation = await self._validate_workflow_flow(state)
        
        if not flow_validation.is_valid:
            errors.extend([
                {
                    "type": "flow_error",
                    "message": error
                }
                for error in flow_validation.errors
            ])
        
        warnings.extend([
            {
                "type": "flow_warning",
                "message": warning
            }
            for warning in flow_validation.warnings
        ])
        
        suggestions.extend([
            {
                "type": "flow_suggestion",
                "message": suggestion
            }
            for suggestion in flow_validation.suggestions
        ])
        
        # Check for additional workflow-level issues
        await self._validate_workflow_structure(state, errors, warnings, suggestions)
        await self._validate_workflow_performance(state, warnings, suggestions)
        await self._validate_workflow_best_practices(state, warnings, suggestions)
        
        # Create validation result
        validation_time = time.time() - start_time
        is_valid = len(errors) == 0
        
        validation = WorkflowDesignerValidation(
            workflow_id=workflow_id,
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            node_validations=node_validations,
            connection_validations=connection_validations,
            flow_validation=flow_validation,
            validation_time=validation_time,
            validated_at=datetime.utcnow()
        )
        
        logger.info(
            "Workflow validation completed",
            workflow_id=workflow_id,
            is_valid=is_valid,
            error_count=len(errors),
            warning_count=len(warnings),
            suggestion_count=len(suggestions),
            validation_time=validation_time
        )
        
        return validation
    
    async def _validate_node(self, node: WorkflowDesignerNode) -> ValidationResult:
        """
        Validate a single node
        """
        start_time = time.time()
        errors = []
        warnings = []
        suggestions = []
        
        # Basic node validation
        if not node.name or not node.name.strip():
            errors.append("Node name is required")
        
        if not node.node_type:
            errors.append("Node type is required")
        
        # Validate node type
        if node.node_type == NodeType.TASK:
            if not node.task_type:
                errors.append("Task type is required for task nodes")
            else:
                # Validate task type exists in node library
                node_details = await self.node_library_service.get_node_details(node.task_type)
                if not node_details:
                    errors.append(f"Unknown task type: {node.task_type}")
                else:
                    # Validate node parameters
                    if node.parameters:
                        param_validation = await self.node_library_service.validate_node_parameters(
                            node.task_type, node.parameters
                        )
                        if not param_validation["valid"]:
                            errors.extend(param_validation["errors"])
        
        # Validate ports
        if node.node_type not in [NodeType.START, NodeType.END]:
            if not node.input_ports and not node.output_ports:
                warnings.append("Node has no input or output ports")
        
        # Validate position
        if node.position["x"] < 0 or node.position["y"] < 0:
            warnings.append("Node position should be positive")
        
        # Validate timeout
        if node.timeout and node.timeout <= 0:
            errors.append("Node timeout must be positive")
        
        # Validate retry configuration
        if node.retry_count < 0:
            errors.append("Retry count cannot be negative")
        
        if node.retry_delay < 0:
            errors.append("Retry delay cannot be negative")
        
        # Suggestions
        if node.node_type == NodeType.TASK:
            if not node.description:
                suggestions.append("Consider adding a description to clarify node purpose")
            
            if node.timeout and node.timeout > 3600:  # 1 hour
                suggestions.append("Consider if such a long timeout is necessary")
            
            if node.retry_count > 5:
                suggestions.append("High retry count might indicate design issues")
        
        validation_time = time.time() - start_time
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            validation_time=validation_time,
            validated_at=datetime.utcnow()
        )
    
    async def _validate_connection(
        self,
        state: WorkflowDesignerState,
        connection: WorkflowDesignerConnection
    ) -> ValidationResult:
        """
        Validate a single connection
        """
        start_time = time.time()
        errors = []
        warnings = []
        suggestions = []
        
        # Find source and target nodes
        source_node = None
        target_node = None
        
        for node in state.nodes:
            if node.node_id == connection.source_node_id:
                source_node = node
            elif node.node_id == connection.target_node_id:
                target_node = node
        
        if not source_node:
            errors.append(f"Source node {connection.source_node_id} not found")
        
        if not target_node:
            errors.append(f"Target node {connection.target_node_id} not found")
        
        if source_node and target_node:
            # Validate ports exist
            if connection.source_port not in source_node.output_ports:
                errors.append(f"Source port '{connection.source_port}' not found on node '{source_node.name}'")
            
            if connection.target_port not in target_node.input_ports:
                errors.append(f"Target port '{connection.target_port}' not found on node '{target_node.name}'")
            
            # Validate connection types
            if connection.connection_type == ConnectionType.CONDITIONAL:
                if not connection.condition:
                    errors.append("Conditional connections must have a condition")
            
            # Check for self-connections
            if connection.source_node_id == connection.target_node_id:
                errors.append("Node cannot connect to itself")
            
            # Check for duplicate connections
            duplicate_connections = [
                conn for conn in state.connections
                if (conn.connection_id != connection.connection_id and
                    conn.source_node_id == connection.source_node_id and
                    conn.target_node_id == connection.target_node_id and
                    conn.source_port == connection.source_port and
                    conn.target_port == connection.target_port)
            ]
            
            if duplicate_connections:
                warnings.append("Duplicate connection detected")
            
            # Suggestions
            if source_node.node_type == NodeType.END:
                suggestions.append("End nodes typically don't have outgoing connections")
            
            if target_node.node_type == NodeType.START:
                suggestions.append("Start nodes typically don't have incoming connections")
        
        validation_time = time.time() - start_time
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            validation_time=validation_time,
            validated_at=datetime.utcnow()
        )
    
    async def _validate_workflow_flow(self, state: WorkflowDesignerState) -> ValidationResult:
        """
        Validate workflow execution flow
        """
        start_time = time.time()
        errors = []
        warnings = []
        suggestions = []
        
        # Check for start and end nodes
        start_nodes = [node for node in state.nodes if node.node_type == NodeType.START]
        end_nodes = [node for node in state.nodes if node.node_type == NodeType.END]
        
        if not start_nodes:
            errors.append("Workflow must have at least one start node")
        elif len(start_nodes) > 1:
            warnings.append("Multiple start nodes detected")
        
        if not end_nodes:
            errors.append("Workflow must have at least one end node")
        elif len(end_nodes) > 1:
            warnings.append("Multiple end nodes detected")
        
        # Check for cycles
        if await self._has_cycles(state):
            errors.append("Workflow contains cycles")
        
        # Check for unreachable nodes
        unreachable_nodes = await self._find_unreachable_nodes(state)
        if unreachable_nodes:
            warnings.extend([
                f"Node '{node.name}' is unreachable" for node in unreachable_nodes
            ])
        
        # Check for dead ends
        dead_end_nodes = await self._find_dead_end_nodes(state)
        if dead_end_nodes:
            warnings.extend([
                f"Node '{node.name}' has no outgoing connections" for node in dead_end_nodes
                if node.node_type not in [NodeType.END]
            ])
        
        # Check for disconnected components
        disconnected_components = await self._find_disconnected_components(state)
        if len(disconnected_components) > 1:
            warnings.append(f"Workflow has {len(disconnected_components)} disconnected components")
        
        # Suggestions
        if len(state.nodes) > 20:
            suggestions.append("Consider breaking large workflows into smaller, reusable components")
        
        if len(state.connections) > 30:
            suggestions.append("Complex connection patterns might benefit from simplification")
        
        validation_time = time.time() - start_time
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            validation_time=validation_time,
            validated_at=datetime.utcnow()
        )
    
    async def _validate_workflow_structure(
        self,
        state: WorkflowDesignerState,
        errors: List[Dict[str, Any]],
        warnings: List[Dict[str, Any]],
        suggestions: List[Dict[str, Any]]
    ):
        """
        Validate workflow structure
        """
        # Check for empty workflow
        if not state.nodes:
            errors.append({
                "type": "structure_error",
                "message": "Workflow cannot be empty"
            })
            return
        
        # Check for minimum viable workflow
        if len(state.nodes) < 2:
            warnings.append({
                "type": "structure_warning",
                "message": "Workflow should have at least start and end nodes"
            })
        
        # Check for proper node naming
        node_names = [node.name for node in state.nodes]
        duplicate_names = [name for name in node_names if node_names.count(name) > 1]
        if duplicate_names:
            warnings.append({
                "type": "structure_warning",
                "message": f"Duplicate node names found: {', '.join(set(duplicate_names))}"
            })
        
        # Check for proper workflow metadata
        if not state.name or not state.name.strip():
            errors.append({
                "type": "structure_error",
                "message": "Workflow name is required"
            })
        
        if not state.description:
            suggestions.append({
                "type": "structure_suggestion",
                "message": "Consider adding a workflow description"
            })
    
    async def _validate_workflow_performance(
        self,
        state: WorkflowDesignerState,
        warnings: List[Dict[str, Any]],
        suggestions: List[Dict[str, Any]]
    ):
        """
        Validate workflow performance characteristics
        """
        # Check for potential performance issues
        parallel_nodes = [node for node in state.nodes if node.node_type == NodeType.PARALLEL]
        if len(parallel_nodes) > 5:
            warnings.append({
                "type": "performance_warning",
                "message": "Many parallel nodes may impact system performance"
            })
        
        # Check for long-running tasks
        long_running_nodes = [
            node for node in state.nodes
            if node.timeout and node.timeout > 1800  # 30 minutes
        ]
        if long_running_nodes:
            warnings.append({
                "type": "performance_warning",
                "message": f"{len(long_running_nodes)} nodes have long timeout values"
            })
        
        # Check for excessive retry counts
        high_retry_nodes = [
            node for node in state.nodes
            if node.retry_count > 3
        ]
        if high_retry_nodes:
            suggestions.append({
                "type": "performance_suggestion",
                "message": "Consider reducing retry counts for better performance"
            })
    
    async def _validate_workflow_best_practices(
        self,
        state: WorkflowDesignerState,
        warnings: List[Dict[str, Any]],
        suggestions: List[Dict[str, Any]]
    ):
        """
        Validate workflow against best practices
        """
        # Check for error handling
        nodes_without_error_handling = [
            node for node in state.nodes
            if node.node_type == NodeType.TASK and not node.continue_on_error
        ]
        
        error_connections = [
            conn for conn in state.connections
            if conn.connection_type == ConnectionType.FAILURE
        ]
        
        if nodes_without_error_handling and not error_connections:
            suggestions.append({
                "type": "best_practice_suggestion",
                "message": "Consider adding error handling to your workflow"
            })
        
        # Check for documentation
        undocumented_nodes = [
            node for node in state.nodes
            if node.node_type == NodeType.TASK and not node.description
        ]
        
        if len(undocumented_nodes) > len(state.nodes) * 0.5:
            suggestions.append({
                "type": "best_practice_suggestion",
                "message": "Consider adding descriptions to more nodes for better maintainability"
            })
        
        # Check for variable usage
        if state.variables:
            # Check if variables are actually used
            suggestions.append({
                "type": "best_practice_suggestion",
                "message": "Ensure all defined variables are used in the workflow"
            })
    
    async def _has_cycles(self, state: WorkflowDesignerState) -> bool:
        """
        Check if workflow contains cycles using DFS
        """
        # Build adjacency list
        graph = {}
        for node in state.nodes:
            graph[node.node_id] = []
        
        for connection in state.connections:
            if connection.source_node_id in graph:
                graph[connection.source_node_id].append(connection.target_node_id)
        
        # DFS to detect cycles
        visited = set()
        rec_stack = set()
        
        def dfs(node_id):
            if node_id in rec_stack:
                return True
            if node_id in visited:
                return False
            
            visited.add(node_id)
            rec_stack.add(node_id)
            
            for neighbor in graph.get(node_id, []):
                if dfs(neighbor):
                    return True
            
            rec_stack.remove(node_id)
            return False
        
        for node_id in graph:
            if node_id not in visited:
                if dfs(node_id):
                    return True
        
        return False
    
    async def _find_unreachable_nodes(self, state: WorkflowDesignerState) -> List[WorkflowDesignerNode]:
        """
        Find nodes that cannot be reached from start nodes
        """
        start_nodes = [node for node in state.nodes if node.node_type == NodeType.START]
        if not start_nodes:
            return []
        
        # Build adjacency list
        graph = {}
        for node in state.nodes:
            graph[node.node_id] = []
        
        for connection in state.connections:
            if connection.source_node_id in graph:
                graph[connection.source_node_id].append(connection.target_node_id)
        
        # BFS from start nodes
        reachable = set()
        queue = [node.node_id for node in start_nodes]
        
        while queue:
            node_id = queue.pop(0)
            if node_id in reachable:
                continue
            
            reachable.add(node_id)
            for neighbor in graph.get(node_id, []):
                if neighbor not in reachable:
                    queue.append(neighbor)
        
        # Find unreachable nodes
        unreachable = []
        for node in state.nodes:
            if node.node_id not in reachable and node.node_type != NodeType.START:
                unreachable.append(node)
        
        return unreachable
    
    async def _find_dead_end_nodes(self, state: WorkflowDesignerState) -> List[WorkflowDesignerNode]:
        """
        Find nodes with no outgoing connections
        """
        nodes_with_outgoing = set()
        for connection in state.connections:
            nodes_with_outgoing.add(connection.source_node_id)
        
        dead_ends = []
        for node in state.nodes:
            if node.node_id not in nodes_with_outgoing:
                dead_ends.append(node)
        
        return dead_ends
    
    async def _find_disconnected_components(self, state: WorkflowDesignerState) -> List[List[str]]:
        """
        Find disconnected components in the workflow
        """
        # Build undirected graph
        graph = {}
        for node in state.nodes:
            graph[node.node_id] = []
        
        for connection in state.connections:
            if connection.source_node_id in graph:
                graph[connection.source_node_id].append(connection.target_node_id)
            if connection.target_node_id in graph:
                graph[connection.target_node_id].append(connection.source_node_id)
        
        # Find connected components
        visited = set()
        components = []
        
        def dfs(node_id, component):
            if node_id in visited:
                return
            
            visited.add(node_id)
            component.append(node_id)
            
            for neighbor in graph.get(node_id, []):
                dfs(neighbor, component)
        
        for node_id in graph:
            if node_id not in visited:
                component = []
                dfs(node_id, component)
                components.append(component)
        
        return components