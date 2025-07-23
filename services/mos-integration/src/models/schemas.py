"""Pydantic schemas for MOS Integration Service"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


# Enums for MOS protocol
class MOSMessageType(str, Enum):
    """MOS message types"""
    # Connection messages
    MOS_ACK = "mosAck"
    MOS_HEARTBEAT = "heartbeat"
    MOS_LIST_MACHINE_INFO = "mosListMachineInfo"
    MOS_MACHINE_INFO = "mosMachineInfo"
    
    # Object messages
    MOS_OBJ = "mosObj"
    MOS_OBJ_CREATE = "mosObjCreate"
    MOS_LIST_ALL = "mosListAll"
    MOS_REQ_OBJ = "mosReqObj"
    MOS_REQ_ALL = "mosReqAll"
    
    # Running order messages
    RO_ACK = "roAck"
    RO_CREATE = "roCreate"
    RO_REPLACE = "roReplace"
    RO_DELETE = "roDelete"
    RO_METADATA_REPLACE = "roMetadataReplace"
    RO_LIST_ALL = "roListAll"
    RO_REQ_ALL = "roReqAll"
    RO_STORY_APPEND = "roStoryAppend"
    RO_STORY_INSERT = "roStoryInsert"
    RO_STORY_REPLACE = "roStoryReplace"
    RO_STORY_MOVE = "roStoryMove"
    RO_STORY_SWAP = "roStorySwap"
    RO_STORY_DELETE = "roStoryDelete"
    RO_ITEM_REPLACE = "roItemReplace"
    RO_ITEM_MOVE = "roItemMove"
    RO_ITEM_DELETE = "roItemDelete"
    RO_READY_TO_AIR = "roReadyToAir"
    RO_STORY_SEND = "roStorySend"


class MOSStatus(str, Enum):
    """MOS object/story status"""
    NEW = "NEW"
    UPDATED = "UPDATED"
    MOVED = "MOVED"
    BUSY = "BUSY"
    UNKNOWN = "UNKNOWN"
    READY = "READY"
    NOT_READY = "NOT_READY"


class MOSAirStatus(str, Enum):
    """MOS air status"""
    READY = "READY"
    NOT_READY = "NOT_READY"
    MANUAL_CTRL = "MANUAL_CTRL"


class ConnectionStatus(str, Enum):
    """Connection status"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    ERROR = "error"


# Base schemas
class MOSPath(BaseModel):
    """MOS object file path"""
    media_type: str = Field(..., alias="Type")
    description: Optional[str] = Field(None, alias="Description")
    target: str = Field(..., alias="Target")
    
    class Config:
        allow_population_by_field_name = True


class MOSTime(BaseModel):
    """MOS time representation"""
    time_base: int = Field(25, description="Time base (frames per second)")
    time_code: str = Field(..., description="Timecode in HH:MM:SS:FF format")
    
    @validator("time_code")
    def validate_timecode(cls, v):
        import re
        if not re.match(r"^\d{2}:\d{2}:\d{2}:\d{2}$", v):
            raise ValueError("Timecode must be in HH:MM:SS:FF format")
        return v


# MOS Object schemas
class MOSObjectBase(BaseModel):
    """Base MOS object schema"""
    obj_id: str = Field(..., alias="objID")
    obj_slug: str = Field(..., alias="objSlug")
    obj_type: str = Field(..., alias="objType")
    obj_tb: int = Field(25, alias="objTB", description="Time base")
    obj_rev: int = Field(1, alias="objRev", description="Revision")
    obj_dur: Optional[int] = Field(None, alias="objDur", description="Duration")
    status: MOSStatus = Field(MOSStatus.NEW)
    obj_air: Optional[MOSAirStatus] = Field(None, alias="objAir")
    obj_abstract: Optional[str] = Field(None, alias="mosAbstract")
    obj_group: Optional[str] = Field(None, alias="objGroup")
    obj_paths: Optional[List[MOSPath]] = Field(None, alias="objPaths")
    created_by: Optional[str] = Field(None, alias="createdBy")
    created: Optional[datetime] = Field(None)
    changed_by: Optional[str] = Field(None, alias="changedBy")
    changed: Optional[datetime] = Field(None)
    description: Optional[str] = Field(None)
    external_metadata: Optional[Dict[str, Any]] = Field(None, alias="mosExternalMetadata")
    
    class Config:
        allow_population_by_field_name = True


class MOSObjectCreate(MOSObjectBase):
    """Schema for creating MOS objects"""
    pass


class MOSObjectResponse(MOSObjectBase):
    """Schema for MOS object responses"""
    id: str
    connection_id: str
    created_at: datetime
    updated_at: datetime


# MOS Story schemas
class MOSStoryItemBase(BaseModel):
    """Base MOS story item schema"""
    item_id: str = Field(..., alias="itemID")
    item_slug: Optional[str] = Field(None, alias="itemSlug")
    item_channel: Optional[str] = Field(None, alias="itemChannel")
    obj_id: Optional[str] = Field(None, alias="objID")
    mos_abstract: Optional[str] = Field(None, alias="mosAbstract")
    item_duration: Optional[int] = Field(None, alias="itemDur")
    item_in_point: Optional[int] = Field(None, alias="itemInPoint")
    item_out_point: Optional[int] = Field(None, alias="itemOutPoint")
    
    class Config:
        allow_population_by_field_name = True


class MOSStoryBase(BaseModel):
    """Base MOS story schema"""
    story_id: str = Field(..., alias="storyID")
    story_slug: str = Field(..., alias="storySlug")
    story_num: Optional[int] = Field(None, alias="storyNum")
    story_body: Optional[str] = Field(None, alias="storyBody")
    items: Optional[List[MOSStoryItemBase]] = Field(None)
    
    class Config:
        allow_population_by_field_name = True


# MOS Running Order schemas
class MOSRunningOrderBase(BaseModel):
    """Base MOS running order schema"""
    ro_id: str = Field(..., alias="roID")
    ro_slug: str = Field(..., alias="roSlug")
    ro_edition_id: Optional[str] = Field(None, alias="roEditionID")
    ro_title: Optional[str] = Field(None, alias="roTitle")
    ro_start_time: Optional[datetime] = Field(None, alias="roStartTime")
    ro_end_time: Optional[datetime] = Field(None, alias="roEndTime")
    ro_duration: Optional[int] = Field(None, alias="roDur")
    stories: Optional[List[MOSStoryBase]] = Field(None)
    
    class Config:
        allow_population_by_field_name = True


class MOSRunningOrderCreate(MOSRunningOrderBase):
    """Schema for creating running orders"""
    pass


class MOSRunningOrderResponse(MOSRunningOrderBase):
    """Schema for running order responses"""
    id: str
    connection_id: str
    status: str
    ready_to_air: bool
    created_at: datetime
    updated_at: datetime


# MOS Message schemas
class MOSAck(BaseModel):
    """MOS acknowledgment message"""
    message_id: str = Field(..., alias="messageID")
    status: str = Field(..., description="ACK or NACK")
    status_description: Optional[str] = Field(None, alias="statusDescription")
    
    class Config:
        allow_population_by_field_name = True


class MOSHeartbeatMessage(BaseModel):
    """MOS heartbeat message"""
    mos_id: str = Field(..., alias="mosID")
    nrcs_id: str = Field(..., alias="nrcsID")
    heartbeat_time: datetime = Field(..., alias="time")
    status: str = "OK"
    
    class Config:
        allow_population_by_field_name = True


class MOSMachineInfo(BaseModel):
    """MOS machine information"""
    manufacturer: str
    model: str
    hw_rev: str = Field(..., alias="hwRev")
    sw_rev: str = Field(..., alias="swRev")
    dom: datetime = Field(..., alias="DOM", description="Date of manufacture")
    sn: str = Field(..., alias="SN", description="Serial number")
    id: str = Field(..., alias="ID")
    time: datetime
    op_time: Optional[str] = Field(None, alias="opTime")
    mos_rev: str = Field("2.8.5", alias="mosRev")
    supported_profiles: List[str] = Field(default_factory=list, alias="supportedProfiles")
    default_active_x: Optional[str] = Field(None, alias="defaultActiveX")
    mos_external_metadata: Optional[Dict[str, Any]] = Field(None, alias="mosExternalMetadata")
    
    class Config:
        allow_population_by_field_name = True


# Connection schemas
class MOSConnectionBase(BaseModel):
    """Base MOS connection schema"""
    nrcs_id: str
    nrcs_description: Optional[str] = None
    supported_profiles: Optional[List[str]] = None
    capabilities: Optional[Dict[str, Any]] = None


class MOSConnectionCreate(MOSConnectionBase):
    """Schema for creating MOS connections"""
    pass


class MOSConnectionResponse(MOSConnectionBase):
    """Schema for MOS connection responses"""
    id: str
    connection_status: ConnectionStatus
    last_heartbeat: Optional[datetime]
    created_at: datetime
    updated_at: datetime


# Message processing schemas
class MOSMessageBase(BaseModel):
    """Base MOS message schema"""
    message_type: MOSMessageType
    direction: str  # 'inbound' or 'outbound'
    raw_message: str
    parsed_message: Optional[Dict[str, Any]] = None


class MOSMessageCreate(MOSMessageBase):
    """Schema for creating MOS messages"""
    connection_id: str


class MOSMessageResponse(MOSMessageBase):
    """Schema for MOS message responses"""
    id: str
    message_id: Optional[str]
    processing_status: str
    error_message: Optional[str]
    received_at: datetime
    processed_at: Optional[datetime]
    response_sent_at: Optional[datetime]


# Request/Response schemas for API
class ObjectSearchParams(BaseModel):
    """Search parameters for MOS objects"""
    obj_type: Optional[str] = None
    obj_group: Optional[str] = None
    status: Optional[MOSStatus] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    limit: int = Field(50, ge=1, le=1000)
    offset: int = Field(0, ge=0)


class RunningOrderSearchParams(BaseModel):
    """Search parameters for running orders"""
    status: Optional[str] = None
    ready_to_air: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    limit: int = Field(50, ge=1, le=1000)
    offset: int = Field(0, ge=0)


class PaginatedResponse(BaseModel):
    """Paginated response wrapper"""
    items: List[Any]
    total: int
    limit: int
    offset: int
    has_next: bool
    has_prev: bool


# Status and health schemas
class HealthStatus(BaseModel):
    """Health check status"""
    status: str
    timestamp: datetime
    service: str
    version: str
    connections: Dict[str, str]
    database: bool
    redis: bool


class ConnectionStats(BaseModel):
    """Connection statistics"""
    total_connections: int
    active_connections: int
    total_objects: int
    total_running_orders: int
    total_messages: int
    last_24h_messages: int