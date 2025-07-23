"""
Plugin Registry for MAMS Plugin Architecture
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import json
from pathlib import Path

from .plugin_base import PluginType, PluginMetadata, PluginCapability
from ..core.logging import get_logger
from ..core.exceptions import PluginError

logger = get_logger(__name__)


class PluginRegistry:
    """Registry for plugin discovery and marketplace"""
    
    def __init__(self, registry_path: str = "/app/plugin_registry.json"):
        self.registry_path = Path(registry_path)
        self._registry: Dict[str, Dict[str, Any]] = {}
        self._load_registry()
    
    def _load_registry(self):
        """Load registry from file"""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r') as f:
                    self._registry = json.load(f)
                logger.info(
                    "Plugin registry loaded",
                    plugin_count=len(self._registry)
                )
            except Exception as e:
                logger.error("Failed to load plugin registry", error=str(e))
                self._registry = {}
        else:
            self._registry = {}
            self._save_registry()
    
    def _save_registry(self):
        """Save registry to file"""
        try:
            with open(self.registry_path, 'w') as f:
                json.dump(self._registry, f, indent=2, default=str)
        except Exception as e:
            logger.error("Failed to save plugin registry", error=str(e))
    
    def register_plugin(
        self,
        metadata: PluginMetadata,
        download_url: str,
        screenshots: List[str] = None,
        tags: List[str] = None,
        pricing: Dict[str, Any] = None,
        requirements: Dict[str, Any] = None
    ):
        """Register a plugin in the marketplace"""
        plugin_entry = {
            'metadata': {
                'id': metadata.id,
                'name': metadata.name,
                'version': metadata.version,
                'description': metadata.description,
                'author': metadata.author,
                'author_email': metadata.author_email,
                'homepage': metadata.homepage,
                'documentation_url': metadata.documentation_url,
                'icon_url': metadata.icon_url,
                'license': metadata.license,
                'min_mams_version': metadata.min_mams_version,
                'max_mams_version': metadata.max_mams_version
            },
            'download_url': download_url,
            'screenshots': screenshots or [],
            'tags': tags or [],
            'pricing': pricing or {'type': 'free'},
            'requirements': requirements or {},
            'registered_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'downloads': 0,
            'rating': 0.0,
            'reviews': []
        }
        
        self._registry[metadata.id] = plugin_entry
        self._save_registry()
        
        logger.info(
            "Plugin registered",
            plugin_id=metadata.id,
            plugin_name=metadata.name
        )
    
    def update_plugin(
        self,
        plugin_id: str,
        metadata: Optional[PluginMetadata] = None,
        download_url: Optional[str] = None,
        screenshots: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        pricing: Optional[Dict[str, Any]] = None,
        requirements: Optional[Dict[str, Any]] = None
    ):
        """Update plugin information in registry"""
        if plugin_id not in self._registry:
            raise PluginError(f"Plugin {plugin_id} not found in registry")
        
        entry = self._registry[plugin_id]
        
        if metadata:
            entry['metadata'].update({
                'name': metadata.name,
                'version': metadata.version,
                'description': metadata.description,
                'author': metadata.author,
                'author_email': metadata.author_email,
                'homepage': metadata.homepage,
                'documentation_url': metadata.documentation_url,
                'icon_url': metadata.icon_url,
                'license': metadata.license,
                'min_mams_version': metadata.min_mams_version,
                'max_mams_version': metadata.max_mams_version
            })
        
        if download_url is not None:
            entry['download_url'] = download_url
        
        if screenshots is not None:
            entry['screenshots'] = screenshots
        
        if tags is not None:
            entry['tags'] = tags
        
        if pricing is not None:
            entry['pricing'] = pricing
        
        if requirements is not None:
            entry['requirements'] = requirements
        
        entry['updated_at'] = datetime.utcnow().isoformat()
        
        self._save_registry()
        
        logger.info("Plugin updated in registry", plugin_id=plugin_id)
    
    def unregister_plugin(self, plugin_id: str):
        """Remove plugin from registry"""
        if plugin_id in self._registry:
            del self._registry[plugin_id]
            self._save_registry()
            logger.info("Plugin unregistered", plugin_id=plugin_id)
    
    def get_plugin(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Get plugin information from registry"""
        return self._registry.get(plugin_id)
    
    def search_plugins(
        self,
        query: Optional[str] = None,
        plugin_type: Optional[PluginType] = None,
        tags: Optional[List[str]] = None,
        author: Optional[str] = None,
        min_rating: Optional[float] = None,
        max_price: Optional[float] = None,
        capabilities: Optional[List[PluginCapability]] = None,
        sort_by: str = "downloads",
        ascending: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search plugins in registry"""
        results = []
        
        for plugin_id, entry in self._registry.items():
            # Text search
            if query:
                query_lower = query.lower()
                if not any(
                    query_lower in str(field).lower()
                    for field in [
                        entry['metadata']['name'],
                        entry['metadata']['description'],
                        entry['metadata']['author']
                    ]
                ):
                    continue
            
            # Filter by type
            if plugin_type:
                # TODO: Add plugin type to registry
                pass
            
            # Filter by tags
            if tags:
                if not any(tag in entry.get('tags', []) for tag in tags):
                    continue
            
            # Filter by author
            if author:
                if entry['metadata']['author'].lower() != author.lower():
                    continue
            
            # Filter by rating
            if min_rating is not None:
                if entry.get('rating', 0) < min_rating:
                    continue
            
            # Filter by price
            if max_price is not None:
                pricing = entry.get('pricing', {})
                if pricing.get('type') == 'paid':
                    price = pricing.get('price', 0)
                    if price > max_price:
                        continue
            
            # Filter by capabilities
            if capabilities:
                # TODO: Add capabilities to registry
                pass
            
            results.append(entry)
        
        # Sort results
        if sort_by == "downloads":
            results.sort(key=lambda x: x.get('downloads', 0), reverse=not ascending)
        elif sort_by == "rating":
            results.sort(key=lambda x: x.get('rating', 0), reverse=not ascending)
        elif sort_by == "name":
            results.sort(key=lambda x: x['metadata']['name'], reverse=ascending)
        elif sort_by == "updated":
            results.sort(key=lambda x: x.get('updated_at', ''), reverse=not ascending)
        
        # Apply pagination
        start = offset
        end = offset + limit
        
        return results[start:end]
    
    def get_popular_plugins(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular plugins"""
        return self.search_plugins(sort_by="downloads", limit=limit)
    
    def get_featured_plugins(self) -> List[Dict[str, Any]]:
        """Get featured plugins"""
        featured = []
        for plugin_id, entry in self._registry.items():
            if entry.get('featured', False):
                featured.append(entry)
        return featured
    
    def get_new_plugins(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get newest plugins"""
        return self.search_plugins(sort_by="updated", limit=limit)
    
    def increment_downloads(self, plugin_id: str):
        """Increment download counter for a plugin"""
        if plugin_id in self._registry:
            self._registry[plugin_id]['downloads'] += 1
            self._save_registry()
    
    def add_review(
        self,
        plugin_id: str,
        user_id: str,
        rating: float,
        comment: str
    ):
        """Add a review to a plugin"""
        if plugin_id not in self._registry:
            raise PluginError(f"Plugin {plugin_id} not found in registry")
        
        if not 0 <= rating <= 5:
            raise PluginError("Rating must be between 0 and 5")
        
        review = {
            'user_id': user_id,
            'rating': rating,
            'comment': comment,
            'created_at': datetime.utcnow().isoformat()
        }
        
        entry = self._registry[plugin_id]
        entry['reviews'].append(review)
        
        # Update average rating
        ratings = [r['rating'] for r in entry['reviews']]
        entry['rating'] = sum(ratings) / len(ratings) if ratings else 0.0
        
        self._save_registry()
        
        logger.info(
            "Review added",
            plugin_id=plugin_id,
            user_id=user_id,
            rating=rating
        )
    
    def get_plugin_stats(self) -> Dict[str, Any]:
        """Get overall plugin registry statistics"""
        total_plugins = len(self._registry)
        total_downloads = sum(entry.get('downloads', 0) for entry in self._registry.values())
        avg_rating = sum(entry.get('rating', 0) for entry in self._registry.values()) / total_plugins if total_plugins > 0 else 0
        
        # Count by pricing type
        free_plugins = sum(1 for entry in self._registry.values() if entry.get('pricing', {}).get('type') == 'free')
        paid_plugins = total_plugins - free_plugins
        
        # Count by tags
        tag_counts = {}
        for entry in self._registry.values():
            for tag in entry.get('tags', []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        return {
            'total_plugins': total_plugins,
            'total_downloads': total_downloads,
            'average_rating': avg_rating,
            'free_plugins': free_plugins,
            'paid_plugins': paid_plugins,
            'popular_tags': sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        }
    
    def export_registry(self) -> Dict[str, Any]:
        """Export the entire registry"""
        return self._registry.copy()
    
    def import_registry(self, registry_data: Dict[str, Any]):
        """Import registry data"""
        self._registry = registry_data
        self._save_registry()
        logger.info("Registry imported", plugin_count=len(self._registry))