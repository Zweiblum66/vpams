"""
Tests for Audio Extractor

Test cases for the audio metadata extraction functionality.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from src.services.audio_extractor import AudioExtractor
from src.core.exceptions import ExtractionError


class TestAudioExtractor:
    """Test cases for AudioExtractor"""

    @pytest.fixture
    def extractor(self):
        """Create an AudioExtractor instance"""
        return AudioExtractor()

    @pytest.fixture
    def mock_mutagen_result(self):
        """Mock mutagen extraction result"""
        return {
            'format': 'audio/mpeg',
            'length': 240.5,
            'bitrate': 320,
            'channels': 2,
            'sample_rate': 44100,
            'tags': {
                'TIT2': ['Test Song'],
                'TPE1': ['Test Artist'],
                'TALB': ['Test Album'],
                'TDRC': ['2024'],
                'TCON': ['Rock'],
                'TRCK': ['1/12'],
                'TPE2': ['Test Album Artist']
            }
        }

    @pytest.fixture
    def mock_tinytag_result(self):
        """Mock tinytag extraction result"""
        return {
            'format': 256000,
            'length': 240.5,
            'bitrate': 320,
            'channels': 2,
            'sample_rate': 44100,
            'tags': {
                'title': 'Test Song',
                'artist': 'Test Artist',
                'album': 'Test Album',
                'year': '2024',
                'genre': 'Rock',
                'track': '1',
                'track_total': '12'
            }
        }

    def test_is_supported_format(self, extractor):
        """Test format support detection"""
        # Supported formats
        assert extractor.is_supported_format("test.mp3") == True
        assert extractor.is_supported_format("test.FLAC") == True
        assert extractor.is_supported_format("test.ogg") == True
        assert extractor.is_supported_format("test.m4a") == True
        assert extractor.is_supported_format("test.wav") == True
        assert extractor.is_supported_format("test.aac") == True
        assert extractor.is_supported_format("test.wma") == True
        assert extractor.is_supported_format("test.opus") == True
        
        # Unsupported formats
        assert extractor.is_supported_format("test.mp4") == False
        assert extractor.is_supported_format("test.jpg") == False
        assert extractor.is_supported_format("test.txt") == False

    @pytest.mark.asyncio
    async def test_extract_audio_metadata_success(self, extractor, mock_mutagen_result, mock_tinytag_result):
        """Test successful audio metadata extraction"""
        test_file = "/test/audio.mp3"
        
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1024000), \
             patch.object(extractor, '_extract_metadata_sync') as mock_extract:
            
            # Mock the sync extraction result
            mock_extract.return_value = {
                'file_info': {
                    'file_path': test_file,
                    'file_size': 1024000,
                    'file_name': 'audio.mp3',
                    'file_extension': '.mp3',
                    'extracted_at': '2024-01-01T12:00:00',
                    'extraction_method': 'multi_method',
                    'extraction_tool': 'audio_extractor'
                },
                'raw_metadata': {
                    'mutagen': mock_mutagen_result,
                    'tinytag': mock_tinytag_result
                },
                'processed_metadata': {
                    'title': 'Test Song',
                    'artist': 'Test Artist',
                    'album': 'Test Album',
                    'year': '2024',
                    'genre': 'Rock',
                    'track_number': '1'
                },
                'technical_info': {
                    'duration': 240.5,
                    'duration_formatted': '04:00',
                    'bitrate': 320,
                    'bitrate_formatted': '320 kbps',
                    'channels': 2,
                    'channel_layout': 'stereo',
                    'sample_rate': 44100,
                    'sample_rate_formatted': '44100 Hz'
                },
                'tags': {
                    'basic': {
                        'title': 'Test Song',
                        'artist': 'Test Artist',
                        'album': 'Test Album'
                    },
                    'extended': {},
                    'technical': {},
                    'custom': {}
                },
                'format_info': {
                    'mime_type': 'audio/mpeg'
                },
                'stream_info': {
                    'audio_channels': 2,
                    'sample_rate': 44100,
                    'bitrate': 320
                },
                'extraction_errors': []
            }
            
            result = await extractor.extract_audio_metadata(test_file)
            
            # Check structure
            assert isinstance(result, dict)
            assert 'file_info' in result
            assert 'raw_metadata' in result
            assert 'processed_metadata' in result
            assert 'technical_info' in result
            assert 'tags' in result
            
            # Check file info
            file_info = result['file_info']
            assert file_info['file_path'] == test_file
            assert file_info['file_size'] == 1024000
            assert file_info['extraction_tool'] == 'audio_extractor'
            
            # Check processed metadata
            processed = result['processed_metadata']
            assert processed['title'] == 'Test Song'
            assert processed['artist'] == 'Test Artist'
            assert processed['album'] == 'Test Album'
            assert processed['year'] == '2024'
            assert processed['genre'] == 'Rock'
            
            # Check technical info
            technical = result['technical_info']
            assert technical['duration'] == 240.5
            assert technical['bitrate'] == 320
            assert technical['channels'] == 2
            assert technical['sample_rate'] == 44100

    @pytest.mark.asyncio
    async def test_extract_audio_metadata_file_not_found(self, extractor):
        """Test extraction with non-existent file"""
        with patch('os.path.exists', return_value=False):
            with pytest.raises(ExtractionError) as exc_info:
                await extractor.extract_audio_metadata("/nonexistent/file.mp3")
            
            assert "File not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_extract_audio_metadata_unsupported_format(self, extractor):
        """Test extraction with unsupported format"""
        with patch('os.path.exists', return_value=True):
            with pytest.raises(ExtractionError) as exc_info:
                await extractor.extract_audio_metadata("/test/file.txt")
            
            assert "Unsupported file format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_extract_batch(self, extractor):
        """Test batch audio metadata extraction"""
        file_paths = ["/test/audio1.mp3", "/test/audio2.mp3"]
        
        with patch.object(extractor, 'extract_audio_metadata') as mock_extract:
            mock_extract.return_value = {
                'file_info': {'file_path': 'test'},
                'processed_metadata': {'title': 'Test'}
            }
            
            results = await extractor.extract_batch(file_paths)
            
            assert isinstance(results, dict)
            assert len(results) == 2
            
            # Check that extract_audio_metadata was called for each file
            assert mock_extract.call_count == 2

    @pytest.mark.asyncio
    async def test_extract_batch_with_errors(self, extractor):
        """Test batch extraction with some files failing"""
        file_paths = ["/test/audio1.mp3", "/test/audio2.mp3"]
        
        def side_effect(file_path):
            if file_path == "/test/audio1.mp3":
                return {'file_info': {'file_path': file_path}, 'processed_metadata': {'title': 'Test'}}
            else:
                raise ExtractionError("Test error")
        
        with patch.object(extractor, 'extract_audio_metadata', side_effect=side_effect):
            results = await extractor.extract_batch(file_paths)
            
            assert isinstance(results, dict)
            assert len(results) == 2
            
            # Check successful extraction
            assert 'file_info' in results["/test/audio1.mp3"]
            
            # Check failed extraction
            failed_result = results["/test/audio2.mp3"]
            assert 'error' in failed_result
            assert failed_result['file_info']['success'] == False

    @pytest.mark.asyncio
    async def test_get_audio_summary(self, extractor):
        """Test audio summary generation"""
        test_file = "/test/audio.mp3"
        
        mock_metadata = {
            'file_info': {
                'file_name': 'audio.mp3'
            },
            'format_info': {
                'mime_type': 'audio/mpeg'
            },
            'technical_info': {
                'duration_formatted': '04:00',
                'bitrate_formatted': '320 kbps',
                'sample_rate_formatted': '44100 Hz',
                'channel_layout': 'stereo'
            },
            'processed_metadata': {
                'title': 'Test Song',
                'artist': 'Test Artist',
                'album': 'Test Album',
                'genre': 'Rock',
                'year': '2024'
            }
        }
        
        with patch.object(extractor, 'extract_audio_metadata', return_value=mock_metadata):
            summary = await extractor.get_audio_summary(test_file)
            
            assert summary['file_path'] == test_file
            assert summary['file_name'] == 'audio.mp3'
            assert summary['format'] == 'audio/mpeg'
            assert summary['duration'] == '04:00'
            assert summary['bitrate'] == '320 kbps'
            assert summary['sample_rate'] == '44100 Hz'
            assert summary['channels'] == 'stereo'
            assert summary['title'] == 'Test Song'
            assert summary['artist'] == 'Test Artist'
            assert summary['album'] == 'Test Album'
            assert summary['genre'] == 'Rock'
            assert summary['year'] == '2024'
            assert summary['has_tags'] == True
            assert summary['extraction_success'] == True

    def test_extract_with_mutagen(self, extractor):
        """Test mutagen extraction method"""
        test_file = "/test/audio.mp3"
        
        # Mock mutagen
        mock_file = Mock()
        mock_file.mime = ['audio/mpeg']
        mock_file.info.length = 240.5
        mock_file.info.bitrate = 320
        mock_file.info.channels = 2
        mock_file.info.sample_rate = 44100
        mock_file.tags = {
            'TIT2': ['Test Song'],
            'TPE1': ['Test Artist'],
            'TALB': ['Test Album']
        }
        
        with patch('mutagen.File', return_value=mock_file):
            result = extractor._extract_with_mutagen(test_file)
            
            assert result is not None
            assert result['format'] == 'audio/mpeg'
            assert result['length'] == 240.5
            assert result['bitrate'] == 320
            assert result['channels'] == 2
            assert result['sample_rate'] == 44100
            assert result['tags']['TIT2'] == ['Test Song']

    def test_extract_with_tinytag(self, extractor):
        """Test tinytag extraction method"""
        test_file = "/test/audio.mp3"
        
        # Mock tinytag
        mock_tag = Mock()
        mock_tag.filesize = 1024000
        mock_tag.duration = 240.5
        mock_tag.bitrate = 320
        mock_tag.channels = 2
        mock_tag.samplerate = 44100
        mock_tag.title = 'Test Song'
        mock_tag.artist = 'Test Artist'
        mock_tag.album = 'Test Album'
        mock_tag.year = '2024'
        mock_tag.genre = 'Rock'
        mock_tag.track = '1'
        mock_tag.track_total = '12'
        mock_tag.comment = None
        mock_tag.extra = None
        
        with patch('tinytag.TinyTag.get', return_value=mock_tag):
            result = extractor._extract_with_tinytag(test_file)
            
            assert result is not None
            assert result['length'] == 240.5
            assert result['bitrate'] == 320
            assert result['channels'] == 2
            assert result['sample_rate'] == 44100
            assert result['tags']['title'] == 'Test Song'
            assert result['tags']['artist'] == 'Test Artist'

    def test_extract_with_eyed3(self, extractor):
        """Test eyed3 extraction method"""
        test_file = "/test/audio.mp3"
        
        # Mock eyed3
        mock_audio = Mock()
        mock_audio.info.time_secs = 240.5
        mock_audio.info.bit_rate = (None, 320)
        mock_audio.info.mode = 'stereo'
        mock_audio.info.sample_freq = 44100
        mock_audio.tag.title = 'Test Song'
        mock_audio.tag.artist = 'Test Artist'
        mock_audio.tag.album = 'Test Album'
        mock_audio.tag.genre = Mock()
        mock_audio.tag.genre.name = 'Rock'
        mock_audio.tag.track_num = (1, 12)
        
        with patch('eyed3.load', return_value=mock_audio):
            result = extractor._extract_with_eyed3(test_file)
            
            assert result is not None
            assert result['format'] == 'audio/mpeg'
            assert result['length'] == 240.5
            assert result['bitrate'] == 320
            assert result['channels'] == 'stereo'
            assert result['sample_rate'] == 44100

    def test_extract_with_taglib(self, extractor):
        """Test taglib extraction method"""
        test_file = "/test/audio.mp3"
        
        # Mock taglib
        mock_file = Mock()
        mock_file.length = 240.5
        mock_file.bitrate = 320
        mock_file.channels = 2
        mock_file.sampleRate = 44100
        mock_file.tags = {
            'TITLE': ['Test Song'],
            'ARTIST': ['Test Artist'],
            'ALBUM': ['Test Album']
        }
        
        with patch('taglib.File', return_value=mock_file):
            result = extractor._extract_with_taglib(test_file)
            
            assert result is not None
            assert result['length'] == 240.5
            assert result['bitrate'] == 320
            assert result['channels'] == 2
            assert result['sample_rate'] == 44100
            assert result['tags']['TITLE'] == ['Test Song']

    def test_process_metadata(self, extractor):
        """Test metadata processing and mapping"""
        raw_metadata = {
            'mutagen': {
                'tags': {
                    'TIT2': ['Test Song'],
                    'TPE1': ['Test Artist'],
                    'TALB': ['Test Album']
                }
            },
            'tinytag': {
                'tags': {
                    'title': 'Test Song',
                    'artist': 'Test Artist',
                    'genre': 'Rock'
                }
            }
        }
        
        result = extractor._process_metadata(raw_metadata)
        
        # Check that metadata was processed and mapped correctly
        assert 'title' in result
        assert 'artist' in result
        assert 'album' in result
        assert 'genre' in result

    def test_extract_technical_info(self, extractor):
        """Test technical information extraction"""
        raw_metadata = {
            'mutagen': {
                'length': 240.5,
                'bitrate': 320,
                'channels': 2,
                'sample_rate': 44100
            }
        }
        
        result = extractor._extract_technical_info(raw_metadata)
        
        assert result['duration'] == 240.5
        assert result['duration_formatted'] == '04:00'
        assert result['bitrate'] == 320
        assert result['bitrate_formatted'] == '320 kbps'
        assert result['channels'] == 2
        assert result['channel_layout'] == 'stereo'
        assert result['sample_rate'] == 44100
        assert result['sample_rate_formatted'] == '44100 Hz'

    def test_extract_tags(self, extractor):
        """Test tag categorization"""
        raw_metadata = {
            'mutagen': {
                'tags': {
                    'TIT2': ['Test Song'],
                    'TPE1': ['Test Artist'],
                    'COMM': ['Test Comment'],
                    'TENC': ['Test Encoder']
                }
            }
        }
        
        with patch.object(extractor, '_process_metadata') as mock_process:
            mock_process.return_value = {
                'title': 'Test Song',
                'artist': 'Test Artist',
                'comment': 'Test Comment',
                'encoded_by': 'Test Encoder'
            }
            
            result = extractor._extract_tags(raw_metadata)
            
            assert 'basic' in result
            assert 'extended' in result
            assert 'technical' in result
            assert 'custom' in result
            
            # Check categorization
            assert result['basic']['title'] == 'Test Song'
            assert result['basic']['artist'] == 'Test Artist'
            assert result['extended']['comment'] == 'Test Comment'
            assert result['technical']['encoded_by'] == 'Test Encoder'

    def test_format_duration(self, extractor):
        """Test duration formatting"""
        assert extractor._format_duration(125.5) == "02:05"
        assert extractor._format_duration(3661.0) == "01:01:01"
        assert extractor._format_duration(45.0) == "00:45"
        assert extractor._format_duration("invalid") == "00:00"

    def test_get_channel_layout(self, extractor):
        """Test channel layout description"""
        assert extractor._get_channel_layout(1) == "mono"
        assert extractor._get_channel_layout(2) == "stereo"
        assert extractor._get_channel_layout(6) == "5.1"
        assert extractor._get_channel_layout(8) == "7.1"
        assert extractor._get_channel_layout(10) == "10 channels"
        assert extractor._get_channel_layout("stereo") == "stereo"

    def test_extract_format_info(self, extractor):
        """Test format information extraction"""
        raw_metadata = {
            'mutagen': {
                'format': 'audio/mpeg'
            }
        }
        
        result = extractor._extract_format_info(raw_metadata)
        
        assert result['mime_type'] == 'audio/mpeg'

    def test_extract_stream_info(self, extractor):
        """Test stream information extraction"""
        raw_metadata = {
            'mutagen': {
                'channels': 2,
                'sample_rate': 44100,
                'bitrate': 320
            }
        }
        
        result = extractor._extract_stream_info(raw_metadata)
        
        assert result['audio_channels'] == 2
        assert result['sample_rate'] == 44100
        assert result['bitrate'] == 320

    def test_extract_metadata_sync_with_exceptions(self, extractor):
        """Test sync extraction with method exceptions"""
        test_file = "/test/audio.mp3"
        
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1024000), \
             patch.object(extractor, '_extract_with_mutagen', side_effect=Exception("Test error")), \
             patch.object(extractor, '_extract_with_tinytag', return_value={'tags': {'title': 'Test'}}), \
             patch.object(extractor, '_extract_with_eyed3', return_value=None), \
             patch.object(extractor, '_extract_with_taglib', return_value=None):
            
            result = extractor._extract_metadata_sync(test_file)
            
            # Should handle the exception and continue with other methods
            assert isinstance(result, dict)
            assert 'extraction_errors' in result
            assert len(result['extraction_errors']) > 0
            assert 'raw_metadata' in result
            assert 'tinytag' in result['raw_metadata']

    def test_library_import_failures(self, extractor):
        """Test handling of missing library imports"""
        test_file = "/test/audio.mp3"
        
        # Test mutagen import failure
        with patch('mutagen.File', side_effect=ImportError("mutagen not available")):
            result = extractor._extract_with_mutagen(test_file)
            assert result is None
        
        # Test tinytag import failure
        with patch('tinytag.TinyTag.get', side_effect=ImportError("tinytag not available")):
            result = extractor._extract_with_tinytag(test_file)
            assert result is None
        
        # Test eyed3 import failure
        with patch('eyed3.load', side_effect=ImportError("eyed3 not available")):
            result = extractor._extract_with_eyed3(test_file)
            assert result is None
        
        # Test taglib import failure
        with patch('taglib.File', side_effect=ImportError("taglib not available")):
            result = extractor._extract_with_taglib(test_file)
            assert result is None