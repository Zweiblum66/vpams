"""
Tests for EXIF Extractor

Test cases for the EXIF metadata extraction functionality.
"""

import pytest
import tempfile
import os
from pathlib import Path
from uuid import uuid4
from PIL import Image, ExifTags
import piexif

from src.services.exif_extractor import ExifExtractor
from src.core.exceptions import ExtractionError


class TestExifExtractor:
    """Test cases for ExifExtractor"""

    @pytest.fixture
    def extractor(self):
        """Create an ExifExtractor instance"""
        return ExifExtractor()

    @pytest.fixture
    def sample_image_with_exif(self):
        """Create a sample image with EXIF data"""
        # Create a temporary image file with EXIF data
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            # Create a simple image
            img = Image.new('RGB', (100, 100), color='red')
            
            # Create EXIF data
            exif_dict = {
                "0th": {
                    piexif.ImageIFD.Make: "Test Camera",
                    piexif.ImageIFD.Model: "Test Model",
                    piexif.ImageIFD.DateTime: "2024:01:01 12:00:00",
                    piexif.ImageIFD.Software: "Test Software",
                    piexif.ImageIFD.Artist: "Test Artist",
                    piexif.ImageIFD.Copyright: "Test Copyright",
                    piexif.ImageIFD.ImageWidth: 100,
                    piexif.ImageIFD.ImageLength: 100,
                    piexif.ImageIFD.Orientation: 1,
                    piexif.ImageIFD.XResolution: (72, 1),
                    piexif.ImageIFD.YResolution: (72, 1),
                    piexif.ImageIFD.ResolutionUnit: 2,
                },
                "Exif": {
                    piexif.ExifIFD.DateTimeOriginal: "2024:01:01 12:00:00",
                    piexif.ExifIFD.DateTimeDigitized: "2024:01:01 12:00:00",
                    piexif.ExifIFD.ISOSpeedRatings: 100,
                    piexif.ExifIFD.ExposureTime: (1, 60),
                    piexif.ExifIFD.FNumber: (28, 10),
                    piexif.ExifIFD.FocalLength: (50, 1),
                    piexif.ExifIFD.ExposureProgram: 2,
                    piexif.ExifIFD.MeteringMode: 5,
                    piexif.ExifIFD.LightSource: 1,
                    piexif.ExifIFD.Flash: 16,
                    piexif.ExifIFD.WhiteBalance: 0,
                    piexif.ExifIFD.ColorSpace: 1,
                },
                "GPS": {
                    piexif.GPSIFD.GPSLatitude: ((40, 1), (45, 1), (1234, 100)),
                    piexif.GPSIFD.GPSLatitudeRef: "N",
                    piexif.GPSIFD.GPSLongitude: ((74, 1), (0, 1), (5678, 100)),
                    piexif.GPSIFD.GPSLongitudeRef: "W",
                    piexif.GPSIFD.GPSAltitude: (100, 1),
                    piexif.GPSIFD.GPSAltitudeRef: 0,
                    piexif.GPSIFD.GPSTimeStamp: ((12, 1), (0, 1), (0, 1)),
                    piexif.GPSIFD.GPSDateStamp: "2024:01:01",
                }
            }
            
            # Convert to bytes and save
            exif_bytes = piexif.dump(exif_dict)
            img.save(tmp_file.name, exif=exif_bytes)
            
            yield tmp_file.name
            
            # Cleanup
            os.unlink(tmp_file.name)

    @pytest.fixture
    def sample_image_without_exif(self):
        """Create a sample image without EXIF data"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            img = Image.new('RGB', (200, 150), color='blue')
            img.save(tmp_file.name)
            
            yield tmp_file.name
            
            # Cleanup
            os.unlink(tmp_file.name)

    def test_is_supported_format(self, extractor):
        """Test format support detection"""
        assert extractor.is_supported_format("test.jpg") == True
        assert extractor.is_supported_format("test.jpeg") == True
        assert extractor.is_supported_format("test.TIFF") == True
        assert extractor.is_supported_format("test.png") == True
        assert extractor.is_supported_format("test.cr2") == True
        assert extractor.is_supported_format("test.nef") == True
        assert extractor.is_supported_format("test.arw") == True
        assert extractor.is_supported_format("test.dng") == True
        
        # Unsupported formats
        assert extractor.is_supported_format("test.mp4") == False
        assert extractor.is_supported_format("test.txt") == False
        assert extractor.is_supported_format("test.pdf") == False

    @pytest.mark.asyncio
    async def test_extract_exif_metadata_with_exif(self, extractor, sample_image_with_exif):
        """Test EXIF extraction from image with EXIF data"""
        result = await extractor.extract_exif_metadata(sample_image_with_exif)
        
        # Check structure
        assert isinstance(result, dict)
        assert 'raw_exif' in result
        assert 'processed_exif' in result
        assert 'gps_data' in result
        assert 'camera_info' in result
        assert 'technical_info' in result
        assert 'extraction_info' in result
        
        # Check processed EXIF data
        processed = result['processed_exif']
        assert 'camera_make' in processed
        assert 'camera_model' in processed
        assert 'date_time' in processed
        assert 'date_time_original' in processed
        assert 'iso_speed' in processed
        assert 'f_number' in processed
        assert 'focal_length' in processed
        
        # Check GPS data
        gps_data = result['gps_data']
        assert gps_data['has_gps'] == True
        assert 'latitude' in gps_data
        assert 'longitude' in gps_data
        assert 'altitude' in gps_data
        
        # Check camera info
        camera_info = result['camera_info']
        assert camera_info['make'] == "Test Camera"
        assert camera_info['model'] == "Test Model"
        assert camera_info['artist'] == "Test Artist"
        assert camera_info['copyright'] == "Test Copyright"
        
        # Check technical info
        technical_info = result['technical_info']
        assert technical_info['width'] == 100
        assert technical_info['height'] == 100
        assert technical_info['iso_speed'] == 100
        
        # Check extraction info
        extraction_info = result['extraction_info']
        assert extraction_info['extraction_method'] == 'multi_method'
        assert extraction_info['file_path'] == sample_image_with_exif
        assert 'extracted_at' in extraction_info

    @pytest.mark.asyncio
    async def test_extract_exif_metadata_without_exif(self, extractor, sample_image_without_exif):
        """Test EXIF extraction from image without EXIF data"""
        result = await extractor.extract_exif_metadata(sample_image_without_exif)
        
        # Check structure exists but may be empty
        assert isinstance(result, dict)
        assert 'raw_exif' in result
        assert 'processed_exif' in result
        assert 'gps_data' in result
        assert 'camera_info' in result
        assert 'technical_info' in result
        assert 'extraction_info' in result
        
        # GPS should be false
        assert result['gps_data']['has_gps'] == False
        
        # Extraction info should be present
        assert result['extraction_info']['extraction_method'] == 'multi_method'
        assert result['extraction_info']['file_path'] == sample_image_without_exif

    @pytest.mark.asyncio
    async def test_extract_exif_metadata_nonexistent_file(self, extractor):
        """Test EXIF extraction from non-existent file"""
        with pytest.raises(ExtractionError) as exc_info:
            await extractor.extract_exif_metadata("/nonexistent/file.jpg")
        
        assert "File not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_extract_exif_metadata_unsupported_format(self, extractor):
        """Test EXIF extraction from unsupported format"""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp_file:
            tmp_file.write(b"test content")
            tmp_file.flush()
            
            try:
                with pytest.raises(ExtractionError) as exc_info:
                    await extractor.extract_exif_metadata(tmp_file.name)
                
                assert "Unsupported file format" in str(exc_info.value)
            finally:
                os.unlink(tmp_file.name)

    @pytest.mark.asyncio
    async def test_get_basic_image_info(self, extractor, sample_image_with_exif):
        """Test basic image information extraction"""
        result = await extractor.get_basic_image_info(sample_image_with_exif)
        
        assert isinstance(result, dict)
        assert result['width'] == 100
        assert result['height'] == 100
        assert result['format'] == 'JPEG'
        assert result['mode'] == 'RGB'
        assert result['has_transparency'] == False
        assert result['aspect_ratio'] == 1.0
        assert 'file_size' in result
        assert result['file_size'] > 0

    @pytest.mark.asyncio
    async def test_extract_batch(self, extractor, sample_image_with_exif, sample_image_without_exif):
        """Test batch EXIF extraction"""
        file_paths = [sample_image_with_exif, sample_image_without_exif]
        
        results = await extractor.extract_batch(file_paths)
        
        assert isinstance(results, dict)
        assert len(results) == 2
        
        # Check results for file with EXIF
        result1 = results[sample_image_with_exif]
        assert 'raw_exif' in result1
        assert 'processed_exif' in result1
        assert result1['gps_data']['has_gps'] == True
        
        # Check results for file without EXIF
        result2 = results[sample_image_without_exif]
        assert 'raw_exif' in result2
        assert 'processed_exif' in result2
        assert result2['gps_data']['has_gps'] == False

    @pytest.mark.asyncio
    async def test_extract_batch_with_invalid_file(self, extractor, sample_image_with_exif):
        """Test batch EXIF extraction with invalid file"""
        file_paths = [sample_image_with_exif, "/nonexistent/file.jpg"]
        
        results = await extractor.extract_batch(file_paths)
        
        assert isinstance(results, dict)
        assert len(results) == 2
        
        # Check successful extraction
        result1 = results[sample_image_with_exif]
        assert 'raw_exif' in result1
        assert result1['gps_data']['has_gps'] == True
        
        # Check failed extraction
        result2 = results["/nonexistent/file.jpg"]
        assert 'error' in result2
        assert result2['extraction_info']['success'] == False

    def test_convert_exif_value(self, extractor):
        """Test EXIF value conversion"""
        # Test bytes
        assert extractor._convert_exif_value(b"test") == "test"
        assert extractor._convert_exif_value(b"\xff\xfe") == "fffe"
        
        # Test tuple
        assert extractor._convert_exif_value((1, 2, 3)) == [1, 2, 3]
        
        # Test regular values
        assert extractor._convert_exif_value("test") == "test"
        assert extractor._convert_exif_value(123) == 123
        assert extractor._convert_exif_value(45.67) == 45.67

    def test_convert_gps_coordinate(self, extractor):
        """Test GPS coordinate conversion"""
        # Test degrees, minutes, seconds format
        coord = [40, 45, 12.34]
        assert abs(extractor._convert_gps_coordinate(coord, "N") - 40.753428) < 0.0001
        assert abs(extractor._convert_gps_coordinate(coord, "S") - (-40.753428)) < 0.0001
        assert abs(extractor._convert_gps_coordinate(coord, "E") - 40.753428) < 0.0001
        assert abs(extractor._convert_gps_coordinate(coord, "W") - (-40.753428)) < 0.0001
        
        # Test string format
        coord_str = "[40, 45, 12.34]"
        assert abs(extractor._convert_gps_coordinate(coord_str, "N") - 40.753428) < 0.0001

    def test_convert_gps_altitude(self, extractor):
        """Test GPS altitude conversion"""
        # Above sea level
        assert extractor._convert_gps_altitude(100, "0") == 100.0
        
        # Below sea level
        assert extractor._convert_gps_altitude(100, "1") == -100.0
        
        # String input
        assert extractor._convert_gps_altitude("50.5", "0") == 50.5

    def test_find_exif_value(self, extractor):
        """Test EXIF value finding across different extraction methods"""
        raw_exif = {
            "PIL_Make": "Canon",
            "EXIFREAD_Image Make": "Canon",
            "PIEXIF_0th_Make": "Canon",
            "PIEXIF_Exif_ISOSpeedRatings": 200,
            "direct_value": "test"
        }
        
        assert extractor._find_exif_value(raw_exif, "Make") == "Canon"
        assert extractor._find_exif_value(raw_exif, "ISOSpeedRatings") == 200
        assert extractor._find_exif_value(raw_exif, "direct_value") == "test"
        assert extractor._find_exif_value(raw_exif, "NonExistent") is None

    def test_process_dates(self, extractor):
        """Test date processing"""
        processed = {
            "date_time": "2024:01:01 12:00:00",
            "date_time_original": "2024:01:01 12:00:00",
            "invalid_date": "not a date"
        }
        
        extractor._process_dates(processed)
        
        assert processed["date_time"] == "2024-01-01T12:00:00"
        assert processed["date_time_original"] == "2024-01-01T12:00:00"
        assert processed["invalid_date"] == "not a date"  # Should remain unchanged

    @pytest.mark.asyncio
    async def test_extract_from_png_file(self, extractor):
        """Test EXIF extraction from PNG file"""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            img = Image.new('RGB', (100, 100), color='green')
            img.save(tmp_file.name)
            
            try:
                result = await extractor.extract_exif_metadata(tmp_file.name)
                
                # PNG files typically don't have EXIF data
                assert isinstance(result, dict)
                assert 'raw_exif' in result
                assert 'extraction_info' in result
                assert result['extraction_info']['file_path'] == tmp_file.name
                
            finally:
                os.unlink(tmp_file.name)

    @pytest.mark.asyncio
    async def test_extract_from_various_formats(self, extractor):
        """Test EXIF extraction from various supported formats"""
        formats = ['.jpg', '.jpeg', '.tiff', '.png', '.bmp', '.webp']
        
        for fmt in formats:
            with tempfile.NamedTemporaryFile(suffix=fmt, delete=False) as tmp_file:
                img = Image.new('RGB', (50, 50), color='white')
                img.save(tmp_file.name)
                
                try:
                    result = await extractor.extract_exif_metadata(tmp_file.name)
                    
                    # Should succeed for all supported formats
                    assert isinstance(result, dict)
                    assert 'extraction_info' in result
                    assert result['extraction_info']['file_path'] == tmp_file.name
                    
                finally:
                    os.unlink(tmp_file.name)