"""
Audio Metadata Extractor

This module provides functionality for extracting metadata from audio files,
including ID3 tags, Vorbis comments, and other audio-specific metadata.
"""

import os
import json
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import structlog

from ..core.exceptions import ExtractionError

logger = structlog.get_logger()


class AudioExtractor:
    """Extracts metadata from audio files using multiple methods"""
    
    def __init__(self):
        self.supported_formats = {
            'MP3', 'FLAC', 'OGG', 'M4A', 'AAC', 'WAV', 'AIFF', 'WMA', 'AC3',
            'DTS', 'OPUS', 'AMR', 'APE', 'WV', 'TTA', 'MPC', 'DSF', 'DFF'
        }
        
        # Common audio metadata field mappings
        self.metadata_mapping = {
            'title': 'title',
            'artist': 'artist',
            'album': 'album',
            'albumartist': 'album_artist',
            'composer': 'composer',
            'genre': 'genre',
            'date': 'date',
            'year': 'year',
            'track': 'track_number',
            'tracktotal': 'total_tracks',
            'disc': 'disc_number',
            'disctotal': 'total_discs',
            'comment': 'comment',
            'lyrics': 'lyrics',
            'bpm': 'tempo',
            'key': 'musical_key',
            'isrc': 'isrc',
            'copyright': 'copyright',
            'publisher': 'publisher',
            'label': 'record_label',
            'barcode': 'barcode',
            'catalog': 'catalog_number',
            'grouping': 'grouping',
            'mood': 'mood',
            'style': 'style',
            'language': 'language',
            'country': 'country',
            'rating': 'rating',
            'playcount': 'play_count',
            'encoder': 'encoded_by',
            'encodedby': 'encoded_by',
            'originaldate': 'original_date',
            'originalyear': 'original_year',
            'originalartist': 'original_artist',
            'remixer': 'remixer',
            'conductor': 'conductor',
            'lyricist': 'lyricist',
            'arranger': 'arranger',
            'producer': 'producer',
            'engineer': 'engineer',
            'mixer': 'mixer',
            'mastered': 'mastered_by',
            'performer': 'performer',
            'soloist': 'soloist',
            'ensemble': 'ensemble',
            'part': 'part',
            'partnumber': 'part_number',
            'version': 'version',
            'subtitle': 'subtitle',
            'description': 'description',
            'longdescription': 'long_description',
            'url': 'url',
            'contact': 'contact',
            'license': 'license'
        }
    
    def is_supported_format(self, file_path: str) -> bool:
        """Check if file format is supported for audio extraction"""
        extension = Path(file_path).suffix.upper().lstrip('.')
        return extension in self.supported_formats
    
    async def extract_audio_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract audio metadata from file using multiple methods
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Dictionary containing extracted audio metadata
        """
        try:
            if not os.path.exists(file_path):
                raise ExtractionError(f"File not found: {file_path}")
            
            if not self.is_supported_format(file_path):
                extension = Path(file_path).suffix
                raise ExtractionError(f"Unsupported file format: {extension}")
            
            # Run extraction in thread pool to avoid blocking
            metadata = await asyncio.get_event_loop().run_in_executor(
                None, self._extract_metadata_sync, file_path
            )
            
            logger.info(
                "audio_extraction_completed",
                file_path=file_path,
                has_tags=bool(metadata.get('tags', {})),
                duration=metadata.get('technical_info', {}).get('duration')
            )
            
            return metadata
            
        except Exception as e:
            logger.error(
                "audio_extraction_failed",
                file_path=file_path,
                error=str(e)
            )
            raise ExtractionError(f"Failed to extract audio metadata: {str(e)}")
    
    def _extract_metadata_sync(self, file_path: str) -> Dict[str, Any]:
        """Synchronous audio metadata extraction using multiple methods"""
        try:
            # Initialize result structure
            result = {
                'file_info': {
                    'file_path': file_path,
                    'file_size': os.path.getsize(file_path),
                    'file_name': Path(file_path).name,
                    'file_extension': Path(file_path).suffix.lower(),
                    'extracted_at': datetime.utcnow().isoformat(),
                    'extraction_method': 'multi_method',
                    'extraction_tool': 'audio_extractor'
                },
                'raw_metadata': {},
                'processed_metadata': {},
                'technical_info': {},
                'tags': {},
                'format_info': {},
                'stream_info': {},
                'extraction_errors': []
            }
            
            # Try different extraction methods
            methods = [
                ('mutagen', self._extract_with_mutagen),
                ('tinytag', self._extract_with_tinytag),
                ('eyed3', self._extract_with_eyed3),
                ('taglib', self._extract_with_taglib)
            ]
            
            for method_name, method_func in methods:
                try:
                    method_result = method_func(file_path)
                    if method_result:
                        result['raw_metadata'][method_name] = method_result
                        logger.debug(f"audio_extraction_method_success", method=method_name)
                except Exception as e:
                    error_msg = f"{method_name} extraction failed: {str(e)}"
                    result['extraction_errors'].append(error_msg)
                    logger.warning(f"audio_extraction_method_failed", method=method_name, error=str(e))
            
            # Process and consolidate metadata
            result['processed_metadata'] = self._process_metadata(result['raw_metadata'])
            result['technical_info'] = self._extract_technical_info(result['raw_metadata'])
            result['tags'] = self._extract_tags(result['raw_metadata'])
            result['format_info'] = self._extract_format_info(result['raw_metadata'])
            result['stream_info'] = self._extract_stream_info(result['raw_metadata'])
            
            return result
            
        except Exception as e:
            logger.error("audio_sync_extraction_failed", error=str(e))
            raise ExtractionError(f"Audio metadata extraction failed: {str(e)}")
    
    def _extract_with_mutagen(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract metadata using mutagen library"""
        try:
            from mutagen import File
            from mutagen.id3 import ID3NoHeaderError
            
            audio_file = File(file_path)
            if not audio_file:
                return None
            
            result = {
                'format': audio_file.mime[0] if audio_file.mime else 'unknown',
                'length': audio_file.info.length if audio_file.info else 0,
                'bitrate': getattr(audio_file.info, 'bitrate', 0),
                'channels': getattr(audio_file.info, 'channels', 0),
                'sample_rate': getattr(audio_file.info, 'sample_rate', 0),
                'tags': {}
            }
            
            # Extract tags
            if audio_file.tags:
                for key, value in audio_file.tags.items():
                    if isinstance(value, list):
                        result['tags'][key] = [str(v) for v in value]
                    else:
                        result['tags'][key] = str(value)
            
            return result
            
        except ImportError:
            logger.warning("mutagen library not available")
            return None
        except Exception as e:
            logger.warning(f"mutagen extraction failed: {str(e)}")
            return None
    
    def _extract_with_tinytag(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract metadata using tinytag library"""
        try:
            from tinytag import TinyTag
            
            tag = TinyTag.get(file_path)
            if not tag:
                return None
            
            result = {
                'format': tag.filesize,
                'length': tag.duration or 0,
                'bitrate': tag.bitrate or 0,
                'channels': tag.channels or 0,
                'sample_rate': tag.samplerate or 0,
                'tags': {}
            }
            
            # Extract common tags
            tag_fields = [
                'title', 'artist', 'album', 'albumartist', 'composer',
                'genre', 'year', 'track', 'track_total', 'disc', 'disc_total',
                'comment', 'extra'
            ]
            
            for field in tag_fields:
                value = getattr(tag, field, None)
                if value is not None:
                    result['tags'][field] = str(value)
            
            return result
            
        except ImportError:
            logger.warning("tinytag library not available")
            return None
        except Exception as e:
            logger.warning(f"tinytag extraction failed: {str(e)}")
            return None
    
    def _extract_with_eyed3(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract metadata using eyed3 library (MP3 ID3 tags)"""
        try:
            import eyed3
            
            if not file_path.lower().endswith('.mp3'):
                return None
            
            audio_file = eyed3.load(file_path)
            if not audio_file:
                return None
            
            result = {
                'format': 'audio/mpeg',
                'length': audio_file.info.time_secs if audio_file.info else 0,
                'bitrate': audio_file.info.bit_rate[1] if audio_file.info and audio_file.info.bit_rate else 0,
                'channels': audio_file.info.mode if audio_file.info else 'unknown',
                'sample_rate': audio_file.info.sample_freq if audio_file.info else 0,
                'tags': {}
            }
            
            # Extract ID3 tags
            if audio_file.tag:
                tag_fields = {
                    'title': 'title',
                    'artist': 'artist',
                    'album': 'album',
                    'album_artist': 'album_artist',
                    'composer': 'composer',
                    'genre': 'genre',
                    'release_date': 'date',
                    'track_num': 'track',
                    'disc_num': 'disc',
                    'comments': 'comment'
                }
                
                for attr_name, tag_name in tag_fields.items():
                    value = getattr(audio_file.tag, attr_name, None)
                    if value is not None:
                        if hasattr(value, '__iter__') and not isinstance(value, str):
                            result['tags'][tag_name] = [str(v) for v in value]
                        else:
                            result['tags'][tag_name] = str(value)
            
            return result
            
        except ImportError:
            logger.warning("eyed3 library not available")
            return None
        except Exception as e:
            logger.warning(f"eyed3 extraction failed: {str(e)}")
            return None
    
    def _extract_with_taglib(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract metadata using taglib library"""
        try:
            import taglib
            
            audio_file = taglib.File(file_path)
            if not audio_file:
                return None
            
            result = {
                'format': 'unknown',
                'length': audio_file.length,
                'bitrate': audio_file.bitrate,
                'channels': audio_file.channels,
                'sample_rate': audio_file.sampleRate,
                'tags': dict(audio_file.tags) if audio_file.tags else {}
            }
            
            return result
            
        except ImportError:
            logger.warning("taglib library not available")
            return None
        except Exception as e:
            logger.warning(f"taglib extraction failed: {str(e)}")
            return None
    
    def _process_metadata(self, raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process and consolidate metadata from different sources"""
        processed = {}
        
        # Combine tags from all sources
        all_tags = {}
        for method_name, method_data in raw_metadata.items():
            if isinstance(method_data, dict) and 'tags' in method_data:
                all_tags.update(method_data['tags'])
        
        # Map to standardized field names
        for raw_key, raw_value in all_tags.items():
            # Normalize key
            normalized_key = raw_key.lower().replace(' ', '_').replace('-', '_')
            
            # Use mapping if available
            mapped_key = self.metadata_mapping.get(normalized_key, normalized_key)
            
            # Process value
            if isinstance(raw_value, list):
                processed[mapped_key] = [str(v) for v in raw_value if v]
            else:
                processed[mapped_key] = str(raw_value) if raw_value else None
        
        return processed
    
    def _extract_technical_info(self, raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract technical information from raw metadata"""
        technical_info = {}
        
        # Find the best source for technical info
        for method_name, method_data in raw_metadata.items():
            if isinstance(method_data, dict):
                # Duration
                if 'length' in method_data and method_data['length']:
                    technical_info['duration'] = float(method_data['length'])
                    technical_info['duration_formatted'] = self._format_duration(method_data['length'])
                
                # Bitrate
                if 'bitrate' in method_data and method_data['bitrate']:
                    technical_info['bitrate'] = int(method_data['bitrate'])
                    technical_info['bitrate_formatted'] = f"{method_data['bitrate']} kbps"
                
                # Channels
                if 'channels' in method_data and method_data['channels']:
                    technical_info['channels'] = method_data['channels']
                    technical_info['channel_layout'] = self._get_channel_layout(method_data['channels'])
                
                # Sample rate
                if 'sample_rate' in method_data and method_data['sample_rate']:
                    technical_info['sample_rate'] = int(method_data['sample_rate'])
                    technical_info['sample_rate_formatted'] = f"{method_data['sample_rate']} Hz"
        
        return technical_info
    
    def _extract_tags(self, raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and organize tags by category"""
        tags = {
            'basic': {},
            'extended': {},
            'technical': {},
            'custom': {}
        }
        
        # Basic tags
        basic_fields = [
            'title', 'artist', 'album', 'album_artist', 'composer',
            'genre', 'date', 'year', 'track_number', 'disc_number'
        ]
        
        # Extended tags
        extended_fields = [
            'comment', 'lyrics', 'copyright', 'publisher', 'record_label',
            'isrc', 'barcode', 'catalog_number', 'grouping', 'mood'
        ]
        
        # Technical tags
        technical_fields = [
            'encoded_by', 'encoder', 'encoding_settings', 'source',
            'ripper', 'ripping_date'
        ]
        
        # Process metadata from all sources
        all_processed = {}
        for method_name, method_data in raw_metadata.items():
            if isinstance(method_data, dict) and 'tags' in method_data:
                all_processed.update(method_data['tags'])
        
        processed_metadata = self._process_metadata(raw_metadata)
        
        # Categorize tags
        for field, value in processed_metadata.items():
            if field in basic_fields:
                tags['basic'][field] = value
            elif field in extended_fields:
                tags['extended'][field] = value
            elif field in technical_fields:
                tags['technical'][field] = value
            else:
                tags['custom'][field] = value
        
        return tags
    
    def _extract_format_info(self, raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract format-specific information"""
        format_info = {}
        
        for method_name, method_data in raw_metadata.items():
            if isinstance(method_data, dict) and 'format' in method_data:
                format_info['mime_type'] = method_data['format']
                break
        
        return format_info
    
    def _extract_stream_info(self, raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract stream information"""
        stream_info = {}
        
        # This would be expanded to include more detailed stream information
        # For now, basic audio stream info
        for method_name, method_data in raw_metadata.items():
            if isinstance(method_data, dict):
                if 'channels' in method_data:
                    stream_info['audio_channels'] = method_data['channels']
                if 'sample_rate' in method_data:
                    stream_info['sample_rate'] = method_data['sample_rate']
                if 'bitrate' in method_data:
                    stream_info['bitrate'] = method_data['bitrate']
        
        return stream_info
    
    def _format_duration(self, duration_seconds: float) -> str:
        """Format duration in seconds to MM:SS or HH:MM:SS"""
        try:
            total_seconds = int(duration_seconds)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            if hours > 0:
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                return f"{minutes:02d}:{seconds:02d}"
        except (ValueError, TypeError):
            return "00:00"
    
    def _get_channel_layout(self, channels: int) -> str:
        """Get channel layout description"""
        channel_layouts = {
            1: "mono",
            2: "stereo",
            3: "2.1",
            4: "4.0",
            5: "5.0",
            6: "5.1",
            7: "6.1",
            8: "7.1"
        }
        
        if isinstance(channels, int):
            return channel_layouts.get(channels, f"{channels} channels")
        else:
            return str(channels)
    
    async def extract_batch(self, file_paths: List[str]) -> Dict[str, Dict[str, Any]]:
        """Extract metadata from multiple audio files"""
        results = {}
        
        for file_path in file_paths:
            try:
                results[file_path] = await self.extract_audio_metadata(file_path)
            except Exception as e:
                logger.error(
                    "batch_audio_extraction_failed",
                    file_path=file_path,
                    error=str(e)
                )
                results[file_path] = {
                    'error': str(e),
                    'file_info': {
                        'extracted_at': datetime.utcnow().isoformat(),
                        'extraction_tool': 'audio_extractor',
                        'file_path': file_path,
                        'success': False
                    }
                }
        
        return results
    
    async def get_audio_summary(self, file_path: str) -> Dict[str, Any]:
        """Get a summary of audio file information"""
        try:
            metadata = await self.extract_audio_metadata(file_path)
            
            # Create summary
            summary = {
                'file_path': file_path,
                'file_name': metadata['file_info']['file_name'],
                'format': metadata['format_info'].get('mime_type', 'unknown'),
                'duration': metadata['technical_info'].get('duration_formatted', '00:00'),
                'bitrate': metadata['technical_info'].get('bitrate_formatted', 'unknown'),
                'sample_rate': metadata['technical_info'].get('sample_rate_formatted', 'unknown'),
                'channels': metadata['technical_info'].get('channel_layout', 'unknown'),
                'title': metadata['processed_metadata'].get('title', 'Unknown'),
                'artist': metadata['processed_metadata'].get('artist', 'Unknown'),
                'album': metadata['processed_metadata'].get('album', 'Unknown'),
                'genre': metadata['processed_metadata'].get('genre', 'Unknown'),
                'year': metadata['processed_metadata'].get('year', 'Unknown'),
                'has_tags': bool(metadata['processed_metadata']),
                'extraction_success': True
            }
            
            return summary
            
        except Exception as e:
            logger.error("audio_summary_failed", file_path=file_path, error=str(e))
            return {
                'file_path': file_path,
                'error': str(e),
                'extraction_success': False
            }