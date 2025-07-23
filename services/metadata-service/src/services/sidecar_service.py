"""
Sidecar File Service

This module provides functionality for reading and writing sidecar files (XML, JSON)
that contain metadata alongside media files.
"""

import os
import json
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from datetime import datetime
import structlog
import uuid
from xml.dom import minidom
import asyncio

from ..core.exceptions import ExtractionError, ValidationError

logger = structlog.get_logger()


class SidecarService:
    """Service for managing sidecar files containing metadata"""
    
    def __init__(self):
        self.supported_formats = {
            'JSON': '.json',
            'XML': '.xml',
            'XMP': '.xmp',
            'AVID': '.avid',
            'PREMIERE': '.pproj',
            'FCPXML': '.fcpxml'
        }
        
        # Common sidecar naming patterns
        self.naming_patterns = [
            '{basename}.{ext}',           # video.mp4 -> video.json
            '{basename}.metadata.{ext}',  # video.mp4 -> video.metadata.json
            '{basename}_metadata.{ext}',  # video.mp4 -> video_metadata.json
            '{basename}-metadata.{ext}',  # video.mp4 -> video-metadata.json
            '.{basename}.{ext}',          # video.mp4 -> .video.json (hidden)
            '{basename}.sidecar.{ext}',   # video.mp4 -> video.sidecar.json
        ]
        
        # XMP namespace definitions
        self.xmp_namespaces = {
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'xmp': 'http://ns.adobe.com/xap/1.0/',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'xmpMM': 'http://ns.adobe.com/xap/1.0/mm/',
            'xmpRights': 'http://ns.adobe.com/xap/1.0/rights/',
            'photoshop': 'http://ns.adobe.com/photoshop/1.0/',
            'tiff': 'http://ns.adobe.com/tiff/1.0/',
            'exif': 'http://ns.adobe.com/exif/1.0/',
            'aux': 'http://ns.adobe.com/exif/1.0/aux/',
            'crs': 'http://ns.adobe.com/camera-raw-settings/1.0/',
            'lr': 'http://ns.adobe.com/lightroom/1.0/'
        }
    
    def is_supported_format(self, file_extension: str) -> bool:
        """Check if file extension is supported for sidecar files"""
        return file_extension.lower() in self.supported_formats.values()
    
    async def find_sidecar_files(self, media_file_path: str) -> List[Dict[str, Any]]:
        """
        Find all sidecar files for a given media file
        
        Args:
            media_file_path: Path to the media file
            
        Returns:
            List of sidecar file information
        """
        try:
            media_path = Path(media_file_path)
            media_dir = media_path.parent
            media_basename = media_path.stem
            
            sidecar_files = []
            
            # Check for sidecar files using various naming patterns
            for pattern in self.naming_patterns:
                for format_name, ext in self.supported_formats.items():
                    sidecar_name = pattern.format(basename=media_basename, ext=ext.lstrip('.'))
                    sidecar_path = media_dir / sidecar_name
                    
                    if sidecar_path.exists():
                        sidecar_files.append({
                            'path': str(sidecar_path),
                            'format': format_name,
                            'pattern': pattern,
                            'size': sidecar_path.stat().st_size,
                            'modified': datetime.fromtimestamp(sidecar_path.stat().st_mtime).isoformat()
                        })
            
            logger.info(
                "sidecar_files_found",
                media_file=media_file_path,
                count=len(sidecar_files)
            )
            
            return sidecar_files
            
        except Exception as e:
            logger.error(
                "sidecar_search_failed",
                media_file=media_file_path,
                error=str(e)
            )
            return []
    
    async def read_sidecar_file(self, sidecar_path: str) -> Dict[str, Any]:
        """
        Read and parse a sidecar file
        
        Args:
            sidecar_path: Path to the sidecar file
            
        Returns:
            Parsed sidecar data
        """
        try:
            if not os.path.exists(sidecar_path):
                raise ExtractionError(f"Sidecar file not found: {sidecar_path}")
            
            file_extension = Path(sidecar_path).suffix.lower()
            
            # Run parsing in thread pool to avoid blocking
            metadata = await asyncio.get_event_loop().run_in_executor(
                None, self._parse_sidecar_sync, sidecar_path, file_extension
            )
            
            logger.info(
                "sidecar_read_completed",
                sidecar_path=sidecar_path,
                format=file_extension,
                metadata_fields=len(metadata.get('metadata', {}))
            )
            
            return metadata
            
        except Exception as e:
            logger.error(
                "sidecar_read_failed",
                sidecar_path=sidecar_path,
                error=str(e)
            )
            raise ExtractionError(f"Failed to read sidecar file: {str(e)}")
    
    def _parse_sidecar_sync(self, sidecar_path: str, file_extension: str) -> Dict[str, Any]:
        """Synchronous sidecar file parsing"""
        result = {
            'file_info': {
                'path': sidecar_path,
                'format': file_extension,
                'size': os.path.getsize(sidecar_path),
                'modified': datetime.fromtimestamp(os.path.getmtime(sidecar_path)).isoformat(),
                'parsed_at': datetime.utcnow().isoformat()
            },
            'metadata': {},
            'raw_data': None,
            'parsing_errors': []
        }
        
        try:
            if file_extension == '.json':
                result.update(self._parse_json_sidecar(sidecar_path))
            elif file_extension in ['.xml', '.xmp', '.fcpxml']:
                result.update(self._parse_xml_sidecar(sidecar_path))
            elif file_extension == '.avid':
                result.update(self._parse_avid_sidecar(sidecar_path))
            else:
                result['parsing_errors'].append(f"Unsupported sidecar format: {file_extension}")
            
            return result
            
        except Exception as e:
            result['parsing_errors'].append(str(e))
            return result
    
    def _parse_json_sidecar(self, sidecar_path: str) -> Dict[str, Any]:
        """Parse JSON sidecar file"""
        try:
            with open(sidecar_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            return {
                'metadata': data,
                'raw_data': data,
                'format_info': {
                    'type': 'json',
                    'version': data.get('version', '1.0'),
                    'schema': data.get('$schema', 'custom')
                }
            }
            
        except json.JSONDecodeError as e:
            raise ExtractionError(f"Invalid JSON in sidecar file: {str(e)}")
    
    def _parse_xml_sidecar(self, sidecar_path: str) -> Dict[str, Any]:
        """Parse XML sidecar file"""
        try:
            tree = ET.parse(sidecar_path)
            root = tree.getroot()
            
            # Detect XML type
            if root.tag == 'xmpmeta' or 'xmp' in root.tag.lower():
                return self._parse_xmp_metadata(root)
            elif 'fcpxml' in root.tag.lower():
                return self._parse_fcpxml_metadata(root)
            else:
                return self._parse_generic_xml_metadata(root)
                
        except ET.ParseError as e:
            raise ExtractionError(f"Invalid XML in sidecar file: {str(e)}")
    
    def _parse_xmp_metadata(self, root: ET.Element) -> Dict[str, Any]:
        """Parse XMP metadata"""
        metadata = {}
        
        # Register namespaces
        for prefix, uri in self.xmp_namespaces.items():
            ET.register_namespace(prefix, uri)
        
        # Extract RDF data
        rdf_elem = root.find('.//rdf:RDF', self.xmp_namespaces)
        if rdf_elem is not None:
            description = rdf_elem.find('.//rdf:Description', self.xmp_namespaces)
            if description is not None:
                # Extract attributes
                for attr_name, attr_value in description.attrib.items():
                    # Remove namespace prefix
                    clean_name = attr_name.split('}')[-1] if '}' in attr_name else attr_name
                    metadata[clean_name] = attr_value
                
                # Extract child elements
                for child in description:
                    tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    if child.text:
                        metadata[tag_name] = child.text
                    elif len(child) > 0:
                        # Handle complex elements (arrays, etc.)
                        metadata[tag_name] = self._parse_xml_complex_element(child)
        
        return {
            'metadata': metadata,
            'raw_data': ET.tostring(root, encoding='unicode'),
            'format_info': {
                'type': 'xmp',
                'namespaces': list(self.xmp_namespaces.keys())
            }
        }
    
    def _parse_fcpxml_metadata(self, root: ET.Element) -> Dict[str, Any]:
        """Parse Final Cut Pro XML metadata"""
        metadata = {
            'version': root.get('version', '1.0'),
            'events': [],
            'projects': [],
            'clips': []
        }
        
        # Extract events
        for event in root.findall('.//event'):
            event_data = {
                'name': event.get('name'),
                'uid': event.get('uid'),
                'projects': []
            }
            
            # Extract projects in event
            for project in event.findall('.//project'):
                project_data = {
                    'name': project.get('name'),
                    'uid': project.get('uid'),
                    'timecode': project.get('timecode'),
                    'sequences': []
                }
                event_data['projects'].append(project_data)
            
            metadata['events'].append(event_data)
        
        # Extract clips
        for clip in root.findall('.//clip'):
            clip_data = {
                'name': clip.get('name'),
                'duration': clip.get('duration'),
                'start': clip.get('start'),
                'tcFormat': clip.get('tcFormat'),
                'metadata': {}
            }
            
            # Extract clip metadata
            for meta in clip.findall('.//metadata'):
                for md in meta:
                    clip_data['metadata'][md.tag] = md.text
            
            metadata['clips'].append(clip_data)
        
        return {
            'metadata': metadata,
            'raw_data': ET.tostring(root, encoding='unicode'),
            'format_info': {
                'type': 'fcpxml',
                'version': root.get('version', '1.0')
            }
        }
    
    def _parse_generic_xml_metadata(self, root: ET.Element) -> Dict[str, Any]:
        """Parse generic XML metadata"""
        metadata = self._xml_to_dict(root)
        
        return {
            'metadata': metadata,
            'raw_data': ET.tostring(root, encoding='unicode'),
            'format_info': {
                'type': 'xml',
                'root_tag': root.tag,
                'attributes': root.attrib
            }
        }
    
    def _parse_avid_sidecar(self, sidecar_path: str) -> Dict[str, Any]:
        """Parse Avid sidecar file (simplified)"""
        # This is a placeholder - actual Avid sidecar parsing would be more complex
        try:
            with open(sidecar_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Try to parse as XML first
            try:
                root = ET.fromstring(content)
                return self._parse_generic_xml_metadata(root)
            except ET.ParseError:
                # Fall back to text parsing
                return {
                    'metadata': {'raw_content': content},
                    'raw_data': content,
                    'format_info': {
                        'type': 'avid',
                        'parsing_method': 'text'
                    }
                }
                
        except Exception as e:
            raise ExtractionError(f"Failed to parse Avid sidecar: {str(e)}")
    
    def _xml_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        """Convert XML element to dictionary"""
        result = {}
        
        # Add attributes
        if element.attrib:
            result['@attributes'] = element.attrib
        
        # Add text content
        if element.text and element.text.strip():
            if len(element) == 0:  # Leaf node
                return element.text.strip()
            else:
                result['#text'] = element.text.strip()
        
        # Add child elements
        for child in element:
            child_data = self._xml_to_dict(child)
            
            if child.tag in result:
                # Multiple elements with same tag - convert to list
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data
        
        return result
    
    def _parse_xml_complex_element(self, element: ET.Element) -> Any:
        """Parse complex XML elements (arrays, nested objects)"""
        # Handle RDF arrays
        if element.tag.endswith('Bag') or element.tag.endswith('Seq'):
            items = []
            for li in element.findall('.//rdf:li', self.xmp_namespaces):
                items.append(li.text if li.text else li.get('rdf:resource', ''))
            return items
        
        # Handle nested objects
        return self._xml_to_dict(element)
    
    async def write_sidecar_file(self, media_file_path: str, metadata: Dict[str, Any], 
                                format_type: str = 'json', 
                                naming_pattern: str = '{basename}.{ext}') -> str:
        """
        Write metadata to a sidecar file
        
        Args:
            media_file_path: Path to the media file
            metadata: Metadata to write
            format_type: Format type (json, xml, xmp)
            naming_pattern: Naming pattern for sidecar file
            
        Returns:
            Path to created sidecar file
        """
        try:
            media_path = Path(media_file_path)
            media_basename = media_path.stem
            
            # Determine file extension
            if format_type.lower() == 'json':
                ext = 'json'
            elif format_type.lower() == 'xml':
                ext = 'xml'
            elif format_type.lower() == 'xmp':
                ext = 'xmp'
            else:
                raise ValidationError(f"Unsupported format type: {format_type}")
            
            # Generate sidecar file path
            sidecar_name = naming_pattern.format(basename=media_basename, ext=ext)
            sidecar_path = media_path.parent / sidecar_name
            
            # Write sidecar file in thread pool
            await asyncio.get_event_loop().run_in_executor(
                None, self._write_sidecar_sync, str(sidecar_path), metadata, format_type
            )
            
            logger.info(
                "sidecar_write_completed",
                media_file=media_file_path,
                sidecar_path=str(sidecar_path),
                format=format_type
            )
            
            return str(sidecar_path)
            
        except Exception as e:
            logger.error(
                "sidecar_write_failed",
                media_file=media_file_path,
                format=format_type,
                error=str(e)
            )
            raise ExtractionError(f"Failed to write sidecar file: {str(e)}")
    
    def _write_sidecar_sync(self, sidecar_path: str, metadata: Dict[str, Any], format_type: str):
        """Synchronous sidecar file writing"""
        if format_type.lower() == 'json':
            self._write_json_sidecar(sidecar_path, metadata)
        elif format_type.lower() == 'xml':
            self._write_xml_sidecar(sidecar_path, metadata)
        elif format_type.lower() == 'xmp':
            self._write_xmp_sidecar(sidecar_path, metadata)
        else:
            raise ValidationError(f"Unsupported format type: {format_type}")
    
    def _write_json_sidecar(self, sidecar_path: str, metadata: Dict[str, Any]):
        """Write JSON sidecar file"""
        sidecar_data = {
            'version': '1.0',
            'created_at': datetime.utcnow().isoformat(),
            'created_by': 'MAMS Metadata Service',
            'metadata': metadata
        }
        
        with open(sidecar_path, 'w', encoding='utf-8') as file:
            json.dump(sidecar_data, file, indent=2, ensure_ascii=False)
    
    def _write_xml_sidecar(self, sidecar_path: str, metadata: Dict[str, Any]):
        """Write XML sidecar file"""
        root = ET.Element('metadata')
        root.set('version', '1.0')
        root.set('created_at', datetime.utcnow().isoformat())
        root.set('created_by', 'MAMS Metadata Service')
        
        # Convert metadata dict to XML elements
        self._dict_to_xml(metadata, root)
        
        # Pretty print XML
        xml_str = ET.tostring(root, encoding='unicode')
        pretty_xml = minidom.parseString(xml_str).toprettyxml(indent='  ')
        
        with open(sidecar_path, 'w', encoding='utf-8') as file:
            file.write(pretty_xml)
    
    def _write_xmp_sidecar(self, sidecar_path: str, metadata: Dict[str, Any]):
        """Write XMP sidecar file"""
        # Create XMP structure
        xmpmeta = ET.Element('x:xmpmeta')
        xmpmeta.set('xmlns:x', 'adobe:ns:meta/')
        
        rdf = ET.SubElement(xmpmeta, 'rdf:RDF')
        rdf.set('xmlns:rdf', self.xmp_namespaces['rdf'])
        
        # Add namespace declarations
        for prefix, uri in self.xmp_namespaces.items():
            if prefix != 'rdf':
                rdf.set(f'xmlns:{prefix}', uri)
        
        description = ET.SubElement(rdf, 'rdf:Description')
        description.set('rdf:about', '')
        
        # Add metadata as attributes and elements
        for key, value in metadata.items():
            if isinstance(value, str):
                description.set(f'xmp:{key}', value)
            elif isinstance(value, list):
                # Create array structure
                array_elem = ET.SubElement(description, f'dc:{key}')
                bag = ET.SubElement(array_elem, 'rdf:Bag')
                for item in value:
                    li = ET.SubElement(bag, 'rdf:li')
                    li.text = str(item)
            else:
                # Convert to string for other types
                description.set(f'xmp:{key}', str(value))
        
        # Pretty print XMP
        xml_str = ET.tostring(xmpmeta, encoding='unicode')
        pretty_xml = minidom.parseString(xml_str).toprettyxml(indent='  ')
        
        with open(sidecar_path, 'w', encoding='utf-8') as file:
            file.write(pretty_xml)
    
    def _dict_to_xml(self, data: Dict[str, Any], parent: ET.Element):
        """Convert dictionary to XML elements"""
        for key, value in data.items():
            # Clean key name (remove invalid XML characters)
            clean_key = self._clean_xml_tag_name(key)
            
            if isinstance(value, dict):
                elem = ET.SubElement(parent, clean_key)
                self._dict_to_xml(value, elem)
            elif isinstance(value, list):
                for item in value:
                    elem = ET.SubElement(parent, clean_key)
                    if isinstance(item, dict):
                        self._dict_to_xml(item, elem)
                    else:
                        elem.text = str(item)
            else:
                elem = ET.SubElement(parent, clean_key)
                elem.text = str(value)
    
    def _clean_xml_tag_name(self, name: str) -> str:
        """Clean string to be valid XML tag name"""
        # Remove invalid characters and replace with underscore
        import re
        clean_name = re.sub(r'[^\w\-.]', '_', str(name))
        
        # Ensure it doesn't start with a number
        if clean_name and clean_name[0].isdigit():
            clean_name = f'item_{clean_name}'
        
        return clean_name or 'item'
    
    async def sync_sidecar_with_metadata(self, media_file_path: str, 
                                       metadata: Dict[str, Any],
                                       auto_create: bool = True) -> List[str]:
        """
        Synchronize sidecar files with current metadata
        
        Args:
            media_file_path: Path to media file
            metadata: Current metadata
            auto_create: Whether to create sidecar files if they don't exist
            
        Returns:
            List of updated sidecar file paths
        """
        try:
            updated_files = []
            
            # Find existing sidecar files
            existing_sidecars = await self.find_sidecar_files(media_file_path)
            
            # Update existing sidecar files
            for sidecar_info in existing_sidecars:
                sidecar_path = sidecar_info['path']
                format_type = sidecar_info['format'].lower()
                
                if format_type in ['json', 'xml', 'xmp']:
                    await asyncio.get_event_loop().run_in_executor(
                        None, self._write_sidecar_sync, sidecar_path, metadata, format_type
                    )
                    updated_files.append(sidecar_path)
            
            # Create new sidecar files if requested and none exist
            if auto_create and not existing_sidecars:
                json_sidecar = await self.write_sidecar_file(
                    media_file_path, metadata, 'json'
                )
                updated_files.append(json_sidecar)
            
            logger.info(
                "sidecar_sync_completed",
                media_file=media_file_path,
                updated_count=len(updated_files)
            )
            
            return updated_files
            
        except Exception as e:
            logger.error(
                "sidecar_sync_failed",
                media_file=media_file_path,
                error=str(e)
            )
            raise ExtractionError(f"Failed to sync sidecar files: {str(e)}")
    
    async def create_sidecar_template(self, template_name: str, 
                                    template_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a sidecar template for reuse
        
        Args:
            template_name: Name of the template
            template_data: Template data structure
            
        Returns:
            Template information
        """
        template = {
            'id': str(uuid.uuid4()),
            'name': template_name,
            'created_at': datetime.utcnow().isoformat(),
            'version': '1.0',
            'template_data': template_data,
            'supported_formats': ['json', 'xml', 'xmp']
        }
        
        logger.info(
            "sidecar_template_created",
            template_name=template_name,
            template_id=template['id']
        )
        
        return template
    
    async def apply_sidecar_template(self, media_file_path: str, 
                                   template: Dict[str, Any],
                                   metadata_overrides: Dict[str, Any] = None) -> str:
        """
        Apply a sidecar template to create a sidecar file
        
        Args:
            media_file_path: Path to media file
            template: Template to apply
            metadata_overrides: Override values for template
            
        Returns:
            Path to created sidecar file
        """
        try:
            # Merge template data with overrides
            metadata = template['template_data'].copy()
            if metadata_overrides:
                metadata.update(metadata_overrides)
            
            # Add template information
            metadata['template_info'] = {
                'template_id': template['id'],
                'template_name': template['name'],
                'applied_at': datetime.utcnow().isoformat()
            }
            
            # Create sidecar file
            sidecar_path = await self.write_sidecar_file(
                media_file_path, metadata, 'json'
            )
            
            logger.info(
                "sidecar_template_applied",
                media_file=media_file_path,
                template_name=template['name'],
                sidecar_path=sidecar_path
            )
            
            return sidecar_path
            
        except Exception as e:
            logger.error(
                "sidecar_template_apply_failed",
                media_file=media_file_path,
                template_name=template.get('name', 'unknown'),
                error=str(e)
            )
            raise ExtractionError(f"Failed to apply sidecar template: {str(e)}")
    
    async def validate_sidecar_file(self, sidecar_path: str) -> Dict[str, Any]:
        """
        Validate a sidecar file
        
        Args:
            sidecar_path: Path to sidecar file
            
        Returns:
            Validation result
        """
        try:
            validation_result = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'format_info': {},
                'metadata_count': 0
            }
            
            if not os.path.exists(sidecar_path):
                validation_result['valid'] = False
                validation_result['errors'].append('Sidecar file does not exist')
                return validation_result
            
            # Parse the sidecar file
            sidecar_data = await self.read_sidecar_file(sidecar_path)
            
            # Check for parsing errors
            if sidecar_data.get('parsing_errors'):
                validation_result['valid'] = False
                validation_result['errors'].extend(sidecar_data['parsing_errors'])
            
            # Validate format-specific requirements
            file_extension = Path(sidecar_path).suffix.lower()
            
            if file_extension == '.json':
                validation_result.update(self._validate_json_sidecar(sidecar_data))
            elif file_extension in ['.xml', '.xmp']:
                validation_result.update(self._validate_xml_sidecar(sidecar_data))
            
            # Count metadata fields
            metadata = sidecar_data.get('metadata', {})
            validation_result['metadata_count'] = len(metadata) if isinstance(metadata, dict) else 0
            
            logger.info(
                "sidecar_validation_completed",
                sidecar_path=sidecar_path,
                valid=validation_result['valid'],
                errors=len(validation_result['errors'])
            )
            
            return validation_result
            
        except Exception as e:
            logger.error(
                "sidecar_validation_failed",
                sidecar_path=sidecar_path,
                error=str(e)
            )
            return {
                'valid': False,
                'errors': [str(e)],
                'warnings': [],
                'format_info': {},
                'metadata_count': 0
            }
    
    def _validate_json_sidecar(self, sidecar_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate JSON sidecar file"""
        validation_result = {
            'format_info': sidecar_data.get('format_info', {}),
            'errors': [],
            'warnings': []
        }
        
        metadata = sidecar_data.get('metadata', {})
        
        if not isinstance(metadata, dict):
            validation_result['errors'].append('Metadata must be a JSON object')
        
        # Check for required fields (optional validation)
        # This could be extended with schema validation
        
        return validation_result
    
    def _validate_xml_sidecar(self, sidecar_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate XML sidecar file"""
        validation_result = {
            'format_info': sidecar_data.get('format_info', {}),
            'errors': [],
            'warnings': []
        }
        
        # Check if XML was parsed successfully
        if not sidecar_data.get('metadata'):
            validation_result['errors'].append('No metadata found in XML')
        
        # Additional XML-specific validation could be added here
        
        return validation_result