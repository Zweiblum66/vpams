"""
Tests for Edge Manager
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import asyncio

from src.services.edge_manager import EdgeManager
from src.models.schemas import (
    EdgeNode, NodeStatus, NodeType, ProcessingTask,
    TaskStatus, TaskType, TaskPriority, LoadBalanceStrategy,
    NodeHeartbeat, AlertType
)


@pytest.fixture
async def edge_manager(mock_db, mock_redis):
    """Create edge manager instance"""
    manager = EdgeManager(db=mock_db, redis=mock_redis)
    # Don't start background tasks in tests
    manager._heartbeat_task = None
    manager._monitor_task = None
    manager._scheduler_task = None
    return manager


@pytest.fixture
def mock_nodes():
    """Create mock nodes"""
    return [
        EdgeNode(
            node_id="node-1",
            node_type=NodeType.STANDARD,
            location="us-west-2",
            status=NodeStatus.ONLINE,
            capabilities=["transcode", "thumbnail"],
            resources={"cpu_count": 4, "memory_total_gb": 16}
        ),
        EdgeNode(
            node_id="node-2",
            node_type=NodeType.GPU,
            location="us-west-2",
            status=NodeStatus.ONLINE,
            capabilities=["transcode", "thumbnail", "face_detection"],
            resources={"cpu_count": 8, "memory_total_gb": 32, "gpu_count": 1}
        ),
        EdgeNode(
            node_id="node-3",
            node_type=NodeType.STANDARD,
            location="eu-west-1",
            status=NodeStatus.OFFLINE,
            capabilities=["transcode"],
            resources={"cpu_count": 2, "memory_total_gb": 8}
        )
    ]


@pytest.fixture
def mock_tasks():
    """Create mock tasks"""
    return [
        ProcessingTask(
            task_id="task-1",
            task_type=TaskType.VIDEO_TRANSCODE,
            status=TaskStatus.PENDING,
            priority=TaskPriority.HIGH,
            asset_id="asset-1",
            parameters={"preset": "medium"}
        ),
        ProcessingTask(
            task_id="task-2",
            task_type=TaskType.FACE_DETECTION,
            status=TaskStatus.PENDING,
            priority=TaskPriority.NORMAL,
            asset_id="asset-2",
            parameters={"confidence": 0.8}
        ),
        ProcessingTask(
            task_id="task-3",
            task_type=TaskType.THUMBNAIL_GENERATION,
            status=TaskStatus.PENDING,
            priority=TaskPriority.LOW,
            asset_id="asset-3",
            parameters={"width": 320, "height": 180}
        )
    ]


class TestEdgeManager:
    """Test edge manager functionality"""
    
    @pytest.mark.asyncio
    async def test_initialize(self, edge_manager):
        """Test edge manager initialization"""
        with patch.object(edge_manager, '_register_node', new_callable=AsyncMock) as mock_register:
            with patch.object(edge_manager, '_load_nodes', new_callable=AsyncMock) as mock_load:
                await edge_manager.initialize()
                
                mock_register.assert_called_once()
                mock_load.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_register_node(self, edge_manager, mock_db):
        """Test node registration"""
        # Mock get_node_resources
        with patch.object(edge_manager, '_get_node_resources', new_callable=AsyncMock) as mock_resources:
            mock_resources.return_value = {
                "cpu_count": 4,
                "memory_total_gb": 16
            }
            
            await edge_manager._register_node()
            
            # Verify database operations
            assert mock_db.add.called
            assert mock_db.commit.called
    
    @pytest.mark.asyncio
    async def test_get_node_resources(self, edge_manager):
        """Test getting node resources"""
        with patch('psutil.cpu_count', return_value=4):
            with patch('psutil.cpu_freq') as mock_freq:
                mock_freq.return_value.current = 2400
                with patch('psutil.virtual_memory') as mock_mem:
                    mock_mem.return_value.total = 16 * 1024**3
                    mock_mem.return_value.available = 8 * 1024**3
                    with patch('psutil.disk_usage') as mock_disk:
                        mock_disk.return_value.total = 500 * 1024**3
                        mock_disk.return_value.free = 200 * 1024**3
                        
                        resources = await edge_manager._get_node_resources()
                        
                        assert resources["cpu_count"] == 4
                        assert resources["memory_total_gb"] == 16
                        assert resources["disk_total_gb"] == 500
    
    @pytest.mark.asyncio
    async def test_task_distribution_round_robin(self, edge_manager, mock_nodes, mock_tasks):
        """Test round-robin task distribution"""
        # Only use online nodes
        online_nodes = [n for n in mock_nodes if n.status == NodeStatus.ONLINE]
        
        distribution = await edge_manager._create_task_distribution(
            mock_tasks,
            online_nodes,
            LoadBalanceStrategy.ROUND_ROBIN
        )
        
        # Check tasks are distributed evenly
        assert len(distribution.task_assignments) == 2  # 2 online nodes
        assert distribution.task_assignments["node-1"] == ["task-1", "task-3"]
        assert distribution.task_assignments["node-2"] == ["task-2"]
    
    @pytest.mark.asyncio
    async def test_task_distribution_capability_based(self, edge_manager, mock_nodes, mock_tasks):
        """Test capability-based task distribution"""
        online_nodes = [n for n in mock_nodes if n.status == NodeStatus.ONLINE]
        
        distribution = await edge_manager._create_task_distribution(
            mock_tasks,
            online_nodes,
            LoadBalanceStrategy.CAPABILITY_BASED
        )
        
        # Face detection should go to GPU node
        assert "task-2" in distribution.task_assignments.get("node-2", [])
        
        # Other tasks can go to either node
        all_assigned = []
        for tasks in distribution.task_assignments.values():
            all_assigned.extend(tasks)
        assert set(all_assigned) == {"task-1", "task-2", "task-3"}
    
    @pytest.mark.asyncio
    async def test_assign_task_to_node(self, edge_manager, mock_db, mock_redis):
        """Test assigning task to node"""
        task_id = "test-task"
        node_id = "test-node"
        
        # Mock database execute
        mock_result = Mock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Mock node
        mock_node = EdgeNode(
            node_id=node_id,
            node_type=NodeType.STANDARD,
            location="us-west-2",
            status=NodeStatus.ONLINE,
            capabilities=["transcode"]
        )
        
        with patch.object(edge_manager, '_get_node', new_callable=AsyncMock) as mock_get_node:
            mock_get_node.return_value = mock_node
            
            await edge_manager._assign_task_to_node(task_id, node_id)
            
            # Verify database update
            assert mock_db.execute.called
            assert mock_db.commit.called
            
            # Verify Redis assignment
            mock_redis.setex.assert_called_with(
                f"edge:task:assignment:{task_id}",
                3600,
                node_id
            )
    
    @pytest.mark.asyncio
    async def test_monitor_nodes(self, edge_manager, mock_nodes, mock_redis):
        """Test node monitoring"""
        edge_manager.is_master = True
        
        # Mock _get_all_nodes
        with patch.object(edge_manager, '_get_all_nodes', new_callable=AsyncMock) as mock_get_nodes:
            mock_get_nodes.return_value = mock_nodes
            
            # Mock heartbeat data
            heartbeat = NodeHeartbeat(
                node_id="node-1",
                status=NodeStatus.ONLINE,
                cpu_usage=85.0,
                memory_usage=70.0,
                disk_usage=95.0,
                active_tasks=5,
                cache_size_gb=50.0
            )
            mock_redis.get = AsyncMock(return_value=heartbeat.json())
            
            # Mock other methods
            with patch.object(edge_manager, '_update_node_status', new_callable=AsyncMock):
                with patch.object(edge_manager, '_create_alert', new_callable=AsyncMock) as mock_alert:
                    with patch.object(edge_manager, '_update_cluster_metrics', new_callable=AsyncMock):
                        # Run one iteration
                        edge_manager._monitor_task = asyncio.create_task(edge_manager._monitor_nodes())
                        await asyncio.sleep(0.1)
                        edge_manager._monitor_task.cancel()
                        
                        # Should create high disk usage alert
                        mock_alert.assert_called()
                        alert_calls = mock_alert.call_args_list
                        assert any(
                            call[0][0] == AlertType.LOW_STORAGE
                            for call in alert_calls
                        )
    
    @pytest.mark.asyncio
    async def test_reassign_node_tasks(self, edge_manager, mock_db):
        """Test reassigning tasks from failed node"""
        failed_node_id = "failed-node"
        
        # Mock tasks assigned to failed node
        mock_tasks = [
            Mock(
                task_id="task-1",
                status=TaskStatus.PROCESSING,
                assigned_node=failed_node_id,
                retry_count=0
            ),
            Mock(
                task_id="task-2",
                status=TaskStatus.ASSIGNED,
                assigned_node=failed_node_id,
                retry_count=1
            )
        ]
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_tasks
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        await edge_manager._reassign_node_tasks(failed_node_id)
        
        # Verify tasks were reset
        for task in mock_tasks:
            assert task.status == TaskStatus.PENDING
            assert task.assigned_node is None
            assert task.retry_count == 2 or task.retry_count == 1
        
        assert mock_db.commit.called
    
    @pytest.mark.asyncio
    async def test_create_alert(self, edge_manager, mock_redis):
        """Test creating alerts"""
        await edge_manager._create_alert(
            AlertType.NODE_OFFLINE,
            "Node node-1 is offline",
            "node-1",
            "critical"
        )
        
        # Verify alert stored in Redis
        assert mock_redis.lpush.called
        assert mock_redis.ltrim.called
    
    @pytest.mark.asyncio
    async def test_get_cluster_status(self, edge_manager, mock_nodes):
        """Test getting cluster status"""
        with patch.object(edge_manager, '_get_all_nodes', new_callable=AsyncMock) as mock_get_nodes:
            mock_get_nodes.return_value = mock_nodes
            
            # Mock heartbeats
            edge_manager.node_health = {
                "node-1": NodeHeartbeat(
                    node_id="node-1",
                    status=NodeStatus.ONLINE,
                    cpu_usage=50.0,
                    memory_usage=60.0,
                    disk_usage=40.0,
                    active_tasks=2,
                    cache_size_gb=30.0
                ),
                "node-2": NodeHeartbeat(
                    node_id="node-2",
                    status=NodeStatus.ONLINE,
                    cpu_usage=30.0,
                    memory_usage=40.0,
                    disk_usage=50.0,
                    active_tasks=1,
                    cache_size_gb=40.0
                )
            }
            
            # Mock task queries
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = []
            edge_manager.db.execute = AsyncMock(return_value=mock_result)
            
            status = await edge_manager.get_cluster_status()
            
            assert status.total_nodes == 3
            assert status.online_nodes == 2
            assert status.total_capacity["cpu_cores"] == 12  # 4 + 8
            assert status.total_capacity["memory_gb"] == 48  # 16 + 32