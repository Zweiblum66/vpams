"""Tests for XML parser"""

import pytest
from datetime import datetime

from src.utils.xml_parser import MOSXMLParser, MOSXMLGenerator
from src.models.schemas import MOSMessageType


class TestMOSXMLParser:
    """Test MOS XML parser"""
    
    def test_parse_mos_obj(self, sample_mos_obj_xml):
        """Test parsing mosObj message"""
        parser = MOSXMLParser()
        result = parser.parse_message(sample_mos_obj_xml)
        
        assert result['message_type'] == MOSMessageType.MOS_OBJ
        assert result['obj_id'] == 'test_obj_001'
        assert result['obj_slug'] == 'Test Video Clip'
        assert result['obj_type'] == 'video'
        assert result['obj_tb'] == 25
        assert result['obj_rev'] == 1
        assert result['obj_dur'] == 1500
        assert result['status'] == 'NEW'
        assert result['obj_air'] == 'READY'
        assert result['obj_abstract'] == 'Test video clip for news story'
        assert result['obj_group'] == 'news'
        assert result['created_by'] == 'test_user'
        assert result['description'] == 'Test video clip for unit testing'
        
        # Test object paths
        assert len(result['obj_paths']) == 2
        assert result['obj_paths'][0]['media_type'] == 'video'
        assert result['obj_paths'][0]['description'] == 'High quality video'
        assert result['obj_paths'][0]['target'] == 'file:///storage/video/test_clip.mp4'
    
    def test_parse_running_order(self, sample_running_order_xml):
        """Test parsing running order message"""
        parser = MOSXMLParser()
        result = parser.parse_message(sample_running_order_xml)
        
        assert result['message_type'] == MOSMessageType.RO_CREATE
        assert result['ro_id'] == 'RO_20240115_1800'
        assert result['ro_slug'] == 'Evening News'
        assert result['ro_edition_id'] == 'MAIN'
        assert result['ro_title'] == 'Evening News - January 15, 2024'
        assert result['ro_duration'] == 1800
        
        # Test stories
        assert len(result['stories']) == 1
        story = result['stories'][0]
        assert story['story_id'] == 'STORY_001'
        assert story['story_slug'] == 'Breaking News'
        assert story['story_num'] == 1
        assert story['story_body'] == 'Breaking news story about local events'
        
        # Test items
        assert len(story['items']) == 1
        item = story['items'][0]
        assert item['item_id'] == 'ITEM_001'
        assert item['item_slug'] == 'News Clip'
        assert item['item_channel'] == 'V1'
        assert item['obj_id'] == 'test_obj_001'
        assert item['item_duration'] == 120
    
    def test_parse_heartbeat(self, sample_heartbeat_xml):
        """Test parsing heartbeat message"""
        parser = MOSXMLParser()
        result = parser.parse_message(sample_heartbeat_xml)
        
        assert result['message_type'] == MOSMessageType.MOS_HEARTBEAT
        assert result['mos_id'] == 'test_mos_server'
        assert result['nrcs_id'] == 'test_nrcs_client'
        assert result['status'] == 'OK'
        assert isinstance(result['time'], datetime)
    
    def test_parse_mos_ack(self, sample_mos_ack_xml):
        """Test parsing MOS ACK message"""
        parser = MOSXMLParser()
        result = parser.parse_message(sample_mos_ack_xml)
        
        assert result['message_type'] == MOSMessageType.MOS_ACK
        assert result['message_id'] == 'test_message_001'
        assert result['status'] == 'ACK'
        assert result['status_description'] == 'Message processed successfully'
    
    def test_parse_invalid_xml(self):
        """Test parsing invalid XML"""
        parser = MOSXMLParser()
        
        with pytest.raises(ValueError):
            parser.parse_message("<invalid><xml")
    
    def test_parse_empty_message(self):
        """Test parsing empty message"""
        parser = MOSXMLParser()
        
        with pytest.raises(ValueError):
            parser.parse_message("")


class TestMOSXMLGenerator:
    """Test MOS XML generator"""
    
    def test_generate_mos_ack(self):
        """Test generating MOS ACK message"""
        generator = MOSXMLGenerator()
        xml = generator.generate_mos_ack(
            message_id="test_123",
            status="ACK",
            status_description="Success"
        )
        
        assert "test_123" in xml
        assert "<status>ACK</status>" in xml
        assert "Success" in xml
        assert xml.startswith("<?xml")
    
    def test_generate_heartbeat(self):
        """Test generating heartbeat message"""
        generator = MOSXMLGenerator()
        xml = generator.generate_heartbeat(
            mos_id="mos_server",
            nrcs_id="nrcs_client"
        )
        
        assert "mos_server" in xml
        assert "nrcs_client" in xml
        assert "<status>OK</status>" in xml
        assert xml.startswith("<?xml")
    
    def test_generate_mos_obj(self):
        """Test generating MOS object message"""
        generator = MOSXMLGenerator()
        
        obj_data = {
            'obj_id': 'test_obj_001',
            'obj_slug': 'Test Video',
            'obj_type': 'video',
            'obj_tb': 25,
            'obj_rev': 1,
            'obj_dur': 1500,
            'status': 'NEW',
            'obj_air': 'READY',
            'obj_abstract': 'Test video clip',
            'obj_group': 'news',
            'obj_paths': [
                {
                    'media_type': 'video',
                    'description': 'High quality',
                    'target': 'file:///test.mp4'
                }
            ],
            'created_by': 'test_user',
            'description': 'Test description'
        }
        
        xml = generator.generate_mos_obj(obj_data)
        
        assert "test_obj_001" in xml
        assert "Test Video" in xml
        assert "<objType>video</objType>" in xml
        assert "<objTB>25</objTB>" in xml
        assert "<status>NEW</status>" in xml
        assert "file:///test.mp4" in xml
        assert xml.startswith("<?xml")
    
    def test_generate_running_order(self):
        """Test generating running order message"""
        generator = MOSXMLGenerator()
        
        ro_data = {
            'ro_id': 'RO_001',
            'ro_slug': 'Test RO',
            'ro_title': 'Test Running Order',
            'ro_duration': 1800,
            'stories': [
                {
                    'story_id': 'STORY_001',
                    'story_slug': 'Test Story',
                    'story_num': 1,
                    'story_body': 'Test story content',
                    'items': [
                        {
                            'item_id': 'ITEM_001',
                            'item_slug': 'Test Item',
                            'obj_id': 'test_obj_001'
                        }
                    ]
                }
            ]
        }
        
        xml = generator.generate_running_order(ro_data)
        
        assert "RO_001" in xml
        assert "Test RO" in xml
        assert "STORY_001" in xml
        assert "test_obj_001" in xml
        assert xml.startswith("<?xml")