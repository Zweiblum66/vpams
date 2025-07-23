"""
Permission Inheritance Service

Advanced permission inheritance system for roles and groups with
sophisticated inheritance patterns and conflict resolution.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any, Set, Tuple
from uuid import UUID
from datetime import datetime, timezone
import logging
from enum import Enum
from dataclasses import dataclass

from db.models import User, Role, Permission, Group
from services.rbac_service import RBACService
from services.group_service import GroupService

logger = logging.getLogger(__name__)


class InheritanceType(Enum):
    """Types of permission inheritance"""
    DIRECT = "direct"
    ROLE_HIERARCHY = "role_hierarchy"
    GROUP_HIERARCHY = "group_hierarchy"
    GROUP_ROLE = "group_role"
    MIXED = "mixed"


class InheritancePolicy(Enum):
    """Permission inheritance policies"""
    ADDITIVE = "additive"  # All permissions are combined
    RESTRICTIVE = "restrictive"  # Only common permissions
    OVERRIDE = "override"  # Child overrides parent
    PRIORITY = "priority"  # Higher priority wins


@dataclass
class PermissionSource:
    """Information about where a permission comes from"""
    permission_name: str
    source_type: InheritanceType
    source_id: UUID
    source_name: str
    priority: int
    granted_at: Optional[datetime] = None
    granted_by: Optional[UUID] = None


@dataclass
class InheritanceRule:
    """Rule for permission inheritance"""
    source_type: InheritanceType
    target_type: InheritanceType
    policy: InheritancePolicy
    priority: int
    conditions: Dict[str, Any]


class InheritanceService:
    """Service for managing permission inheritance"""
    
    def __init__(self):
        self.rbac_service = RBACService()
        self.group_service = GroupService()
        
        # Default inheritance rules
        self.default_rules = [
            InheritanceRule(
                source_type=InheritanceType.ROLE_HIERARCHY,
                target_type=InheritanceType.DIRECT,
                policy=InheritancePolicy.ADDITIVE,
                priority=1,
                conditions={}
            ),
            InheritanceRule(
                source_type=InheritanceType.GROUP_HIERARCHY,
                target_type=InheritanceType.DIRECT,
                policy=InheritancePolicy.ADDITIVE,
                priority=2,
                conditions={}
            ),
            InheritanceRule(
                source_type=InheritanceType.GROUP_ROLE,
                target_type=InheritanceType.DIRECT,
                policy=InheritancePolicy.ADDITIVE,
                priority=3,
                conditions={}
            ),
        ]
    
    async def get_effective_permissions(
        self,
        db: AsyncSession,
        user_id: UUID,
        include_sources: bool = False
    ) -> Dict[str, Any]:
        """
        Get effective permissions for a user with detailed source information
        
        Args:
            db: Database session
            user_id: User ID
            include_sources: Include source information for each permission
            
        Returns:
            Dictionary containing permissions and their sources
        """
        try:
            # Get user with all relationships
            user_result = await db.execute(
                select(User)
                .options(
                    selectinload(User.roles).selectinload(Role.permissions),
                    selectinload(User.roles).selectinload(Role.parent_role),
                    selectinload(User.groups).selectinload(Group.permissions),
                    selectinload(User.groups).selectinload(Group.roles).selectinload(Role.permissions),
                    selectinload(User.groups).selectinload(Group.parent_group)
                )
                .where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                return {"permissions": [], "sources": []}
            
            # Collect all permission sources
            permission_sources = []
            
            # Direct role permissions
            await self._collect_direct_role_permissions(db, user, permission_sources)
            
            # Role hierarchy permissions
            await self._collect_role_hierarchy_permissions(db, user, permission_sources)
            
            # Group permissions
            await self._collect_group_permissions(db, user, permission_sources)
            
            # Group hierarchy permissions
            await self._collect_group_hierarchy_permissions(db, user, permission_sources)
            
            # Resolve conflicts and apply inheritance rules
            effective_permissions = self._resolve_permission_conflicts(permission_sources)
            
            result = {
                "permissions": list(effective_permissions.keys()),
                "total_count": len(effective_permissions)
            }
            
            if include_sources:
                result["sources"] = [
                    {
                        "permission_name": perm.permission_name,
                        "source_type": perm.source_type.value,
                        "source_id": str(perm.source_id),
                        "source_name": perm.source_name,
                        "priority": perm.priority,
                        "granted_at": perm.granted_at.isoformat() if perm.granted_at else None,
                        "granted_by": str(perm.granted_by) if perm.granted_by else None
                    }
                    for perm in effective_permissions.values()
                ]
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting effective permissions: {e}")
            return {"permissions": [], "sources": []}
    
    async def _collect_direct_role_permissions(
        self,
        db: AsyncSession,
        user: User,
        permission_sources: List[PermissionSource]
    ):
        """Collect permissions from direct role assignments"""
        for role in user.roles:
            if not role.is_active:
                continue
                
            for permission in role.permissions:
                if permission.is_active:
                    permission_sources.append(PermissionSource(
                        permission_name=permission.name,
                        source_type=InheritanceType.DIRECT,
                        source_id=role.id,
                        source_name=f"Role: {role.name}",
                        priority=10,  # High priority for direct assignments
                        granted_at=role.created_at
                    ))
    
    async def _collect_role_hierarchy_permissions(
        self,
        db: AsyncSession,
        user: User,
        permission_sources: List[PermissionSource]
    ):
        """Collect permissions from role hierarchy"""
        for role in user.roles:
            if not role.is_active or not role.parent_role_id:
                continue
                
            # Get parent role permissions recursively
            parent_permissions = await self._get_role_hierarchy_permissions(
                db, role.parent_role_id, visited=set()
            )
            
            for perm_name, parent_role in parent_permissions:
                permission_sources.append(PermissionSource(
                    permission_name=perm_name,
                    source_type=InheritanceType.ROLE_HIERARCHY,
                    source_id=parent_role.id,
                    source_name=f"Inherited from Role: {parent_role.name}",
                    priority=5,  # Lower priority for inherited permissions
                    granted_at=parent_role.created_at
                ))
    
    async def _collect_group_permissions(
        self,
        db: AsyncSession,
        user: User,
        permission_sources: List[PermissionSource]
    ):
        """Collect permissions from group memberships"""
        for group in user.groups:
            if not group.is_active:
                continue
                
            # Direct group permissions
            for permission in group.permissions:
                if permission.is_active:
                    permission_sources.append(PermissionSource(
                        permission_name=permission.name,
                        source_type=InheritanceType.DIRECT,
                        source_id=group.id,
                        source_name=f"Group: {group.name}",
                        priority=8,  # High priority for group permissions
                        granted_at=group.created_at
                    ))
            
            # Group role permissions
            for role in group.roles:
                if not role.is_active:
                    continue
                    
                for permission in role.permissions:
                    if permission.is_active:
                        permission_sources.append(PermissionSource(
                            permission_name=permission.name,
                            source_type=InheritanceType.GROUP_ROLE,
                            source_id=role.id,
                            source_name=f"Group Role: {group.name} -> {role.name}",
                            priority=7,  # Medium priority for group roles
                            granted_at=role.created_at
                        ))
    
    async def _collect_group_hierarchy_permissions(
        self,
        db: AsyncSession,
        user: User,
        permission_sources: List[PermissionSource]
    ):
        """Collect permissions from group hierarchy"""
        for group in user.groups:
            if not group.is_active or not group.parent_group_id:
                continue
                
            # Get parent group permissions recursively
            parent_permissions = await self._get_group_hierarchy_permissions(
                db, group.parent_group_id, visited=set()
            )
            
            for perm_name, parent_group in parent_permissions:
                permission_sources.append(PermissionSource(
                    permission_name=perm_name,
                    source_type=InheritanceType.GROUP_HIERARCHY,
                    source_id=parent_group.id,
                    source_name=f"Inherited from Group: {parent_group.name}",
                    priority=3,  # Lower priority for inherited group permissions
                    granted_at=parent_group.created_at
                ))
    
    async def _get_role_hierarchy_permissions(
        self,
        db: AsyncSession,
        role_id: UUID,
        visited: Set[UUID]
    ) -> List[Tuple[str, Role]]:
        """Get permissions from role hierarchy recursively"""
        if role_id in visited:
            return []  # Prevent infinite loops
        
        visited.add(role_id)
        
        try:
            role_result = await db.execute(
                select(Role)
                .options(
                    selectinload(Role.permissions),
                    selectinload(Role.parent_role)
                )
                .where(Role.id == role_id, Role.is_active == True)
            )
            role = role_result.scalar_one_or_none()
            
            if not role:
                return []
            
            permissions = []
            
            # Add direct permissions
            for permission in role.permissions:
                if permission.is_active:
                    permissions.append((permission.name, role))
            
            # Add parent permissions recursively
            if role.parent_role_id:
                parent_permissions = await self._get_role_hierarchy_permissions(
                    db, role.parent_role_id, visited
                )
                permissions.extend(parent_permissions)
            
            return permissions
            
        except Exception as e:
            logger.error(f"Error getting role hierarchy permissions: {e}")
            return []
    
    async def _get_group_hierarchy_permissions(
        self,
        db: AsyncSession,
        group_id: UUID,
        visited: Set[UUID]
    ) -> List[Tuple[str, Group]]:
        """Get permissions from group hierarchy recursively"""
        if group_id in visited:
            return []  # Prevent infinite loops
        
        visited.add(group_id)
        
        try:
            group_result = await db.execute(
                select(Group)
                .options(
                    selectinload(Group.permissions),
                    selectinload(Group.roles).selectinload(Role.permissions),
                    selectinload(Group.parent_group)
                )
                .where(Group.id == group_id, Group.is_active == True)
            )
            group = group_result.scalar_one_or_none()
            
            if not group:
                return []
            
            permissions = []
            
            # Add direct group permissions
            for permission in group.permissions:
                if permission.is_active:
                    permissions.append((permission.name, group))
            
            # Add group role permissions
            for role in group.roles:
                if role.is_active:
                    for permission in role.permissions:
                        if permission.is_active:
                            permissions.append((permission.name, group))
            
            # Add parent group permissions recursively
            if group.parent_group_id:
                parent_permissions = await self._get_group_hierarchy_permissions(
                    db, group.parent_group_id, visited
                )
                permissions.extend(parent_permissions)
            
            return permissions
            
        except Exception as e:
            logger.error(f"Error getting group hierarchy permissions: {e}")
            return []
    
    def _resolve_permission_conflicts(
        self,
        permission_sources: List[PermissionSource]
    ) -> Dict[str, PermissionSource]:
        """Resolve conflicts between permission sources"""
        # Group by permission name
        permission_map = {}
        for source in permission_sources:
            perm_name = source.permission_name
            if perm_name not in permission_map:
                permission_map[perm_name] = []
            permission_map[perm_name].append(source)
        
        # Resolve conflicts for each permission
        resolved_permissions = {}
        for perm_name, sources in permission_map.items():
            # Sort by priority (higher priority first)
            sources.sort(key=lambda x: x.priority, reverse=True)
            
            # Take the highest priority source
            resolved_permissions[perm_name] = sources[0]
        
        return resolved_permissions
    
    async def get_permission_inheritance_tree(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> Dict[str, Any]:
        """Get the full inheritance tree for a user"""
        try:
            user_result = await db.execute(
                select(User)
                .options(
                    selectinload(User.roles).selectinload(Role.parent_role),
                    selectinload(User.groups).selectinload(Group.parent_group)
                )
                .where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                return {"tree": {}}
            
            tree = {
                "user_id": str(user_id),
                "roles": [],
                "groups": []
            }
            
            # Build role hierarchy tree
            for role in user.roles:
                if role.is_active:
                    role_tree = await self._build_role_tree(db, role.id, visited=set())
                    tree["roles"].append(role_tree)
            
            # Build group hierarchy tree
            for group in user.groups:
                if group.is_active:
                    group_tree = await self._build_group_tree(db, group.id, visited=set())
                    tree["groups"].append(group_tree)
            
            return {"tree": tree}
            
        except Exception as e:
            logger.error(f"Error getting inheritance tree: {e}")
            return {"tree": {}}
    
    async def _build_role_tree(
        self,
        db: AsyncSession,
        role_id: UUID,
        visited: Set[UUID]
    ) -> Dict[str, Any]:
        """Build role hierarchy tree recursively"""
        if role_id in visited:
            return {"circular_reference": True}
        
        visited.add(role_id)
        
        try:
            role_result = await db.execute(
                select(Role)
                .options(
                    selectinload(Role.permissions),
                    selectinload(Role.parent_role)
                )
                .where(Role.id == role_id)
            )
            role = role_result.scalar_one_or_none()
            
            if not role:
                return {"error": "Role not found"}
            
            tree = {
                "role_id": str(role.id),
                "name": role.name,
                "display_name": role.display_name,
                "permissions": [p.name for p in role.permissions if p.is_active],
                "parent": None
            }
            
            if role.parent_role_id:
                parent_tree = await self._build_role_tree(db, role.parent_role_id, visited)
                tree["parent"] = parent_tree
            
            return tree
            
        except Exception as e:
            logger.error(f"Error building role tree: {e}")
            return {"error": str(e)}
    
    async def _build_group_tree(
        self,
        db: AsyncSession,
        group_id: UUID,
        visited: Set[UUID]
    ) -> Dict[str, Any]:
        """Build group hierarchy tree recursively"""
        if group_id in visited:
            return {"circular_reference": True}
        
        visited.add(group_id)
        
        try:
            group_result = await db.execute(
                select(Group)
                .options(
                    selectinload(Group.permissions),
                    selectinload(Group.roles).selectinload(Role.permissions),
                    selectinload(Group.parent_group)
                )
                .where(Group.id == group_id)
            )
            group = group_result.scalar_one_or_none()
            
            if not group:
                return {"error": "Group not found"}
            
            tree = {
                "group_id": str(group.id),
                "name": group.name,
                "display_name": group.display_name,
                "permissions": [p.name for p in group.permissions if p.is_active],
                "roles": [
                    {
                        "role_id": str(role.id),
                        "name": role.name,
                        "permissions": [p.name for p in role.permissions if p.is_active]
                    }
                    for role in group.roles if role.is_active
                ],
                "parent": None
            }
            
            if group.parent_group_id:
                parent_tree = await self._build_group_tree(db, group.parent_group_id, visited)
                tree["parent"] = parent_tree
            
            return tree
            
        except Exception as e:
            logger.error(f"Error building group tree: {e}")
            return {"error": str(e)}
    
    async def check_permission_conflicts(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> Dict[str, Any]:
        """Check for permission conflicts in user's assignments"""
        try:
            effective_permissions = await self.get_effective_permissions(
                db, user_id, include_sources=True
            )
            
            # Group sources by permission
            permission_sources = {}
            for source in effective_permissions.get("sources", []):
                perm_name = source["permission_name"]
                if perm_name not in permission_sources:
                    permission_sources[perm_name] = []
                permission_sources[perm_name].append(source)
            
            # Find conflicts (permissions from multiple sources)
            conflicts = {}
            for perm_name, sources in permission_sources.items():
                if len(sources) > 1:
                    conflicts[perm_name] = {
                        "sources": sources,
                        "resolution": "highest_priority",
                        "chosen_source": sources[0]  # Highest priority
                    }
            
            return {
                "total_permissions": len(permission_sources),
                "conflicted_permissions": len(conflicts),
                "conflicts": conflicts
            }
            
        except Exception as e:
            logger.error(f"Error checking permission conflicts: {e}")
            return {"total_permissions": 0, "conflicted_permissions": 0, "conflicts": {}}
    
    async def get_inheritance_statistics(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> Dict[str, Any]:
        """Get statistics about permission inheritance for a user"""
        try:
            effective_permissions = await self.get_effective_permissions(
                db, user_id, include_sources=True
            )
            
            # Count permissions by source type
            source_counts = {}
            for source in effective_permissions.get("sources", []):
                source_type = source["source_type"]
                source_counts[source_type] = source_counts.get(source_type, 0) + 1
            
            # Get inheritance tree depth
            tree = await self.get_permission_inheritance_tree(db, user_id)
            max_role_depth = self._calculate_max_depth(tree.get("tree", {}).get("roles", []))
            max_group_depth = self._calculate_max_depth(tree.get("tree", {}).get("groups", []))
            
            return {
                "total_permissions": effective_permissions["total_count"],
                "source_breakdown": source_counts,
                "max_role_inheritance_depth": max_role_depth,
                "max_group_inheritance_depth": max_group_depth,
                "inheritance_complexity": max_role_depth + max_group_depth
            }
            
        except Exception as e:
            logger.error(f"Error getting inheritance statistics: {e}")
            return {}
    
    def _calculate_max_depth(self, items: List[Dict[str, Any]]) -> int:
        """Calculate maximum depth in hierarchy"""
        if not items:
            return 0
        
        max_depth = 0
        for item in items:
            depth = 1
            current = item
            while current.get("parent"):
                depth += 1
                current = current["parent"]
                if depth > 100:  # Prevent infinite loops
                    break
            max_depth = max(max_depth, depth)
        
        return max_depth
    
    async def optimize_user_permissions(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> Dict[str, Any]:
        """Suggest optimizations for user permission assignments"""
        try:
            effective_permissions = await self.get_effective_permissions(
                db, user_id, include_sources=True
            )
            
            conflicts = await self.check_permission_conflicts(db, user_id)
            
            # Find redundant assignments
            redundant = []
            permission_sources = {}
            
            for source in effective_permissions.get("sources", []):
                perm_name = source["permission_name"]
                if perm_name not in permission_sources:
                    permission_sources[perm_name] = []
                permission_sources[perm_name].append(source)
            
            for perm_name, sources in permission_sources.items():
                if len(sources) > 1:
                    # Sort by priority
                    sources.sort(key=lambda x: x["priority"], reverse=True)
                    # Mark lower priority sources as redundant
                    for source in sources[1:]:
                        redundant.append({
                            "permission": perm_name,
                            "redundant_source": source,
                            "reason": "Lower priority than existing assignment"
                        })
            
            recommendations = []
            
            # Recommend consolidation
            if len(redundant) > 0:
                recommendations.append({
                    "type": "consolidation",
                    "description": f"Remove {len(redundant)} redundant permission assignments",
                    "details": redundant
                })
            
            # Recommend role/group optimization
            direct_count = len([s for s in effective_permissions.get("sources", []) 
                              if s["source_type"] == "direct"])
            
            if direct_count > 10:
                recommendations.append({
                    "type": "grouping",
                    "description": f"Consider creating groups for {direct_count} direct assignments",
                    "details": {"direct_assignments": direct_count}
                })
            
            return {
                "total_permissions": effective_permissions["total_count"],
                "redundant_assignments": len(redundant),
                "conflicts": conflicts["conflicted_permissions"],
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"Error optimizing user permissions: {e}")
            return {}