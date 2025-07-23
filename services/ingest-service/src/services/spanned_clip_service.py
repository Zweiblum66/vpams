"""
Spanned Clip Detection Service for handling multi-file clips
"""

import os
import re
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from datetime import datetime
import structlog

from ..models.schemas import SpannedClipInfo, FileMetadata
from ..core.exceptions import SpannedClipError
from ..core.logging import get_logger

logger = get_logger(__name__)


class SpannedClipService:
    """Service for detecting and managing spanned clips"""
    
    def __init__(self):
        # Common patterns for spanned clips
        self.span_patterns = [
            # Pattern: filename_001.ext, filename_002.ext, etc.
            r'^(.+)_(\d{3,4})\.(\w+)$',
            
            # Pattern: filenameA001.ext, filenameA002.ext, etc.
            r'^(.+)([A-Z])(\d{3,4})\.(\w+)$',
            
            # Pattern: filename-001.ext, filename-002.ext, etc.
            r'^(.+)-(\d{3,4})\.(\w+)$',
            
            # Pattern: filename(001).ext, filename(002).ext, etc.
            r'^(.+)\((\d{3,4})\)\.(\w+)$',
            
            # Pattern: filename.001.ext, filename.002.ext, etc.
            r'^(.+)\.(\d{3,4})\.(\w+)$',
            
            # Pattern: C0001A01.MXF, C0001A02.MXF (common in professional cameras)
            r'^([A-Z]\d{4})([A-Z])(\d{2})\.(\w+)$',
            
            # Pattern: CLIP001_01.ext, CLIP001_02.ext, etc.
            r'^([A-Z]+\d+)_(\d{2})\.(\w+)$'
        ]
        
        # Video file extensions that commonly span
        self.spannable_extensions = {
            '.MXF', '.MOV', '.MP4', '.AVI', '.MKV', '.R3D', '.BRAW'
        }
    
    async def detect_spanned_clips(
        self,
        file_paths: List[str]
    ) -> Dict[str, SpannedClipInfo]:
        """
        Detect spanned clips from a list of file paths
        
        Returns:
            Dict mapping base clip name to SpannedClipInfo
        """
        try:
            logger.info("detecting_spanned_clips", file_count=len(file_paths))
            
            # Group files by potential span patterns
            span_groups = self._group_files_by_pattern(file_paths)
            
            # Validate and create SpannedClipInfo objects
            spanned_clips = {}
            
            for base_name, files_info in span_groups.items():
                if len(files_info) > 1:  # Only consider groups with multiple files
                    span_info = await self._create_spanned_clip_info(base_name, files_info)
                    if span_info:
                        spanned_clips[base_name] = span_info
            
            logger.info(
                "spanned_clips_detected",
                total_clips=len(spanned_clips),
                total_files=len(file_paths)
            )
            
            return spanned_clips
            
        except Exception as e:
            logger.error("spanned_clip_detection_failed", error=str(e))
            raise SpannedClipError(f"Failed to detect spanned clips: {str(e)}")
    
    def _group_files_by_pattern(self, file_paths: List[str]) -> Dict[str, List[Dict]]:
        """Group files by matching span patterns"""
        groups = {}
        
        for file_path in file_paths:
            filename = Path(file_path).name
            extension = Path(file_path).suffix.upper()
            
            # Only process files with spannable extensions
            if extension not in self.spannable_extensions:
                continue
            
            # Try each pattern
            for pattern in self.span_patterns:
                match = re.match(pattern, filename, re.IGNORECASE)
                if match:
                    groups_data = match.groups()
                    
                    # Extract base name and span index based on pattern
                    if len(groups_data) == 3:  # Simple pattern: base_001.ext
                        base_name, span_str, ext = groups_data
                        span_index = int(span_str)
                        
                    elif len(groups_data) == 4:  # Complex patterns
                        if pattern == self.span_patterns[1]:  # baseA001.ext
                            base_name, letter, span_str, ext = groups_data
                            base_name = f"{base_name}{letter}"
                            span_index = int(span_str)
                        elif pattern == self.span_patterns[5]:  # C0001A01.ext
                            clip_id, letter, span_str, ext = groups_data
                            base_name = f"{clip_id}{letter}"
                            span_index = int(span_str)
                        else:
                            base_name, span_str, _, ext = groups_data
                            span_index = int(span_str)
                    
                    else:
                        continue
                    
                    # Create group key
                    group_key = f"{base_name}.{ext.lower()}"
                    
                    if group_key not in groups:
                        groups[group_key] = []
                    
                    groups[group_key].append({
                        'file_path': file_path,
                        'filename': filename,
                        'span_index': span_index,
                        'pattern': pattern
                    })
                    
                    break  # Stop trying patterns once we find a match
        
        # Sort files within each group by span index
        for group_key in groups:
            groups[group_key].sort(key=lambda x: x['span_index'])
        
        return groups
    
    async def _create_spanned_clip_info(
        self,
        base_name: str,
        files_info: List[Dict]
    ) -> Optional[SpannedClipInfo]:
        """Create SpannedClipInfo from grouped files"""
        try:
            # Validate span sequence
            span_indices = [f['span_index'] for f in files_info]
            expected_indices = list(range(min(span_indices), max(span_indices) + 1))
            
            # Check if we have a complete sequence
            is_complete = span_indices == expected_indices
            
            # Check if files exist and get basic info
            related_files = []
            total_size = 0
            earliest_creation = None
            
            for file_info in files_info:
                file_path = file_info['file_path']
                
                if os.path.exists(file_path):
                    related_files.append(file_path)
                    
                    # Get file stats
                    file_stat = os.stat(file_path)
                    total_size += file_stat.st_size
                    
                    file_creation = datetime.fromtimestamp(file_stat.st_ctime)
                    if earliest_creation is None or file_creation < earliest_creation:
                        earliest_creation = file_creation
                else:
                    logger.warning(
                        "spanned_file_missing",
                        file_path=file_path,
                        base_name=base_name
                    )
                    is_complete = False
            
            if not related_files:
                return None
            
            # Generate clip ID
            clip_id = self._generate_clip_id(base_name, files_info[0]['file_path'])
            
            span_info = SpannedClipInfo(
                clip_id=clip_id,
                span_index=1,  # This represents the first span
                total_spans=len(expected_indices),
                is_complete=is_complete,
                related_files=related_files
            )
            
            logger.debug(
                "spanned_clip_created",
                clip_id=clip_id,
                total_spans=span_info.total_spans,
                is_complete=is_complete,
                file_count=len(related_files)
            )
            
            return span_info
            
        except Exception as e:
            logger.error(
                "spanned_clip_creation_failed",
                error=str(e),
                base_name=base_name
            )
            return None
    
    def _generate_clip_id(self, base_name: str, sample_file_path: str) -> str:
        """Generate a unique clip ID for spanned clip"""
        # Remove extension from base name
        clean_base = base_name.split('.')[0]
        
        # Get directory hash for uniqueness
        dir_path = str(Path(sample_file_path).parent)
        dir_hash = abs(hash(dir_path)) % 10000
        
        return f"{clean_base}_{dir_hash:04d}"
    
    async def validate_spanned_clip(self, span_info: SpannedClipInfo) -> bool:
        """Validate that a spanned clip is complete and accessible"""
        try:
            if not span_info.related_files:
                return False
            
            # Check if all files exist
            for file_path in span_info.related_files:
                if not os.path.exists(file_path):
                    logger.warning(
                        "spanned_clip_file_missing",
                        clip_id=span_info.clip_id,
                        missing_file=file_path
                    )
                    return False
            
            # Check file sizes (basic validation)
            file_sizes = []
            for file_path in span_info.related_files:
                file_stat = os.stat(file_path)
                file_sizes.append(file_stat.st_size)
            
            # Files should be reasonably similar in size (except possibly the last one)
            if len(file_sizes) > 1:
                avg_size = sum(file_sizes[:-1]) / len(file_sizes[:-1])
                for i, size in enumerate(file_sizes[:-1]):  # Exclude last file
                    # Allow 50% variation in file sizes
                    if abs(size - avg_size) > avg_size * 0.5:
                        logger.warning(
                            "spanned_clip_size_variation",
                            clip_id=span_info.clip_id,
                            file_index=i,
                            file_size=size,
                            average_size=avg_size
                        )
            
            return True
            
        except Exception as e:
            logger.error(
                "spanned_clip_validation_failed",
                error=str(e),
                clip_id=span_info.clip_id
            )
            return False
    
    async def get_primary_file(self, span_info: SpannedClipInfo) -> Optional[str]:
        """Get the primary file path for a spanned clip (usually the first span)"""
        if not span_info.related_files:
            return None
        
        # Sort files to ensure we get the first span
        sorted_files = sorted(span_info.related_files)
        return sorted_files[0]
    
    async def calculate_total_duration(self, span_info: SpannedClipInfo) -> Optional[float]:
        """
        Calculate total duration of spanned clip
        Note: This would require ffprobe or similar tool in practice
        """
        # Placeholder implementation
        # In real implementation, would use ffprobe to get duration of each file
        # and sum them up
        logger.info(
            "duration_calculation_placeholder",
            clip_id=span_info.clip_id,
            total_files=len(span_info.related_files)
        )
        return None
    
    async def merge_spanned_metadata(
        self,
        span_info: SpannedClipInfo,
        file_metadata_list: List[FileMetadata]
    ) -> Dict[str, any]:
        """Merge metadata from all spans into a single metadata object"""
        try:
            merged_metadata = {
                "clip_id": span_info.clip_id,
                "total_spans": span_info.total_spans,
                "is_complete": span_info.is_complete,
                "span_files": span_info.related_files,
                "total_size": sum(fm.file_size for fm in file_metadata_list),
                "span_metadata": []
            }
            
            # Collect metadata from each span
            for i, file_metadata in enumerate(file_metadata_list):
                span_meta = {
                    "span_index": i + 1,
                    "filename": file_metadata.filename,
                    "file_size": file_metadata.file_size,
                    "created_at": file_metadata.created_at,
                    "modified_at": file_metadata.modified_at,
                    "checksums": file_metadata.checksums
                }
                merged_metadata["span_metadata"].append(span_meta)
            
            # Use metadata from first span as base
            if file_metadata_list:
                first_meta = file_metadata_list[0]
                merged_metadata.update({
                    "file_type": first_meta.file_type,
                    "mime_type": first_meta.mime_type,
                    "extension": first_meta.extension
                })
            
            return merged_metadata
            
        except Exception as e:
            logger.error(
                "spanned_metadata_merge_failed",
                error=str(e),
                clip_id=span_info.clip_id
            )
            return {}


# Dependency injection
_spanned_clip_service: Optional[SpannedClipService] = None


async def get_spanned_clip_service() -> SpannedClipService:
    """Get spanned clip service instance"""
    global _spanned_clip_service
    
    if _spanned_clip_service is None:
        _spanned_clip_service = SpannedClipService()
    
    return _spanned_clip_service