"""XML parsing utilities for MOS messages"""

import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import re
from lxml import etree
from ..models.schemas import MOSMessageType, MOSStatus, MOSAirStatus


class MOSXMLParser:
    """Parser for MOS XML messages"""
    
    def __init__(self):
        self.namespace_map = {
            'mos': 'http://www.mosprotocol.com/mos',
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/'
        }
    
    def parse_message(self, xml_content: str) -> Dict[str, Any]:
        """Parse MOS XML message and extract structured data"""
        try:
            # Clean and normalize XML
            xml_content = self._clean_xml(xml_content)
            
            # Parse XML
            root = etree.fromstring(xml_content.encode('utf-8'))
            
            # Determine message type
            message_type = self._get_message_type(root)
            
            # Parse based on message type
            if message_type == MOSMessageType.MOS_OBJ:
                return self._parse_mos_obj(root)
            elif message_type == MOSMessageType.MOS_LIST_ALL:
                return self._parse_mos_list_all(root)
            elif message_type == MOSMessageType.MOS_ACK:
                return self._parse_mos_ack(root)
            elif message_type == MOSMessageType.MOS_HEARTBEAT:
                return self._parse_heartbeat(root)
            elif message_type == MOSMessageType.MOS_MACHINE_INFO:
                return self._parse_machine_info(root)
            elif message_type.startswith('ro'):
                return self._parse_running_order_message(root, message_type)
            else:
                return self._parse_generic_message(root, message_type)
                
        except Exception as e:
            raise ValueError(f"Failed to parse MOS XML: {str(e)}")
    
    def _clean_xml(self, xml_content: str) -> str:
        """Clean and normalize XML content"""
        # Remove BOM if present
        xml_content = xml_content.lstrip('\ufeff')
        
        # Remove XML declaration if malformed
        xml_content = re.sub(r'<\?xml[^>]*\?>', '', xml_content)
        
        # Ensure proper encoding
        if not xml_content.strip().startswith('<?xml'):
            xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_content
        
        return xml_content
    
    def _get_message_type(self, root: etree.Element) -> str:
        """Determine MOS message type from XML root"""
        tag_name = etree.QName(root).localname
        
        # Handle SOAP envelope
        if tag_name == 'Envelope':
            body = root.find('.//soap:Body', self.namespace_map)
            if body is not None and len(body) > 0:
                tag_name = etree.QName(body[0]).localname
        
        return tag_name
    
    def _parse_mos_obj(self, root: etree.Element) -> Dict[str, Any]:
        """Parse mosObj message"""
        obj_data = {
            'message_type': MOSMessageType.MOS_OBJ,
            'obj_id': self._get_text(root, './/objID'),
            'obj_slug': self._get_text(root, './/objSlug'),
            'obj_type': self._get_text(root, './/objType'),
            'obj_tb': self._get_int(root, './/objTB', 25),
            'obj_rev': self._get_int(root, './/objRev', 1),
            'obj_dur': self._get_int(root, './/objDur'),
            'status': self._get_text(root, './/status', 'NEW'),
            'obj_air': self._get_text(root, './/objAir'),
            'obj_abstract': self._get_text(root, './/mosAbstract'),
            'obj_group': self._get_text(root, './/objGroup'),
            'created_by': self._get_text(root, './/createdBy'),
            'created': self._get_datetime(root, './/created'),
            'changed_by': self._get_text(root, './/changedBy'),
            'changed': self._get_datetime(root, './/changed'),
            'description': self._get_text(root, './/description')
        }
        
        # Parse objPaths
        obj_paths = []
        for path_elem in root.findall('.//objPaths/objPath'):
            path_data = {
                'media_type': self._get_text(path_elem, './/@Type'),
                'description': self._get_text(path_elem, './/Description'),
                'target': self._get_text(path_elem, './/Target')
            }
            obj_paths.append(path_data)
        obj_data['obj_paths'] = obj_paths
        
        # Parse external metadata
        metadata_elem = root.find('.//mosExternalMetadata')
        if metadata_elem is not None:
            obj_data['external_metadata'] = self._element_to_dict(metadata_elem)
        
        return obj_data
    
    def _parse_mos_list_all(self, root: etree.Element) -> Dict[str, Any]:
        """Parse mosListAll message"""
        objects = []
        for obj_elem in root.findall('.//mosObj'):
            obj_data = self._parse_mos_obj(obj_elem)
            objects.append(obj_data)
        
        return {
            'message_type': MOSMessageType.MOS_LIST_ALL,
            'objects': objects
        }
    
    def _parse_mos_ack(self, root: etree.Element) -> Dict[str, Any]:
        """Parse mosAck message"""
        return {
            'message_type': MOSMessageType.MOS_ACK,
            'message_id': self._get_text(root, './/messageID'),
            'status': self._get_text(root, './/status'),
            'status_description': self._get_text(root, './/statusDescription')
        }
    
    def _parse_heartbeat(self, root: etree.Element) -> Dict[str, Any]:
        """Parse heartbeat message"""
        return {
            'message_type': MOSMessageType.MOS_HEARTBEAT,
            'mos_id': self._get_text(root, './/mosID'),
            'nrcs_id': self._get_text(root, './/nrcsID'),
            'time': self._get_datetime(root, './/time'),
            'status': self._get_text(root, './/status', 'OK')
        }
    
    def _parse_machine_info(self, root: etree.Element) -> Dict[str, Any]:
        """Parse machine info message"""
        return {
            'message_type': MOSMessageType.MOS_MACHINE_INFO,
            'manufacturer': self._get_text(root, './/manufacturer'),
            'model': self._get_text(root, './/model'),
            'hw_rev': self._get_text(root, './/hwRev'),
            'sw_rev': self._get_text(root, './/swRev'),
            'dom': self._get_datetime(root, './/DOM'),
            'sn': self._get_text(root, './/SN'),
            'id': self._get_text(root, './/ID'),
            'time': self._get_datetime(root, './/time'),
            'op_time': self._get_text(root, './/opTime'),
            'mos_rev': self._get_text(root, './/mosRev', '2.8.5'),
            'supported_profiles': self._get_list(root, './/supportedProfiles/profile'),
            'default_active_x': self._get_text(root, './/defaultActiveX')
        }
    
    def _parse_running_order_message(self, root: etree.Element, message_type: str) -> Dict[str, Any]:
        """Parse running order related messages"""
        base_data = {
            'message_type': message_type,
            'ro_id': self._get_text(root, './/roID'),
            'ro_slug': self._get_text(root, './/roSlug')
        }
        
        # Add specific fields based on message type
        if message_type in [MOSMessageType.RO_CREATE, MOSMessageType.RO_REPLACE]:
            base_data.update({
                'ro_edition_id': self._get_text(root, './/roEditionID'),
                'ro_title': self._get_text(root, './/roTitle'),
                'ro_start_time': self._get_datetime(root, './/roStartTime'),
                'ro_end_time': self._get_datetime(root, './/roEndTime'),
                'ro_duration': self._get_int(root, './/roDur')
            })
            
            # Parse stories
            stories = []
            for story_elem in root.findall('.//story'):
                story_data = self._parse_story(story_elem)
                stories.append(story_data)
            base_data['stories'] = stories
        
        return base_data
    
    def _parse_story(self, story_elem: etree.Element) -> Dict[str, Any]:
        """Parse story element"""
        story_data = {
            'story_id': self._get_text(story_elem, './/storyID'),
            'story_slug': self._get_text(story_elem, './/storySlug'),
            'story_num': self._get_int(story_elem, './/storyNum'),
            'story_body': self._get_text(story_elem, './/storyBody')
        }
        
        # Parse items
        items = []
        for item_elem in story_elem.findall('.//item'):
            item_data = {
                'item_id': self._get_text(item_elem, './/itemID'),
                'item_slug': self._get_text(item_elem, './/itemSlug'),
                'item_channel': self._get_text(item_elem, './/itemChannel'),
                'obj_id': self._get_text(item_elem, './/objID'),
                'mos_abstract': self._get_text(item_elem, './/mosAbstract'),
                'item_duration': self._get_int(item_elem, './/itemDur'),
                'item_in_point': self._get_int(item_elem, './/itemInPoint'),
                'item_out_point': self._get_int(item_elem, './/itemOutPoint')
            }
            items.append(item_data)
        story_data['items'] = items
        
        return story_data
    
    def _parse_generic_message(self, root: etree.Element, message_type: str) -> Dict[str, Any]:
        """Parse generic message structure"""
        return {
            'message_type': message_type,
            'data': self._element_to_dict(root)
        }
    
    def _get_text(self, root: etree.Element, xpath: str, default: Optional[str] = None) -> Optional[str]:
        """Get text content from XPath"""
        elem = root.find(xpath)
        if elem is not None and elem.text:
            return elem.text.strip()
        return default
    
    def _get_int(self, root: etree.Element, xpath: str, default: Optional[int] = None) -> Optional[int]:
        """Get integer value from XPath"""
        text = self._get_text(root, xpath)
        if text:
            try:
                return int(text)
            except ValueError:
                pass
        return default
    
    def _get_datetime(self, root: etree.Element, xpath: str) -> Optional[datetime]:
        """Get datetime value from XPath"""
        text = self._get_text(root, xpath)
        if text:
            try:
                # Try different datetime formats
                for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d %H:%M:%S']:
                    try:
                        return datetime.strptime(text, fmt)
                    except ValueError:
                        continue
            except ValueError:
                pass
        return None
    
    def _get_list(self, root: etree.Element, xpath: str) -> List[str]:
        """Get list of text values from XPath"""
        elements = root.findall(xpath)
        return [elem.text.strip() for elem in elements if elem.text]
    
    def _element_to_dict(self, element: etree.Element) -> Dict[str, Any]:
        """Convert XML element to dictionary"""
        result = {}
        
        # Add attributes
        if element.attrib:
            result.update(element.attrib)
        
        # Add text content
        if element.text and element.text.strip():
            if len(element) == 0:  # No children, just text
                return element.text.strip()
            result['text'] = element.text.strip()
        
        # Add children
        for child in element:
            child_data = self._element_to_dict(child)
            tag = etree.QName(child).localname
            
            if tag in result:
                # Multiple elements with same tag - convert to list
                if not isinstance(result[tag], list):
                    result[tag] = [result[tag]]
                result[tag].append(child_data)
            else:
                result[tag] = child_data
        
        return result


class MOSXMLGenerator:
    """Generator for MOS XML messages"""
    
    def __init__(self):
        self.mos_namespace = "http://www.mosprotocol.com/mos"
        self.soap_namespace = "http://schemas.xmlsoap.org/soap/envelope/"
    
    def generate_mos_ack(self, message_id: str, status: str, 
                        status_description: Optional[str] = None) -> str:
        """Generate mosAck XML message"""
        root = ET.Element("mosAck")
        
        ET.SubElement(root, "messageID").text = message_id
        ET.SubElement(root, "status").text = status
        
        if status_description:
            ET.SubElement(root, "statusDescription").text = status_description
        
        return self._to_xml_string(root)
    
    def generate_heartbeat(self, mos_id: str, nrcs_id: str) -> str:
        """Generate heartbeat XML message"""
        root = ET.Element("heartbeat")
        
        ET.SubElement(root, "mosID").text = mos_id
        ET.SubElement(root, "nrcsID").text = nrcs_id
        ET.SubElement(root, "time").text = datetime.utcnow().isoformat()
        ET.SubElement(root, "status").text = "OK"
        
        return self._to_xml_string(root)
    
    def generate_mos_obj(self, obj_data: Dict[str, Any]) -> str:
        """Generate mosObj XML message"""
        root = ET.Element("mosObj")
        
        # Required fields
        ET.SubElement(root, "objID").text = obj_data["obj_id"]
        ET.SubElement(root, "objSlug").text = obj_data["obj_slug"]
        ET.SubElement(root, "objType").text = obj_data["obj_type"]
        ET.SubElement(root, "objTB").text = str(obj_data.get("obj_tb", 25))
        ET.SubElement(root, "objRev").text = str(obj_data.get("obj_rev", 1))
        ET.SubElement(root, "status").text = obj_data.get("status", "NEW")
        
        # Optional fields
        if obj_data.get("obj_dur"):
            ET.SubElement(root, "objDur").text = str(obj_data["obj_dur"])
        
        if obj_data.get("obj_air"):
            ET.SubElement(root, "objAir").text = obj_data["obj_air"]
        
        if obj_data.get("obj_abstract"):
            ET.SubElement(root, "mosAbstract").text = obj_data["obj_abstract"]
        
        if obj_data.get("obj_group"):
            ET.SubElement(root, "objGroup").text = obj_data["obj_group"]
        
        # Object paths
        if obj_data.get("obj_paths"):
            paths_elem = ET.SubElement(root, "objPaths")
            for path in obj_data["obj_paths"]:
                path_elem = ET.SubElement(paths_elem, "objPath")
                path_elem.set("Type", path["media_type"])
                if path.get("description"):
                    ET.SubElement(path_elem, "Description").text = path["description"]
                ET.SubElement(path_elem, "Target").text = path["target"]
        
        # Creator information
        if obj_data.get("created_by"):
            ET.SubElement(root, "createdBy").text = obj_data["created_by"]
        
        if obj_data.get("created"):
            ET.SubElement(root, "created").text = obj_data["created"].isoformat()
        
        if obj_data.get("changed_by"):
            ET.SubElement(root, "changedBy").text = obj_data["changed_by"]
        
        if obj_data.get("changed"):
            ET.SubElement(root, "changed").text = obj_data["changed"].isoformat()
        
        if obj_data.get("description"):
            ET.SubElement(root, "description").text = obj_data["description"]
        
        # External metadata
        if obj_data.get("external_metadata"):
            metadata_elem = ET.SubElement(root, "mosExternalMetadata")
            self._dict_to_element(obj_data["external_metadata"], metadata_elem)
        
        return self._to_xml_string(root)
    
    def generate_running_order(self, ro_data: Dict[str, Any], message_type: str = "roCreate") -> str:
        """Generate running order XML message"""
        root = ET.Element(message_type)
        
        # Running order header
        ET.SubElement(root, "roID").text = ro_data["ro_id"]
        ET.SubElement(root, "roSlug").text = ro_data["ro_slug"]
        
        if ro_data.get("ro_edition_id"):
            ET.SubElement(root, "roEditionID").text = ro_data["ro_edition_id"]
        
        if ro_data.get("ro_title"):
            ET.SubElement(root, "roTitle").text = ro_data["ro_title"]
        
        if ro_data.get("ro_start_time"):
            ET.SubElement(root, "roStartTime").text = ro_data["ro_start_time"].isoformat()
        
        if ro_data.get("ro_end_time"):
            ET.SubElement(root, "roEndTime").text = ro_data["ro_end_time"].isoformat()
        
        if ro_data.get("ro_duration"):
            ET.SubElement(root, "roDur").text = str(ro_data["ro_duration"])
        
        # Stories
        if ro_data.get("stories"):
            for story in ro_data["stories"]:
                story_elem = ET.SubElement(root, "story")
                self._add_story_elements(story_elem, story)
        
        return self._to_xml_string(root)
    
    def _add_story_elements(self, story_elem: ET.Element, story_data: Dict[str, Any]):
        """Add story elements to XML"""
        ET.SubElement(story_elem, "storyID").text = story_data["story_id"]
        ET.SubElement(story_elem, "storySlug").text = story_data["story_slug"]
        
        if story_data.get("story_num"):
            ET.SubElement(story_elem, "storyNum").text = str(story_data["story_num"])
        
        if story_data.get("story_body"):
            ET.SubElement(story_elem, "storyBody").text = story_data["story_body"]
        
        # Items
        if story_data.get("items"):
            for item in story_data["items"]:
                item_elem = ET.SubElement(story_elem, "item")
                ET.SubElement(item_elem, "itemID").text = item["item_id"]
                
                if item.get("item_slug"):
                    ET.SubElement(item_elem, "itemSlug").text = item["item_slug"]
                
                if item.get("item_channel"):
                    ET.SubElement(item_elem, "itemChannel").text = item["item_channel"]
                
                if item.get("obj_id"):
                    ET.SubElement(item_elem, "objID").text = item["obj_id"]
                
                if item.get("mos_abstract"):
                    ET.SubElement(item_elem, "mosAbstract").text = item["mos_abstract"]
    
    def _dict_to_element(self, data: Dict[str, Any], parent: ET.Element):
        """Convert dictionary to XML elements"""
        for key, value in data.items():
            if isinstance(value, dict):
                child = ET.SubElement(parent, key)
                self._dict_to_element(value, child)
            elif isinstance(value, list):
                for item in value:
                    child = ET.SubElement(parent, key)
                    if isinstance(item, dict):
                        self._dict_to_element(item, child)
                    else:
                        child.text = str(item)
            else:
                child = ET.SubElement(parent, key)
                child.text = str(value)
    
    def _to_xml_string(self, element: ET.Element) -> str:
        """Convert element to XML string"""
        ET.register_namespace("", self.mos_namespace)
        xml_str = ET.tostring(element, encoding='unicode')
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'