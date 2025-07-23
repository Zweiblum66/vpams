"""Data Lineage Service for tracking data flow and transformations"""

import logging
from typing import List, Optional, Dict, Any, Set, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.orm import selectinload
from uuid import UUID, uuid4
import json
import hashlib
from collections import defaultdict, deque

from ..db.models import (
    DataLineageNode, DataLineageEdge, DataTransformation, DataFlowSession,
    DataLineageMetadata, DataLineageSnapshot, DataImpactAnalysis
)
from ..models.schemas import (
    DataLineageNodeCreate, DataLineageNodeUpdate, DataLineageNodeResponse,
    DataLineageEdgeCreate, DataLineageEdgeResponse,
    DataTransformationCreate, DataTransformationResponse,
    DataFlowSessionCreate, DataFlowSessionResponse,
    DataLineageGraphResponse, DataLineageMetricsResponse,
    DataImpactAnalysisRequest, DataImpactAnalysisResponse,
    LineageDirection, NodeType, TransformationType
)
from ..core.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)


class DataLineageService:
    """Service for managing data lineage and flow tracking"""
    
    def __init__(self, db: AsyncSession):
        self.db = db

    # Node Management
    
    async def create_node(
        self,
        node_data: DataLineageNodeCreate,
        created_by: str
    ) -> DataLineageNodeResponse:
        """Create a new data lineage node"""
        try:
            # Check for existing node with same identifier
            existing_node = await self._get_node_by_identifier(
                node_data.node_type,
                node_data.identifier,
                node_data.schema_name
            )
            
            if existing_node:
                # Update existing node instead of creating duplicate
                return await self._update_existing_node(existing_node, node_data, created_by)
            
            node = DataLineageNode(
                id=uuid4(),
                node_type=node_data.node_type,
                identifier=node_data.identifier,
                name=node_data.name,
                description=node_data.description,
                schema_name=node_data.schema_name,
                table_name=node_data.table_name,
                column_name=node_data.column_name,
                data_type=node_data.data_type,
                is_sensitive=node_data.is_sensitive,
                classification_level=node_data.classification_level,
                business_context=node_data.business_context,
                technical_metadata=node_data.technical_metadata,
                compliance_tags=node_data.compliance_tags,
                created_by=created_by
            )
            
            self.db.add(node)
            await self.db.commit()
            await self.db.refresh(node)
            
            logger.info(
                f"Data lineage node created: {node.id}",
                extra={
                    "node_id": str(node.id),
                    "node_type": node_data.node_type,
                    "identifier": node_data.identifier,
                    "created_by": created_by
                }
            )
            
            return DataLineageNodeResponse.from_orm(node)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating lineage node: {e}")
            raise ValidationError(f"Failed to create lineage node: {str(e)}")

    async def get_node(self, node_id: str) -> DataLineageNodeResponse:
        """Get data lineage node by ID"""
        stmt = select(DataLineageNode).where(DataLineageNode.id == UUID(node_id))
        result = await self.db.execute(stmt)
        node = result.scalar_one_or_none()
        
        if not node:
            raise NotFoundError(f"Lineage node not found: {node_id}")
        
        return DataLineageNodeResponse.from_orm(node)

    async def update_node(
        self,
        node_id: str,
        update_data: DataLineageNodeUpdate
    ) -> DataLineageNodeResponse:
        """Update data lineage node"""
        stmt = select(DataLineageNode).where(DataLineageNode.id == UUID(node_id))
        result = await self.db.execute(stmt)
        node = result.scalar_one_or_none()
        
        if not node:
            raise NotFoundError(f"Lineage node not found: {node_id}")
        
        # Update fields
        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            if hasattr(node, field):
                setattr(node, field, value)
        
        node.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(node)
        
        return DataLineageNodeResponse.from_orm(node)

    async def list_nodes(
        self,
        node_type: Optional[NodeType] = None,
        schema_name: Optional[str] = None,
        is_sensitive: Optional[bool] = None,
        classification_level: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[DataLineageNodeResponse]:
        """List data lineage nodes with filtering"""
        stmt = select(DataLineageNode)
        
        # Apply filters
        if node_type:
            stmt = stmt.where(DataLineageNode.node_type == node_type)
        if schema_name:
            stmt = stmt.where(DataLineageNode.schema_name == schema_name)
        if is_sensitive is not None:
            stmt = stmt.where(DataLineageNode.is_sensitive == is_sensitive)
        if classification_level:
            stmt = stmt.where(DataLineageNode.classification_level == classification_level)
        
        stmt = stmt.offset(offset).limit(limit).order_by(DataLineageNode.created_at.desc())
        result = await self.db.execute(stmt)
        nodes = result.scalars().all()
        
        return [DataLineageNodeResponse.from_orm(node) for node in nodes]

    # Edge Management
    
    async def create_edge(
        self,
        edge_data: DataLineageEdgeCreate,
        created_by: str
    ) -> DataLineageEdgeResponse:
        """Create a data lineage edge (relationship)"""
        try:
            # Verify source and target nodes exist
            await self.get_node(edge_data.source_node_id)
            await self.get_node(edge_data.target_node_id)
            
            # Check for existing edge
            existing_edge = await self._get_existing_edge(
                edge_data.source_node_id,
                edge_data.target_node_id,
                edge_data.relationship_type
            )
            
            if existing_edge:
                # Update existing edge
                return await self._update_existing_edge(existing_edge, edge_data, created_by)
            
            edge = DataLineageEdge(
                id=uuid4(),
                source_node_id=UUID(edge_data.source_node_id),
                target_node_id=UUID(edge_data.target_node_id),
                relationship_type=edge_data.relationship_type,
                transformation_logic=edge_data.transformation_logic,
                confidence_score=edge_data.confidence_score,
                is_active=edge_data.is_active,
                metadata=edge_data.metadata,
                created_by=created_by
            )
            
            self.db.add(edge)
            await self.db.commit()
            await self.db.refresh(edge)
            
            logger.info(
                f"Data lineage edge created: {edge.id}",
                extra={
                    "edge_id": str(edge.id),
                    "source_node": edge_data.source_node_id,
                    "target_node": edge_data.target_node_id,
                    "relationship_type": edge_data.relationship_type,
                    "created_by": created_by
                }
            )
            
            return DataLineageEdgeResponse.from_orm(edge)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating lineage edge: {e}")
            raise ValidationError(f"Failed to create lineage edge: {str(e)}")

    # Transformation Tracking
    
    async def record_transformation(
        self,
        transformation_data: DataTransformationCreate,
        session_id: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> DataTransformationResponse:
        """Record a data transformation"""
        try:
            transformation = DataTransformation(
                id=uuid4(),
                session_id=UUID(session_id) if session_id else None,
                transformation_type=transformation_data.transformation_type,
                source_nodes=transformation_data.source_nodes,
                target_nodes=transformation_data.target_nodes,
                transformation_logic=transformation_data.transformation_logic,
                transformation_code=transformation_data.transformation_code,
                execution_context=transformation_data.execution_context,
                data_quality_metrics=transformation_data.data_quality_metrics,
                performance_metrics=transformation_data.performance_metrics,
                error_details=transformation_data.error_details,
                success=transformation_data.success,
                created_by=created_by
            )
            
            self.db.add(transformation)
            await self.db.commit()
            await self.db.refresh(transformation)
            
            # Auto-create edges if they don't exist
            await self._auto_create_edges_from_transformation(transformation)
            
            logger.info(
                f"Data transformation recorded: {transformation.id}",
                extra={
                    "transformation_id": str(transformation.id),
                    "transformation_type": transformation_data.transformation_type,
                    "success": transformation_data.success,
                    "session_id": session_id
                }
            )
            
            return DataTransformationResponse.from_orm(transformation)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error recording transformation: {e}")
            raise ValidationError(f"Failed to record transformation: {str(e)}")

    # Flow Session Management
    
    async def create_flow_session(
        self,
        session_data: DataFlowSessionCreate,
        created_by: str
    ) -> DataFlowSessionResponse:
        """Create a data flow session"""
        try:
            session = DataFlowSession(
                id=uuid4(),
                session_name=session_data.session_name,
                session_type=session_data.session_type,
                description=session_data.description,
                workflow_id=session_data.workflow_id,
                pipeline_id=session_data.pipeline_id,
                start_time=session_data.start_time or datetime.utcnow(),
                expected_end_time=session_data.expected_end_time,
                configuration=session_data.configuration,
                environment=session_data.environment,
                tags=session_data.tags,
                created_by=created_by
            )
            
            self.db.add(session)
            await self.db.commit()
            await self.db.refresh(session)
            
            return DataFlowSessionResponse.from_orm(session)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating flow session: {e}")
            raise ValidationError(f"Failed to create flow session: {str(e)}")

    async def end_flow_session(
        self,
        session_id: str,
        success: bool = True,
        summary: Optional[Dict[str, Any]] = None
    ) -> DataFlowSessionResponse:
        """End a data flow session"""
        stmt = select(DataFlowSession).where(DataFlowSession.id == UUID(session_id))
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if not session:
            raise NotFoundError(f"Flow session not found: {session_id}")
        
        session.end_time = datetime.utcnow()
        session.success = success
        if summary:
            session.summary = summary
        
        await self.db.commit()
        await self.db.refresh(session)
        
        return DataFlowSessionResponse.from_orm(session)

    # Lineage Querying
    
    async def get_lineage_graph(
        self,
        node_id: str,
        direction: LineageDirection = LineageDirection.BOTH,
        max_depth: int = 5,
        include_transformations: bool = True
    ) -> DataLineageGraphResponse:
        """Get data lineage graph for a node"""
        try:
            # Get starting node
            start_node = await self.get_node(node_id)
            
            # Traverse lineage
            nodes, edges, transformations = await self._traverse_lineage(
                node_id, direction, max_depth, include_transformations
            )
            
            # Calculate statistics
            stats = {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "total_transformations": len(transformations) if transformations else 0,
                "max_depth_reached": self._calculate_max_depth(nodes, edges, node_id),
                "sensitive_nodes": sum(1 for n in nodes if n.is_sensitive),
                "node_types": self._count_node_types(nodes)
            }
            
            return DataLineageGraphResponse(
                root_node=start_node,
                nodes=nodes,
                edges=edges,
                transformations=transformations or [],
                direction=direction,
                max_depth=max_depth,
                statistics=stats
            )
            
        except Exception as e:
            logger.error(f"Error getting lineage graph: {e}")
            raise ValidationError(f"Failed to get lineage graph: {str(e)}")

    async def get_upstream_lineage(
        self,
        node_id: str,
        max_depth: int = 5
    ) -> DataLineageGraphResponse:
        """Get upstream data lineage (sources)"""
        return await self.get_lineage_graph(
            node_id, 
            LineageDirection.UPSTREAM, 
            max_depth
        )

    async def get_downstream_lineage(
        self,
        node_id: str,
        max_depth: int = 5
    ) -> DataLineageGraphResponse:
        """Get downstream data lineage (targets)"""
        return await self.get_lineage_graph(
            node_id, 
            LineageDirection.DOWNSTREAM, 
            max_depth
        )

    # Impact Analysis
    
    async def analyze_impact(
        self,
        request: DataImpactAnalysisRequest
    ) -> DataImpactAnalysisResponse:
        """Analyze impact of changes to data nodes"""
        try:
            analysis = DataImpactAnalysis(
                id=uuid4(),
                node_ids=request.node_ids,
                change_type=request.change_type,
                change_description=request.change_description,
                analysis_scope=request.analysis_scope,
                max_depth=request.max_depth,
                include_sensitive_data=request.include_sensitive_data
            )
            
            # Perform impact analysis
            impacted_nodes = []
            impacted_transformations = []
            risk_assessment = {}
            
            for node_id in request.node_ids:
                # Get downstream lineage for impact
                lineage = await self.get_downstream_lineage(node_id, request.max_depth)
                
                for node in lineage.nodes:
                    if node.id != UUID(node_id):  # Exclude the source node
                        impact_info = {
                            "node_id": str(node.id),
                            "node_name": node.name,
                            "node_type": node.node_type,
                            "impact_level": self._calculate_impact_level(node, request),
                            "business_context": node.business_context,
                            "is_sensitive": node.is_sensitive,
                            "classification_level": node.classification_level
                        }
                        impacted_nodes.append(impact_info)
                
                # Get affected transformations
                if lineage.transformations:
                    for transformation in lineage.transformations:
                        if any(n in transformation.target_nodes for n in [node_id]):
                            impact_info = {
                                "transformation_id": str(transformation.id),
                                "transformation_type": transformation.transformation_type,
                                "impact_level": "high" if transformation.transformation_type in ["aggregation", "join"] else "medium"
                            }
                            impacted_transformations.append(impact_info)
            
            # Generate risk assessment
            risk_assessment = await self._generate_risk_assessment(
                request, impacted_nodes, impacted_transformations
            )
            
            # Store analysis results
            analysis.impacted_nodes = impacted_nodes
            analysis.impacted_transformations = impacted_transformations
            analysis.risk_assessment = risk_assessment
            analysis.recommendations = await self._generate_recommendations(
                request, impacted_nodes, risk_assessment
            )
            
            self.db.add(analysis)
            await self.db.commit()
            await self.db.refresh(analysis)
            
            return DataImpactAnalysisResponse.from_orm(analysis)
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error analyzing impact: {e}")
            raise ValidationError(f"Failed to analyze impact: {str(e)}")

    # Metrics and Analytics
    
    async def get_lineage_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> DataLineageMetricsResponse:
        """Get data lineage metrics"""
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Total nodes
        total_nodes_stmt = select(func.count(DataLineageNode.id))
        total_nodes_result = await self.db.execute(total_nodes_stmt)
        total_nodes = total_nodes_result.scalar() or 0
        
        # Total edges
        total_edges_stmt = select(func.count(DataLineageEdge.id))
        total_edges_result = await self.db.execute(total_edges_stmt)
        total_edges = total_edges_result.scalar() or 0
        
        # Nodes by type
        nodes_by_type_stmt = (
            select(
                DataLineageNode.node_type,
                func.count(DataLineageNode.id)
            )
            .group_by(DataLineageNode.node_type)
        )
        nodes_by_type_result = await self.db.execute(nodes_by_type_stmt)
        nodes_by_type = dict(nodes_by_type_result.all())
        
        # Sensitive nodes
        sensitive_nodes_stmt = (
            select(func.count(DataLineageNode.id))
            .where(DataLineageNode.is_sensitive == True)
        )
        sensitive_nodes_result = await self.db.execute(sensitive_nodes_stmt)
        sensitive_nodes = sensitive_nodes_result.scalar() or 0
        
        # Transformations
        transformations_stmt = (
            select(func.count(DataTransformation.id))
            .where(
                and_(
                    DataTransformation.created_at >= start_date,
                    DataTransformation.created_at <= end_date
                )
            )
        )
        transformations_result = await self.db.execute(transformations_stmt)
        transformations = transformations_result.scalar() or 0
        
        # Active sessions
        active_sessions_stmt = (
            select(func.count(DataFlowSession.id))
            .where(DataFlowSession.end_time.is_(None))
        )
        active_sessions_result = await self.db.execute(active_sessions_stmt)
        active_sessions = active_sessions_result.scalar() or 0
        
        return DataLineageMetricsResponse(
            total_nodes=total_nodes,
            total_edges=total_edges,
            nodes_by_type=nodes_by_type,
            sensitive_nodes=sensitive_nodes,
            total_transformations=transformations,
            active_sessions=active_sessions,
            period_start=start_date,
            period_end=end_date
        )

    # Helper Methods
    
    async def _get_node_by_identifier(
        self,
        node_type: NodeType,
        identifier: str,
        schema_name: Optional[str] = None
    ) -> Optional[DataLineageNode]:
        """Get node by type and identifier"""
        stmt = select(DataLineageNode).where(
            and_(
                DataLineageNode.node_type == node_type,
                DataLineageNode.identifier == identifier
            )
        )
        
        if schema_name:
            stmt = stmt.where(DataLineageNode.schema_name == schema_name)
        
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _update_existing_node(
        self,
        node: DataLineageNode,
        node_data: DataLineageNodeCreate,
        updated_by: str
    ) -> DataLineageNodeResponse:
        """Update existing node with new data"""
        node.name = node_data.name
        node.description = node_data.description or node.description
        node.data_type = node_data.data_type or node.data_type
        node.is_sensitive = node_data.is_sensitive
        node.classification_level = node_data.classification_level or node.classification_level
        node.business_context = node_data.business_context or node.business_context
        node.technical_metadata = {**(node.technical_metadata or {}), **(node_data.technical_metadata or {})}
        node.compliance_tags = list(set((node.compliance_tags or []) + (node_data.compliance_tags or [])))
        node.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(node)
        
        return DataLineageNodeResponse.from_orm(node)

    async def _get_existing_edge(
        self,
        source_node_id: str,
        target_node_id: str,
        relationship_type: str
    ) -> Optional[DataLineageEdge]:
        """Get existing edge between nodes"""
        stmt = select(DataLineageEdge).where(
            and_(
                DataLineageEdge.source_node_id == UUID(source_node_id),
                DataLineageEdge.target_node_id == UUID(target_node_id),
                DataLineageEdge.relationship_type == relationship_type
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _update_existing_edge(
        self,
        edge: DataLineageEdge,
        edge_data: DataLineageEdgeCreate,
        updated_by: str
    ) -> DataLineageEdgeResponse:
        """Update existing edge with new data"""
        edge.transformation_logic = edge_data.transformation_logic or edge.transformation_logic
        edge.confidence_score = edge_data.confidence_score
        edge.is_active = edge_data.is_active
        edge.metadata = {**(edge.metadata or {}), **(edge_data.metadata or {})}
        edge.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(edge)
        
        return DataLineageEdgeResponse.from_orm(edge)

    async def _auto_create_edges_from_transformation(
        self,
        transformation: DataTransformation
    ) -> None:
        """Automatically create edges based on transformation"""
        if not transformation.source_nodes or not transformation.target_nodes:
            return
        
        for source_id in transformation.source_nodes:
            for target_id in transformation.target_nodes:
                # Check if edge already exists
                existing_edge = await self._get_existing_edge(
                    source_id, target_id, "derived_from"
                )
                
                if not existing_edge:
                    edge = DataLineageEdge(
                        id=uuid4(),
                        source_node_id=UUID(source_id),
                        target_node_id=UUID(target_id),
                        relationship_type="derived_from",
                        transformation_logic=transformation.transformation_logic,
                        confidence_score=0.9,  # High confidence for recorded transformations
                        is_active=True,
                        metadata={
                            "transformation_id": str(transformation.id),
                            "auto_created": True
                        },
                        created_by="system"
                    )
                    self.db.add(edge)
        
        await self.db.commit()

    async def _traverse_lineage(
        self,
        node_id: str,
        direction: LineageDirection,
        max_depth: int,
        include_transformations: bool
    ) -> Tuple[List[DataLineageNodeResponse], List[DataLineageEdgeResponse], Optional[List[DataTransformationResponse]]]:
        """Traverse lineage graph using BFS"""
        visited_nodes = set()
        visited_edges = set()
        nodes = []
        edges = []
        transformations = [] if include_transformations else None
        
        queue = deque([(node_id, 0)])  # (node_id, depth)
        visited_nodes.add(node_id)
        
        while queue and len(queue) > 0:
            current_node_id, depth = queue.popleft()
            
            if depth > max_depth:
                continue
            
            # Add current node
            node = await self.get_node(current_node_id)
            nodes.append(node)
            
            # Get edges based on direction
            if direction in [LineageDirection.UPSTREAM, LineageDirection.BOTH]:
                upstream_edges = await self._get_upstream_edges(current_node_id)
                edges.extend(upstream_edges)
                
                for edge in upstream_edges:
                    edge_key = (str(edge.source_node_id), str(edge.target_node_id))
                    if edge_key not in visited_edges:
                        visited_edges.add(edge_key)
                        if str(edge.source_node_id) not in visited_nodes and depth < max_depth:
                            queue.append((str(edge.source_node_id), depth + 1))
                            visited_nodes.add(str(edge.source_node_id))
            
            if direction in [LineageDirection.DOWNSTREAM, LineageDirection.BOTH]:
                downstream_edges = await self._get_downstream_edges(current_node_id)
                edges.extend(downstream_edges)
                
                for edge in downstream_edges:
                    edge_key = (str(edge.source_node_id), str(edge.target_node_id))
                    if edge_key not in visited_edges:
                        visited_edges.add(edge_key)
                        if str(edge.target_node_id) not in visited_nodes and depth < max_depth:
                            queue.append((str(edge.target_node_id), depth + 1))
                            visited_nodes.add(str(edge.target_node_id))
        
        # Get transformations if requested
        if include_transformations:
            transformation_list = await self._get_transformations_for_nodes(
                [str(n.id) for n in nodes]
            )
            transformations.extend(transformation_list)
        
        return nodes, edges, transformations

    async def _get_upstream_edges(self, node_id: str) -> List[DataLineageEdgeResponse]:
        """Get edges where this node is the target"""
        stmt = (
            select(DataLineageEdge)
            .where(
                and_(
                    DataLineageEdge.target_node_id == UUID(node_id),
                    DataLineageEdge.is_active == True
                )
            )
        )
        result = await self.db.execute(stmt)
        edges = result.scalars().all()
        return [DataLineageEdgeResponse.from_orm(edge) for edge in edges]

    async def _get_downstream_edges(self, node_id: str) -> List[DataLineageEdgeResponse]:
        """Get edges where this node is the source"""
        stmt = (
            select(DataLineageEdge)
            .where(
                and_(
                    DataLineageEdge.source_node_id == UUID(node_id),
                    DataLineageEdge.is_active == True
                )
            )
        )
        result = await self.db.execute(stmt)
        edges = result.scalars().all()
        return [DataLineageEdgeResponse.from_orm(edge) for edge in edges]

    async def _get_transformations_for_nodes(
        self,
        node_ids: List[str]
    ) -> List[DataTransformationResponse]:
        """Get transformations involving specified nodes"""
        # This is a simplified version - in practice, you'd need more complex JSON queries
        stmt = select(DataTransformation)
        result = await self.db.execute(stmt)
        transformations = result.scalars().all()
        
        relevant_transformations = []
        for transformation in transformations:
            source_nodes = transformation.source_nodes or []
            target_nodes = transformation.target_nodes or []
            
            if any(node_id in source_nodes + target_nodes for node_id in node_ids):
                relevant_transformations.append(DataTransformationResponse.from_orm(transformation))
        
        return relevant_transformations

    def _calculate_max_depth(
        self,
        nodes: List[DataLineageNodeResponse],
        edges: List[DataLineageEdgeResponse],
        root_node_id: str
    ) -> int:
        """Calculate maximum depth reached in traversal"""
        # Simplified depth calculation
        return min(5, len(nodes) // 2)  # Placeholder

    def _count_node_types(self, nodes: List[DataLineageNodeResponse]) -> Dict[str, int]:
        """Count nodes by type"""
        type_counts = defaultdict(int)
        for node in nodes:
            type_counts[node.node_type] += 1
        return dict(type_counts)

    def _calculate_impact_level(
        self,
        node: DataLineageNodeResponse,
        request: DataImpactAnalysisRequest
    ) -> str:
        """Calculate impact level for a node"""
        if node.is_sensitive or node.classification_level in ["confidential", "restricted"]:
            return "high"
        elif node.node_type in ["table", "view"]:
            return "medium"
        else:
            return "low"

    async def _generate_risk_assessment(
        self,
        request: DataImpactAnalysisRequest,
        impacted_nodes: List[Dict[str, Any]],
        impacted_transformations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate risk assessment for impact analysis"""
        high_impact_nodes = sum(1 for n in impacted_nodes if n["impact_level"] == "high")
        sensitive_nodes = sum(1 for n in impacted_nodes if n["is_sensitive"])
        
        overall_risk = "low"
        if high_impact_nodes > 5 or sensitive_nodes > 2:
            overall_risk = "high"
        elif high_impact_nodes > 2 or sensitive_nodes > 0:
            overall_risk = "medium"
        
        return {
            "overall_risk": overall_risk,
            "high_impact_nodes": high_impact_nodes,
            "sensitive_nodes_affected": sensitive_nodes,
            "total_nodes_affected": len(impacted_nodes),
            "total_transformations_affected": len(impacted_transformations),
            "risk_factors": [
                "Sensitive data exposure" if sensitive_nodes > 0 else None,
                "High impact systems affected" if high_impact_nodes > 0 else None,
                "Complex transformation chains" if len(impacted_transformations) > 5 else None
            ]
        }

    async def _generate_recommendations(
        self,
        request: DataImpactAnalysisRequest,
        impacted_nodes: List[Dict[str, Any]],
        risk_assessment: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations for impact analysis"""
        recommendations = []
        
        if risk_assessment["overall_risk"] == "high":
            recommendations.append("Consider implementing change in a staged approach")
            recommendations.append("Perform thorough testing in non-production environment")
            recommendations.append("Notify stakeholders of downstream systems")
        
        if risk_assessment["sensitive_nodes_affected"] > 0:
            recommendations.append("Review data privacy implications")
            recommendations.append("Update data classification documentation")
            recommendations.append("Inform compliance team of potential impacts")
        
        if len(impacted_nodes) > 10:
            recommendations.append("Consider breaking change into smaller increments")
            recommendations.append("Implement monitoring for affected systems")
        
        return recommendations