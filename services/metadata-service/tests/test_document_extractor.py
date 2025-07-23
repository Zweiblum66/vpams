"""
Tests for Document Extractor

Test cases for the document metadata extraction functionality.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from src.services.document_extractor import DocumentExtractor
from src.core.exceptions import ExtractionError


class TestDocumentExtractor:
    """Test cases for DocumentExtractor"""

    @pytest.fixture
    def extractor(self):
        """Create a DocumentExtractor instance"""
        return DocumentExtractor()

    def test_is_supported_format(self, extractor):
        """Test format support detection"""
        # PDF formats
        assert extractor.is_supported_format("test.pdf") == True
        assert extractor.is_supported_format("test.PDF") == True
        
        # Office formats
        assert extractor.is_supported_format("test.docx") == True
        assert extractor.is_supported_format("test.xlsx") == True
        assert extractor.is_supported_format("test.pptx") == True
        assert extractor.is_supported_format("test.doc") == True
        assert extractor.is_supported_format("test.xls") == True
        assert extractor.is_supported_format("test.ppt") == True
        
        # OpenDocument formats
        assert extractor.is_supported_format("test.odt") == True
        assert extractor.is_supported_format("test.ods") == True
        assert extractor.is_supported_format("test.odp") == True
        
        # Text formats
        assert extractor.is_supported_format("test.txt") == True
        assert extractor.is_supported_format("test.rtf") == True
        assert extractor.is_supported_format("test.csv") == True
        assert extractor.is_supported_format("test.md") == True
        
        # Markup formats
        assert extractor.is_supported_format("test.html") == True
        assert extractor.is_supported_format("test.xml") == True
        
        # E-book formats
        assert extractor.is_supported_format("test.epub") == True
        assert extractor.is_supported_format("test.mobi") == True
        
        # Unsupported formats
        assert extractor.is_supported_format("test.mp3") == False
        assert extractor.is_supported_format("test.jpg") == False
        assert extractor.is_supported_format("test.mp4") == False

    @pytest.mark.asyncio
    async def test_extract_document_metadata_success(self, extractor):
        """Test successful document metadata extraction"""
        test_file = "/test/document.pdf"
        
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1024000), \
             patch.object(extractor, '_extract_metadata_sync') as mock_extract:
            
            # Mock the sync extraction result
            mock_extract.return_value = {
                'file_info': {
                    'file_path': test_file,
                    'file_size': 1024000,
                    'file_name': 'document.pdf',
                    'file_extension': '.pdf',
                    'extracted_at': '2024-01-01T12:00:00',
                    'extraction_method': 'multi_method',
                    'extraction_tool': 'document_extractor'
                },
                'raw_metadata': {
                    'pdf': {
                        'page_count': 10,
                        'is_encrypted': False,
                        'metadata': {
                            'title': 'Test Document',
                            'author': 'Test Author',
                            'subject': 'Test Subject',
                            'creator': 'Test Creator',
                            'producer': 'Test Producer',
                            'creationdate': '2024-01-01T12:00:00',
                            'moddate': '2024-01-01T12:00:00'
                        }
                    }
                },
                'processed_metadata': {
                    'title': 'Test Document',
                    'author': 'Test Author',
                    'subject': 'Test Subject',
                    'creator': 'Test Creator',
                    'producer': 'Test Producer',
                    'creation_date': '2024-01-01T12:00:00',
                    'modification_date': '2024-01-01T12:00:00'
                },
                'document_info': {
                    'page_count': 10
                },
                'content_info': {
                    'estimated_word_count': 1000
                },
                'security_info': {
                    'encrypted': False
                },
                'extraction_errors': []
            }
            
            result = await extractor.extract_document_metadata(test_file)
            
            # Check structure
            assert isinstance(result, dict)
            assert 'file_info' in result
            assert 'raw_metadata' in result
            assert 'processed_metadata' in result
            assert 'document_info' in result
            assert 'content_info' in result
            assert 'security_info' in result
            
            # Check processed metadata
            processed = result['processed_metadata']
            assert processed['title'] == 'Test Document'
            assert processed['author'] == 'Test Author'
            assert processed['subject'] == 'Test Subject'
            
            # Check document info
            document_info = result['document_info']
            assert document_info['page_count'] == 10
            
            # Check security info
            security_info = result['security_info']
            assert security_info['encrypted'] == False

    @pytest.mark.asyncio
    async def test_extract_document_metadata_file_not_found(self, extractor):
        """Test extraction with non-existent file"""
        with patch('os.path.exists', return_value=False):
            with pytest.raises(ExtractionError) as exc_info:
                await extractor.extract_document_metadata("/nonexistent/file.pdf")
            
            assert "File not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_extract_document_metadata_unsupported_format(self, extractor):
        """Test extraction with unsupported format"""
        with patch('os.path.exists', return_value=True):
            with pytest.raises(ExtractionError) as exc_info:
                await extractor.extract_document_metadata("/test/file.mp3")
            
            assert "Unsupported file format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_extract_batch(self, extractor):
        """Test batch document metadata extraction"""
        file_paths = ["/test/doc1.pdf", "/test/doc2.docx"]
        
        with patch.object(extractor, 'extract_document_metadata') as mock_extract:
            mock_extract.return_value = {
                'file_info': {'file_path': 'test'},
                'processed_metadata': {'title': 'Test'}
            }
            
            results = await extractor.extract_batch(file_paths)
            
            assert isinstance(results, dict)
            assert len(results) == 2
            
            # Check that extract_document_metadata was called for each file
            assert mock_extract.call_count == 2

    @pytest.mark.asyncio
    async def test_extract_batch_with_errors(self, extractor):
        """Test batch extraction with some files failing"""
        file_paths = ["/test/doc1.pdf", "/test/doc2.pdf"]
        
        def side_effect(file_path):
            if file_path == "/test/doc1.pdf":
                return {'file_info': {'file_path': file_path}, 'processed_metadata': {'title': 'Test'}}
            else:
                raise ExtractionError("Test error")
        
        with patch.object(extractor, 'extract_document_metadata', side_effect=side_effect):
            results = await extractor.extract_batch(file_paths)
            
            assert isinstance(results, dict)
            assert len(results) == 2
            
            # Check successful extraction
            assert 'file_info' in results["/test/doc1.pdf"]
            
            # Check failed extraction
            failed_result = results["/test/doc2.pdf"]
            assert 'error' in failed_result
            assert failed_result['file_info']['success'] == False

    @pytest.mark.asyncio
    async def test_get_document_summary(self, extractor):
        """Test document summary generation"""
        test_file = "/test/document.pdf"
        
        mock_metadata = {
            'file_info': {
                'file_name': 'document.pdf',
                'file_size': 1024000,
                'file_extension': '.pdf'
            },
            'processed_metadata': {
                'title': 'Test Document',
                'author': 'Test Author',
                'subject': 'Test Subject',
                'creation_date': '2024-01-01T12:00:00',
                'modification_date': '2024-01-01T12:00:00'
            },
            'document_info': {
                'page_count': 10
            },
            'content_info': {
                'word_count': 1000,
                'character_count': 5000
            },
            'security_info': {
                'encrypted': False
            }
        }
        
        with patch.object(extractor, 'extract_document_metadata', return_value=mock_metadata):
            summary = await extractor.get_document_summary(test_file)
            
            assert summary['file_path'] == test_file
            assert summary['file_name'] == 'document.pdf'
            assert summary['file_size'] == 1024000
            assert summary['file_extension'] == '.pdf'
            assert summary['title'] == 'Test Document'
            assert summary['author'] == 'Test Author'
            assert summary['subject'] == 'Test Subject'
            assert summary['creation_date'] == '2024-01-01T12:00:00'
            assert summary['modification_date'] == '2024-01-01T12:00:00'
            assert summary['page_count'] == 10
            assert summary['word_count'] == 1000
            assert summary['character_count'] == 5000
            assert summary['has_metadata'] == True
            assert summary['is_encrypted'] == False
            assert summary['extraction_success'] == True

    def test_extract_pdf_metadata(self, extractor):
        """Test PDF metadata extraction"""
        test_file = "/test/document.pdf"
        
        # Mock PyPDF2
        mock_reader = Mock()
        mock_reader.pages = [Mock() for _ in range(5)]  # 5 pages
        mock_reader.is_encrypted = False
        mock_reader.metadata = {
            '/Title': 'Test Document',
            '/Author': 'Test Author',
            '/Subject': 'Test Subject',
            '/Creator': 'Test Creator',
            '/Producer': 'Test Producer',
            '/CreationDate': 'D:20240101120000Z',
            '/ModDate': 'D:20240101120000Z'
        }
        mock_reader.pages[0].extract_text.return_value = "This is test content for the first page."
        
        with patch('PyPDF2.PdfReader', return_value=mock_reader), \
             patch('builtins.open', mock_open()):
            
            result = extractor._extract_pdf_metadata(test_file)
            
            assert result is not None
            assert result['page_count'] == 5
            assert result['is_encrypted'] == False
            assert result['metadata']['title'] == 'Test Document'
            assert result['metadata']['author'] == 'Test Author'
            assert result['estimated_word_count'] > 0

    def test_extract_docx_metadata(self, extractor):
        """Test DOCX metadata extraction"""
        test_file = "/test/document.docx"
        
        # Mock docx
        mock_doc = Mock()
        mock_doc.core_properties.title = 'Test Document'
        mock_doc.core_properties.author = 'Test Author'
        mock_doc.core_properties.subject = 'Test Subject'
        mock_doc.core_properties.keywords = 'test, document'
        mock_doc.core_properties.created = Mock()
        mock_doc.core_properties.created.isoformat.return_value = '2024-01-01T12:00:00'
        mock_doc.core_properties.modified = Mock()
        mock_doc.core_properties.modified.isoformat.return_value = '2024-01-01T12:00:00'
        mock_doc.core_properties.last_modified_by = 'Test User'
        mock_doc.paragraphs = [Mock() for _ in range(3)]
        mock_doc.paragraphs[0].text = "First paragraph"
        mock_doc.paragraphs[1].text = "Second paragraph"
        mock_doc.paragraphs[2].text = "Third paragraph"
        mock_doc.tables = []
        mock_doc.sections = [Mock()]
        
        with patch('docx.Document', return_value=mock_doc):
            result = extractor._extract_docx_metadata(test_file)
            
            assert result is not None
            assert result['metadata']['title'] == 'Test Document'
            assert result['metadata']['author'] == 'Test Author'
            assert result['document_info']['paragraph_count'] == 3
            assert result['content_info']['word_count'] > 0

    def test_extract_xlsx_metadata(self, extractor):
        """Test XLSX metadata extraction"""
        test_file = "/test/document.xlsx"
        
        # Mock openpyxl
        mock_workbook = Mock()
        mock_workbook.properties.title = 'Test Spreadsheet'
        mock_workbook.properties.creator = 'Test Creator'
        mock_workbook.properties.created = Mock()
        mock_workbook.properties.created.isoformat.return_value = '2024-01-01T12:00:00'
        mock_workbook.sheetnames = ['Sheet1', 'Sheet2']
        mock_workbook.worksheets = [Mock(), Mock()]
        mock_workbook.worksheets[0].max_row = 100
        mock_workbook.worksheets[0].max_column = 10
        mock_workbook.close = Mock()
        
        with patch('openpyxl.load_workbook', return_value=mock_workbook):
            result = extractor._extract_xlsx_metadata(test_file)
            
            assert result is not None
            assert result['metadata']['title'] == 'Test Spreadsheet'
            assert result['metadata']['creator'] == 'Test Creator'
            assert result['document_info']['sheet_count'] == 2
            assert result['content_info']['max_row'] == 100
            assert result['content_info']['max_column'] == 10

    def test_extract_text_metadata(self, extractor):
        """Test text file metadata extraction"""
        test_file = "/test/document.txt"
        
        mock_content = "First line\nSecond line\n\nThird line after empty line\nFourth line"
        
        with patch('builtins.open', mock_open(read_data=mock_content)):
            result = extractor._extract_text_metadata(test_file)
            
            assert result is not None
            assert result['content_info']['line_count'] == 5
            assert result['content_info']['word_count'] > 0
            assert result['content_info']['character_count'] > 0
            assert result['content_info']['first_line'] == 'First line'
            assert result['content_info']['last_line'] == 'Fourth line'
            assert result['document_info']['file_type'] == 'text'

    def test_extract_markup_metadata(self, extractor):
        """Test HTML/XML metadata extraction"""
        test_file = "/test/document.html"
        
        mock_html = """
        <html>
        <head>
            <title>Test Page</title>
            <meta name="author" content="Test Author">
            <meta name="description" content="Test Description">
            <meta name="keywords" content="test, html, document">
        </head>
        <body>
            <h1>Test Heading</h1>
            <p>Test paragraph content.</p>
            <div>Test div content.</div>
        </body>
        </html>
        """
        
        with patch('builtins.open', mock_open(read_data=mock_html)):
            result = extractor._extract_markup_metadata(test_file)
            
            assert result is not None
            assert result['metadata']['title'] == 'Test Page'
            assert result['metadata']['author'] == 'Test Author'
            assert result['metadata']['description'] == 'Test Description'
            assert result['content_info']['word_count'] > 0
            assert result['content_info']['tag_count'] > 0

    def test_process_metadata(self, extractor):
        """Test metadata processing and mapping"""
        raw_metadata = {
            'pdf': {
                'metadata': {
                    'title': 'Test Document',
                    'author': 'Test Author',
                    'creationdate': '2024-01-01T12:00:00',
                    'moddate': '2024-01-01T12:00:00'
                }
            },
            'office': {
                'metadata': {
                    'subject': 'Test Subject',
                    'keywords': 'test, document'
                }
            }
        }
        
        result = extractor._process_metadata(raw_metadata)
        
        # Check that metadata was processed and mapped correctly
        assert result['title'] == 'Test Document'
        assert result['author'] == 'Test Author'
        assert result['subject'] == 'Test Subject'
        assert result['keywords'] == 'test, document'
        assert result['creation_date'] == '2024-01-01T12:00:00'
        assert result['modification_date'] == '2024-01-01T12:00:00'

    def test_extract_document_info(self, extractor):
        """Test document information extraction"""
        raw_metadata = {
            'pdf': {
                'document_info': {
                    'page_count': 10
                }
            },
            'office': {
                'document_info': {
                    'slide_count': 5
                }
            }
        }
        
        result = extractor._extract_document_info(raw_metadata)
        
        assert result['page_count'] == 10
        assert result['slide_count'] == 5

    def test_extract_content_info(self, extractor):
        """Test content information extraction"""
        raw_metadata = {
            'pdf': {
                'content_info': {
                    'estimated_word_count': 1000
                }
            },
            'text': {
                'content_info': {
                    'line_count': 50,
                    'character_count': 5000
                }
            }
        }
        
        result = extractor._extract_content_info(raw_metadata)
        
        assert result['estimated_word_count'] == 1000
        assert result['line_count'] == 50
        assert result['character_count'] == 5000

    def test_extract_security_info(self, extractor):
        """Test security information extraction"""
        raw_metadata = {
            'pdf': {
                'is_encrypted': True,
                'security': {
                    'password_protected': True
                }
            }
        }
        
        result = extractor._extract_security_info(raw_metadata)
        
        assert result['encrypted'] == True
        assert result['password_protected'] == True

    def test_extract_metadata_sync_with_different_formats(self, extractor):
        """Test sync extraction with different file formats"""
        
        # Test PDF
        pdf_file = "/test/document.pdf"
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1024000), \
             patch.object(extractor, '_extract_pdf_metadata', return_value={'page_count': 10}):
            
            result = extractor._extract_metadata_sync(pdf_file)
            
            assert isinstance(result, dict)
            assert 'file_info' in result
            assert 'raw_metadata' in result
            assert 'pdf' in result['raw_metadata']
        
        # Test DOCX
        docx_file = "/test/document.docx"
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=512000), \
             patch.object(extractor, '_extract_office_metadata', return_value={'metadata': {'title': 'Test'}}):
            
            result = extractor._extract_metadata_sync(docx_file)
            
            assert isinstance(result, dict)
            assert 'raw_metadata' in result
            assert 'office' in result['raw_metadata']
        
        # Test TXT
        txt_file = "/test/document.txt"
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1024), \
             patch.object(extractor, '_extract_text_metadata', return_value={'content_info': {'line_count': 10}}):
            
            result = extractor._extract_metadata_sync(txt_file)
            
            assert isinstance(result, dict)
            assert 'raw_metadata' in result
            assert 'text' in result['raw_metadata']

    def test_library_import_failures(self, extractor):
        """Test handling of missing library imports"""
        test_file = "/test/document.pdf"
        
        # Test PDF extraction with missing PyPDF2
        with patch('PyPDF2.PdfReader', side_effect=ImportError("PyPDF2 not available")):
            result = extractor._extract_pdf_metadata(test_file)
            assert result is None
        
        # Test DOCX extraction with missing docx
        with patch('docx.Document', side_effect=ImportError("docx not available")):
            result = extractor._extract_docx_metadata(test_file)
            assert result is None
        
        # Test markup extraction with missing BeautifulSoup
        with patch('bs4.BeautifulSoup', side_effect=ImportError("BeautifulSoup not available")):
            result = extractor._extract_markup_metadata(test_file)
            assert result is None

    def test_extract_generic_metadata(self, extractor):
        """Test generic metadata extraction"""
        test_file = "/test/document.unknown"
        
        mock_stat = Mock()
        mock_stat.st_size = 1024
        mock_stat.st_ctime = 1640995200  # 2022-01-01 00:00:00
        mock_stat.st_mtime = 1640995200
        mock_stat.st_atime = 1640995200
        mock_stat.st_mode = 0o644
        mock_stat.st_uid = 1000
        mock_stat.st_gid = 1000
        
        with patch('os.stat', return_value=mock_stat):
            result = extractor._extract_generic_metadata(test_file)
            
            assert result is not None
            assert result['file_info']['size'] == 1024
            assert 'created' in result['file_info']
            assert 'modified' in result['file_info']
            assert 'accessed' in result['file_info']


def mock_open(read_data=''):
    """Helper function to create a mock file open context"""
    mock_file = MagicMock()
    mock_file.read.return_value = read_data
    mock_file.__enter__.return_value = mock_file
    return mock_file