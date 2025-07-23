"""
EXIF Extraction Service

This module provides functionality for extracting EXIF metadata from images.
"""

import os
import json
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import structlog
from PIL import Image, ExifTags
import exifread
import piexif
from io import BytesIO

from ..core.exceptions import ValidationError, ExtractionError

logger = structlog.get_logger()


class ExifExtractor:
    """Extracts EXIF metadata from images using multiple methods"""
    
    def __init__(self):
        self.supported_formats = {
            'JPEG', 'JPG', 'TIFF', 'TIF', 'PNG', 'WEBP', 'BMP', 'DNG', 'CR2', 'NEF', 'ARW'
        }
        
        # Common EXIF tags mapping
        self.exif_tag_mapping = {
            'DateTime': 'date_time',
            'DateTimeOriginal': 'date_time_original',
            'DateTimeDigitized': 'date_time_digitized',
            'Make': 'camera_make',
            'Model': 'camera_model',
            'Software': 'software',
            'Artist': 'artist',
            'Copyright': 'copyright',
            'ImageDescription': 'description',
            'Orientation': 'orientation',
            'XResolution': 'x_resolution',
            'YResolution': 'y_resolution',
            'ResolutionUnit': 'resolution_unit',
            'ColorSpace': 'color_space',
            'WhiteBalance': 'white_balance',
            'Flash': 'flash',
            'FocalLength': 'focal_length',
            'FNumber': 'f_number',
            'ExposureTime': 'exposure_time',
            'ISOSpeedRatings': 'iso_speed',
            'ExposureProgram': 'exposure_program',
            'MeteringMode': 'metering_mode',
            'LightSource': 'light_source',
            'ImageWidth': 'width',
            'ImageLength': 'height',
            'BitsPerSample': 'bits_per_sample',
            'SamplesPerPixel': 'samples_per_pixel',
            'Compression': 'compression',
            'PhotometricInterpretation': 'photometric_interpretation',
            'GPS GPSLatitude': 'gps_latitude',
            'GPS GPSLongitude': 'gps_longitude',
            'GPS GPSAltitude': 'gps_altitude',
            'GPS GPSLatitudeRef': 'gps_latitude_ref',
            'GPS GPSLongitudeRef': 'gps_longitude_ref',
            'GPS GPSAltitudeRef': 'gps_altitude_ref',
            'GPS GPSTimeStamp': 'gps_timestamp',
            'GPS GPSDateStamp': 'gps_datestamp',
            'LensModel': 'lens_model',
            'LensMake': 'lens_make',
            'FocalLengthIn35mmFilm': 'focal_length_35mm',
            'DigitalZoomRatio': 'digital_zoom_ratio',
        }
    
    def is_supported_format(self, file_path: str) -> bool:
        """Check if file format is supported for EXIF extraction"""
        extension = Path(file_path).suffix.upper().lstrip('.')
        return extension in self.supported_formats
    
    async def extract_exif_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract EXIF metadata from image file
        
        Args:
            file_path: Path to image file
            
        Returns:
            Dictionary containing extracted EXIF metadata
        """
        try:
            if not os.path.exists(file_path):
                raise ExtractionError(f"File not found: {file_path}")
            
            if not self.is_supported_format(file_path):
                extension = Path(file_path).suffix
                raise ExtractionError(f"Unsupported file format: {extension}")
            
            # Run extraction in thread pool to avoid blocking
            exif_data = await asyncio.get_event_loop().run_in_executor(
                None, self._extract_exif_sync, file_path
            )
            
            logger.info(
                "exif_extraction_completed",
                file_path=file_path,
                tags_extracted=len(exif_data.get('raw_exif', {}))
            )
            
            return exif_data
            
        except Exception as e:
            logger.error(
                "exif_extraction_failed",
                file_path=file_path,
                error=str(e)
            )
            raise ExtractionError(f"Failed to extract EXIF data: {str(e)}")
    
    def _extract_exif_sync(self, file_path: str) -> Dict[str, Any]:
        """Synchronous EXIF extraction (runs in thread pool)"""
        result = {
            'raw_exif': {},
            'processed_exif': {},
            'gps_data': {},
            'camera_info': {},
            'technical_info': {},
            'extraction_info': {
                'extracted_at': datetime.utcnow().isoformat(),
                'extraction_method': 'multi_method',
                'file_path': file_path,
                'file_size': os.path.getsize(file_path)
            }
        }
        
        # Method 1: Use PIL for basic EXIF
        pil_exif = self._extract_with_pil(file_path)
        if pil_exif:
            result['raw_exif'].update(pil_exif)
        
        # Method 2: Use exifread for detailed EXIF
        exifread_data = self._extract_with_exifread(file_path)
        if exifread_data:
            result['raw_exif'].update(exifread_data)
        
        # Method 3: Use piexif for comprehensive EXIF
        piexif_data = self._extract_with_piexif(file_path)
        if piexif_data:
            result['raw_exif'].update(piexif_data)
        
        # Process and categorize the extracted data
        self._process_exif_data(result)
        
        return result
    
    def _extract_with_pil(self, file_path: str) -> Dict[str, Any]:
        """Extract EXIF using PIL"""
        try:
            with Image.open(file_path) as img:
                exif_dict = img._getexif()
                if not exif_dict:
                    return {}
                
                # Convert numeric tags to names
                named_exif = {}
                for tag_id, value in exif_dict.items():
                    tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                    named_exif[f"PIL_{tag_name}"] = self._convert_exif_value(value)
                
                return named_exif
        except Exception as e:
            logger.debug("pil_exif_extraction_failed", error=str(e))
            return {}
    
    def _extract_with_exifread(self, file_path: str) -> Dict[str, Any]:
        """Extract EXIF using exifread"""
        try:
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f, details=True)
                
                exif_data = {}
                for tag_name, tag_value in tags.items():
                    if tag_name not in ['JPEGThumbnail', 'TIFFThumbnail']:
                        exif_data[f"EXIFREAD_{tag_name}"] = str(tag_value)
                
                return exif_data
        except Exception as e:
            logger.debug("exifread_extraction_failed", error=str(e))
            return {}
    
    def _extract_with_piexif(self, file_path: str) -> Dict[str, Any]:
        """Extract EXIF using piexif"""
        try:
            exif_dict = piexif.load(file_path)
            
            result = {}
            for ifd_name, ifd_data in exif_dict.items():
                if ifd_name == 'thumbnail':
                    continue
                
                if isinstance(ifd_data, dict):
                    for tag_id, value in ifd_data.items():
                        tag_name = piexif.TAGS.get(ifd_name, {}).get(tag_id, tag_id)
                        result[f"PIEXIF_{ifd_name}_{tag_name}"] = self._convert_exif_value(value)
            
            return result
        except Exception as e:
            logger.debug("piexif_extraction_failed", error=str(e))
            return {}
    
    def _convert_exif_value(self, value: Any) -> Any:
        """Convert EXIF values to JSON-serializable format"""
        if isinstance(value, bytes):
            try:
                return value.decode('utf-8')
            except UnicodeDecodeError:
                return value.hex()
        elif isinstance(value, tuple):
            return list(value)
        elif hasattr(value, '__dict__'):
            return str(value)
        else:
            return value
    
    def _process_exif_data(self, result: Dict[str, Any]):
        """Process and categorize raw EXIF data"""
        raw_exif = result['raw_exif']
        processed = result['processed_exif']
        gps_data = result['gps_data']
        camera_info = result['camera_info']
        technical_info = result['technical_info']
        
        # Process standard EXIF tags
        for raw_tag, processed_tag in self.exif_tag_mapping.items():
            value = self._find_exif_value(raw_exif, raw_tag)
            if value is not None:
                processed[processed_tag] = value
        
        # Extract GPS data
        self._extract_gps_data(raw_exif, gps_data)
        
        # Extract camera information
        self._extract_camera_info(raw_exif, camera_info)
        
        # Extract technical information
        self._extract_technical_info(raw_exif, technical_info)
        
        # Process dates
        self._process_dates(processed)
    
    def _find_exif_value(self, raw_exif: Dict[str, Any], tag_name: str) -> Any:
        """Find EXIF value by tag name across different extraction methods"""
        # Check different prefixes from different extraction methods
        prefixes = ['PIL_', 'EXIFREAD_', 'PIEXIF_0th_', 'PIEXIF_Exif_', 'PIEXIF_GPS_']
        
        for prefix in prefixes:
            key = f"{prefix}{tag_name}"
            if key in raw_exif:
                return raw_exif[key]
        
        # Check without prefix
        if tag_name in raw_exif:
            return raw_exif[tag_name]
        
        return None
    
    def _extract_gps_data(self, raw_exif: Dict[str, Any], gps_data: Dict[str, Any]):
        """Extract and process GPS data"""
        try:
            lat = self._find_exif_value(raw_exif, 'GPSLatitude')
            lat_ref = self._find_exif_value(raw_exif, 'GPSLatitudeRef')
            lon = self._find_exif_value(raw_exif, 'GPSLongitude')
            lon_ref = self._find_exif_value(raw_exif, 'GPSLongitudeRef')
            alt = self._find_exif_value(raw_exif, 'GPSAltitude')
            alt_ref = self._find_exif_value(raw_exif, 'GPSAltitudeRef')
            
            if lat and lon:
                gps_data['has_gps'] = True
                gps_data['latitude'] = self._convert_gps_coordinate(lat, lat_ref)
                gps_data['longitude'] = self._convert_gps_coordinate(lon, lon_ref)
                
                if alt:
                    gps_data['altitude'] = self._convert_gps_altitude(alt, alt_ref)
                
                # Extract timestamp
                gps_time = self._find_exif_value(raw_exif, 'GPSTimeStamp')
                gps_date = self._find_exif_value(raw_exif, 'GPSDateStamp')
                
                if gps_time and gps_date:
                    gps_data['gps_timestamp'] = f"{gps_date} {gps_time}"
            else:
                gps_data['has_gps'] = False
                
        except Exception as e:
            logger.debug("gps_extraction_failed", error=str(e))
            gps_data['has_gps'] = False
    
    def _extract_camera_info(self, raw_exif: Dict[str, Any], camera_info: Dict[str, Any]):
        """Extract camera-specific information"""
        camera_fields = {
            'make': 'Make',
            'model': 'Model',
            'lens_model': 'LensModel',
            'lens_make': 'LensMake',
            'software': 'Software',
            'artist': 'Artist',
            'copyright': 'Copyright',
            'serial_number': 'SerialNumber',
            'firmware_version': 'FirmwareVersion'
        }
        
        for field, tag in camera_fields.items():
            value = self._find_exif_value(raw_exif, tag)
            if value:
                camera_info[field] = value
    
    def _extract_technical_info(self, raw_exif: Dict[str, Any], technical_info: Dict[str, Any]):
        """Extract technical photography information"""
        technical_fields = {
            'focal_length': 'FocalLength',
            'focal_length_35mm': 'FocalLengthIn35mmFilm',
            'f_number': 'FNumber',
            'exposure_time': 'ExposureTime',
            'iso_speed': 'ISOSpeedRatings',
            'exposure_program': 'ExposureProgram',
            'metering_mode': 'MeteringMode',
            'light_source': 'LightSource',
            'flash': 'Flash',
            'white_balance': 'WhiteBalance',
            'color_space': 'ColorSpace',
            'width': 'ImageWidth',
            'height': 'ImageLength',
            'orientation': 'Orientation',
            'x_resolution': 'XResolution',
            'y_resolution': 'YResolution',
            'resolution_unit': 'ResolutionUnit',
            'compression': 'Compression',
            'bits_per_sample': 'BitsPerSample',
            'samples_per_pixel': 'SamplesPerPixel',
            'digital_zoom_ratio': 'DigitalZoomRatio'
        }
        
        for field, tag in technical_fields.items():
            value = self._find_exif_value(raw_exif, tag)
            if value:
                technical_info[field] = value
    
    def _process_dates(self, processed: Dict[str, Any]):
        """Process and standardize date fields"""
        date_fields = ['date_time', 'date_time_original', 'date_time_digitized']
        
        for field in date_fields:
            if field in processed:
                try:
                    # Try to parse and standardize date format
                    date_str = str(processed[field])
                    # Handle common EXIF date format: "YYYY:MM:DD HH:MM:SS"
                    if ':' in date_str and len(date_str) >= 19:
                        date_str = date_str.replace(':', '-', 2)  # Replace first two colons
                        parsed_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                        processed[field] = parsed_date.isoformat()
                except Exception as e:
                    logger.debug(f"date_parsing_failed for {field}", error=str(e))
    
    def _convert_gps_coordinate(self, coord: Any, ref: str) -> float:
        """Convert GPS coordinate from EXIF format to decimal degrees"""
        try:
            if isinstance(coord, str):
                # Parse string format like "[12, 34, 56.78]"
                coord = eval(coord)
            
            if isinstance(coord, (list, tuple)) and len(coord) >= 3:
                degrees = float(coord[0])
                minutes = float(coord[1])
                seconds = float(coord[2])
                
                decimal = degrees + minutes/60 + seconds/3600
                
                if ref in ['S', 'W']:
                    decimal = -decimal
                
                return decimal
        except Exception as e:
            logger.debug("gps_coordinate_conversion_failed", error=str(e))
        
        return 0.0
    
    def _convert_gps_altitude(self, alt: Any, ref: str) -> float:
        """Convert GPS altitude from EXIF format"""
        try:
            altitude = float(alt)
            if ref == '1':  # Below sea level
                altitude = -altitude
            return altitude
        except Exception as e:
            logger.debug("gps_altitude_conversion_failed", error=str(e))
        
        return 0.0
    
    async def extract_batch(self, file_paths: List[str]) -> Dict[str, Dict[str, Any]]:
        """Extract EXIF metadata from multiple files in batch"""
        results = {}
        
        for file_path in file_paths:
            try:
                results[file_path] = await self.extract_exif_metadata(file_path)
            except Exception as e:
                logger.error(
                    "batch_exif_extraction_failed",
                    file_path=file_path,
                    error=str(e)
                )
                results[file_path] = {
                    'error': str(e),
                    'extraction_info': {
                        'extracted_at': datetime.utcnow().isoformat(),
                        'extraction_method': 'multi_method',
                        'file_path': file_path,
                        'success': False
                    }
                }
        
        return results
    
    async def get_basic_image_info(self, file_path: str) -> Dict[str, Any]:
        """Get basic image information without full EXIF extraction"""
        try:
            info = await asyncio.get_event_loop().run_in_executor(
                None, self._get_basic_image_info_sync, file_path
            )
            return info
        except Exception as e:
            logger.error("basic_image_info_failed", file_path=file_path, error=str(e))
            raise ExtractionError(f"Failed to get basic image info: {str(e)}")
    
    def _get_basic_image_info_sync(self, file_path: str) -> Dict[str, Any]:
        """Get basic image information synchronously"""
        with Image.open(file_path) as img:
            return {
                'width': img.width,
                'height': img.height,
                'format': img.format,
                'mode': img.mode,
                'has_transparency': img.mode in ('RGBA', 'LA') or 'transparency' in img.info,
                'file_size': os.path.getsize(file_path),
                'aspect_ratio': round(img.width / img.height, 2) if img.height > 0 else 0
            }