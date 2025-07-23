"""
Metadata Validation Service

This module provides validation functionality for metadata against schemas.
"""

import re
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from uuid import UUID
import structlog

from ..db.models import (
    MetadataSchema, FieldDefinition, FieldType, 
    MetadataDocument, FieldConstraint
)
from ..core.exceptions import ValidationError

logger = structlog.get_logger()


class MetadataValidator:
    """Validates metadata against schemas"""
    
    def __init__(self):
        self.type_validators = {
            FieldType.STRING: self._validate_string,
            FieldType.INTEGER: self._validate_integer,
            FieldType.FLOAT: self._validate_float,
            FieldType.BOOLEAN: self._validate_boolean,
            FieldType.DATE: self._validate_date,
            FieldType.DATETIME: self._validate_datetime,
            FieldType.ARRAY: self._validate_array,
            FieldType.OBJECT: self._validate_object,
            FieldType.REFERENCE: self._validate_reference,
            FieldType.ENUM: self._validate_enum,
            FieldType.TEXT: self._validate_text,
            FieldType.URL: self._validate_url,
            FieldType.EMAIL: self._validate_email,
            FieldType.PHONE: self._validate_phone,
            FieldType.JSON: self._validate_json,
            # Advanced custom field types
            FieldType.CURRENCY: self._validate_currency,
            FieldType.PERCENTAGE: self._validate_percentage,
            FieldType.DURATION: self._validate_duration,
            FieldType.GEOLOCATION: self._validate_geolocation,
            FieldType.COLOR: self._validate_color,
            FieldType.RATING: self._validate_rating,
            FieldType.TAGS: self._validate_tags,
            FieldType.RICH_TEXT: self._validate_rich_text,
            FieldType.CODE: self._validate_code,
            FieldType.MARKDOWN: self._validate_markdown,
            FieldType.TIMECODE: self._validate_timecode,
            FieldType.RESOLUTION: self._validate_resolution,
            FieldType.ASPECT_RATIO: self._validate_aspect_ratio,
            FieldType.FILE_SIZE: self._validate_file_size,
            FieldType.MIME_TYPE: self._validate_mime_type,
            FieldType.IP_ADDRESS: self._validate_ip_address,
            FieldType.MAC_ADDRESS: self._validate_mac_address,
            FieldType.UUID_TYPE: self._validate_uuid_type,
            FieldType.REGEX: self._validate_regex,
            FieldType.SLIDER: self._validate_slider,
        }
        
        # Common regex patterns
        self.patterns = {
            "email": re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"),
            "url": re.compile(
                r"^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}"
                r"\b([-a-zA-Z0-9()@:%_\+.~#?&\/\/=]*)$"
            ),
            "phone": re.compile(r"^\+?1?\d{9,15}$"),
        }
    
    async def validate_metadata(
        self,
        metadata: Dict[str, Any],
        schema: MetadataSchema,
        custom_fields: Optional[Dict[str, Any]] = None,
        strict: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Validate metadata against a schema
        
        Args:
            metadata: Metadata values to validate
            schema: Schema to validate against
            custom_fields: Additional custom fields
            strict: Override schema's strict_mode setting
            
        Returns:
            Validation result with errors and warnings
        """
        errors = []
        warnings = []
        validated_data = {}
        
        # Use schema's strict mode if not overridden
        if strict is None:
            strict = schema.strict_mode
        
        # Build field map for quick lookup
        field_map = {field.name: field for field in schema.fields}
        
        # Validate required fields
        for field in schema.fields:
            if field.required and field.name not in metadata:
                # Check if there's a default value
                if field.default_value is not None:
                    validated_data[field.name] = field.default_value
                else:
                    errors.append({
                        "field": field.name,
                        "error": "Required field missing",
                        "type": "missing_required"
                    })
        
        # Validate provided fields
        for field_name, value in metadata.items():
            if field_name not in field_map:
                if strict:
                    errors.append({
                        "field": field_name,
                        "error": "Unknown field in strict mode",
                        "type": "unknown_field"
                    })
                else:
                    # Store as custom field if allowed
                    if schema.allow_custom_fields:
                        if custom_fields is None:
                            custom_fields = {}
                        custom_fields[field_name] = value
                    else:
                        warnings.append({
                            "field": field_name,
                            "warning": "Unknown field ignored",
                            "type": "unknown_field"
                        })
                continue
            
            field_def = field_map[field_name]
            
            # Validate field value
            try:
                validated_value = await self._validate_field(value, field_def)
                validated_data[field_name] = validated_value
            except ValidationError as e:
                errors.append({
                    "field": field_name,
                    "error": str(e),
                    "type": "validation_error"
                })
        
        # Validate unique constraints (would need database check in real implementation)
        # This is a placeholder for the validation result structure
        
        result = {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "validated_data": validated_data,
            "custom_fields": custom_fields or {}
        }
        
        return result
    
    async def _validate_field(self, value: Any, field_def: FieldDefinition) -> Any:
        """Validate a single field value"""
        # Handle null values
        if value is None:
            if field_def.required:
                raise ValidationError("Required field cannot be null")
            return None
        
        # Get type validator
        validator = self.type_validators.get(field_def.field_type)
        if not validator:
            raise ValidationError(f"Unknown field type: {field_def.field_type}")
        
        # Validate type and constraints
        return await validator(value, field_def)
    
    async def _validate_string(self, value: Any, field_def: FieldDefinition) -> str:
        """Validate string field"""
        if not isinstance(value, str):
            raise ValidationError(f"Expected string, got {type(value).__name__}")
        
        constraints = field_def.constraints
        
        # Check length constraints
        if "min_length" in constraints and len(value) < constraints["min_length"]:
            raise ValidationError(
                f"String length {len(value)} is less than minimum {constraints['min_length']}"
            )
        
        if "max_length" in constraints and len(value) > constraints["max_length"]:
            raise ValidationError(
                f"String length {len(value)} exceeds maximum {constraints['max_length']}"
            )
        
        # Check pattern
        if "pattern" in constraints:
            pattern = re.compile(constraints["pattern"])
            if not pattern.match(value):
                raise ValidationError(
                    f"String does not match required pattern: {constraints['pattern']}"
                )
        
        return value
    
    async def _validate_integer(self, value: Any, field_def: FieldDefinition) -> int:
        """Validate integer field"""
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            raise ValidationError(f"Expected integer, got {type(value).__name__}")
        
        constraints = field_def.constraints
        
        # Check value constraints
        if "min_value" in constraints and int_value < constraints["min_value"]:
            raise ValidationError(
                f"Value {int_value} is less than minimum {constraints['min_value']}"
            )
        
        if "max_value" in constraints and int_value > constraints["max_value"]:
            raise ValidationError(
                f"Value {int_value} exceeds maximum {constraints['max_value']}"
            )
        
        return int_value
    
    async def _validate_float(self, value: Any, field_def: FieldDefinition) -> float:
        """Validate float field"""
        try:
            float_value = float(value)
        except (ValueError, TypeError):
            raise ValidationError(f"Expected float, got {type(value).__name__}")
        
        constraints = field_def.constraints
        
        # Check value constraints
        if "min_value" in constraints and float_value < constraints["min_value"]:
            raise ValidationError(
                f"Value {float_value} is less than minimum {constraints['min_value']}"
            )
        
        if "max_value" in constraints and float_value > constraints["max_value"]:
            raise ValidationError(
                f"Value {float_value} exceeds maximum {constraints['max_value']}"
            )
        
        return float_value
    
    async def _validate_boolean(self, value: Any, field_def: FieldDefinition) -> bool:
        """Validate boolean field"""
        if isinstance(value, bool):
            return value
        
        # Handle string representations
        if isinstance(value, str):
            if value.lower() in ("true", "1", "yes", "on"):
                return True
            elif value.lower() in ("false", "0", "no", "off"):
                return False
        
        raise ValidationError(f"Expected boolean, got {type(value).__name__}")
    
    async def _validate_date(self, value: Any, field_def: FieldDefinition) -> str:
        """Validate date field"""
        if isinstance(value, datetime):
            return value.date().isoformat()
        
        if isinstance(value, str):
            try:
                # Try to parse ISO date format
                datetime.fromisoformat(value.replace('Z', '+00:00'))
                return value
            except ValueError:
                raise ValidationError(f"Invalid date format: {value}")
        
        raise ValidationError(f"Expected date, got {type(value).__name__}")
    
    async def _validate_datetime(self, value: Any, field_def: FieldDefinition) -> str:
        """Validate datetime field"""
        if isinstance(value, datetime):
            return value.isoformat()
        
        if isinstance(value, str):
            try:
                # Try to parse ISO datetime format
                datetime.fromisoformat(value.replace('Z', '+00:00'))
                return value
            except ValueError:
                raise ValidationError(f"Invalid datetime format: {value}")
        
        raise ValidationError(f"Expected datetime, got {type(value).__name__}")
    
    async def _validate_array(self, value: Any, field_def: FieldDefinition) -> List[Any]:
        """Validate array field"""
        if not isinstance(value, (list, tuple)):
            raise ValidationError(f"Expected array, got {type(value).__name__}")
        
        constraints = field_def.constraints
        result = []
        
        # Check array length
        if "min_length" in constraints and len(value) < constraints["min_length"]:
            raise ValidationError(
                f"Array length {len(value)} is less than minimum {constraints['min_length']}"
            )
        
        if "max_length" in constraints and len(value) > constraints["max_length"]:
            raise ValidationError(
                f"Array length {len(value)} exceeds maximum {constraints['max_length']}"
            )
        
        # Validate array elements if type is specified
        if field_def.array_type:
            # Create a temporary field definition for array elements
            element_field = FieldDefinition(
                name=f"{field_def.name}[element]",
                display_name="Array Element",
                field_type=field_def.array_type,
                constraints=constraints.get("element_constraints", {})
            )
            
            for i, item in enumerate(value):
                try:
                    validated_item = await self._validate_field(item, element_field)
                    result.append(validated_item)
                except ValidationError as e:
                    raise ValidationError(f"Array element {i}: {str(e)}")
        else:
            result = list(value)
        
        return result
    
    async def _validate_object(self, value: Any, field_def: FieldDefinition) -> Dict[str, Any]:
        """Validate object field"""
        if not isinstance(value, dict):
            raise ValidationError(f"Expected object, got {type(value).__name__}")
        
        # If object schema is defined, validate against it
        if field_def.object_schema:
            result = {}
            schema_fields = {f.name: f for f in field_def.object_schema}
            
            # Validate each field in the object
            for field_name, field_value in value.items():
                if field_name in schema_fields:
                    try:
                        validated_value = await self._validate_field(
                            field_value, 
                            schema_fields[field_name]
                        )
                        result[field_name] = validated_value
                    except ValidationError as e:
                        raise ValidationError(f"Object field '{field_name}': {str(e)}")
                else:
                    # Allow extra fields in objects by default
                    result[field_name] = field_value
            
            # Check required fields
            for field_name, field in schema_fields.items():
                if field.required and field_name not in value:
                    raise ValidationError(f"Required object field '{field_name}' missing")
            
            return result
        
        return value
    
    async def _validate_reference(self, value: Any, field_def: FieldDefinition) -> str:
        """Validate reference field"""
        # Accept UUID string or UUID object
        if isinstance(value, UUID):
            return str(value)
        
        if isinstance(value, str):
            try:
                UUID(value)
                return value
            except ValueError:
                raise ValidationError(f"Invalid UUID reference: {value}")
        
        raise ValidationError(f"Expected UUID reference, got {type(value).__name__}")
    
    async def _validate_enum(self, value: Any, field_def: FieldDefinition) -> str:
        """Validate enum field"""
        enum_values = field_def.constraints.get("enum_values", [])
        
        if not enum_values:
            raise ValidationError("Enum field missing enum_values constraint")
        
        if value not in enum_values:
            raise ValidationError(
                f"Value '{value}' not in allowed enum values: {enum_values}"
            )
        
        return value
    
    async def _validate_text(self, value: Any, field_def: FieldDefinition) -> str:
        """Validate text field (long text)"""
        # Similar to string but typically allows longer content
        return await self._validate_string(value, field_def)
    
    async def _validate_url(self, value: Any, field_def: FieldDefinition) -> str:
        """Validate URL field"""
        if not isinstance(value, str):
            raise ValidationError(f"Expected URL string, got {type(value).__name__}")
        
        if not self.patterns["url"].match(value):
            raise ValidationError(f"Invalid URL format: {value}")
        
        return value
    
    async def _validate_email(self, value: Any, field_def: FieldDefinition) -> str:
        """Validate email field"""
        if not isinstance(value, str):
            raise ValidationError(f"Expected email string, got {type(value).__name__}")
        
        if not self.patterns["email"].match(value):
            raise ValidationError(f"Invalid email format: {value}")
        
        return value.lower()  # Normalize to lowercase
    
    async def _validate_phone(self, value: Any, field_def: FieldDefinition) -> str:
        """Validate phone field"""
        if not isinstance(value, str):
            raise ValidationError(f"Expected phone string, got {type(value).__name__}")
        
        # Remove common formatting characters
        cleaned = re.sub(r"[\s\-\(\)]+", "", value)
        
        if not self.patterns["phone"].match(cleaned):
            raise ValidationError(f"Invalid phone format: {value}")
        
        return cleaned
    
    async def _validate_json(self, value: Any, field_def: FieldDefinition) -> Any:
        """Validate JSON field"""
        # JSON field can contain any valid JSON structure
        # In Python, this means dict, list, str, int, float, bool, or None
        valid_types = (dict, list, str, int, float, bool, type(None))
        
        if not isinstance(value, valid_types):
            raise ValidationError(
                f"Invalid JSON type: {type(value).__name__}"
            )
        
        return value
    
    # Advanced custom field type validators
    async def _validate_currency(self, value: Any, field_def: FieldDefinition) -> Dict[str, Any]:
        """Validate currency field"""
        if isinstance(value, dict):
            if "amount" not in value or "currency" not in value:
                raise ValidationError("Currency must have 'amount' and 'currency' fields")
            
            # Validate amount
            try:
                amount = float(value["amount"])
            except (ValueError, TypeError):
                raise ValidationError("Currency amount must be a number")
            
            # Validate currency code
            currency = value["currency"]
            if not isinstance(currency, str) or len(currency) != 3:
                raise ValidationError("Currency code must be a 3-letter string")
            
            return {"amount": amount, "currency": currency.upper()}
        
        raise ValidationError("Currency must be an object with amount and currency")
    
    async def _validate_percentage(self, value: Any, field_def: FieldDefinition) -> float:
        """Validate percentage field"""
        try:
            percentage = float(value)
        except (ValueError, TypeError):
            raise ValidationError("Percentage must be a number")
        
        constraints = field_def.constraints
        min_val = constraints.get("min_value", 0)
        max_val = constraints.get("max_value", 100)
        
        if percentage < min_val or percentage > max_val:
            raise ValidationError(f"Percentage must be between {min_val} and {max_val}")
        
        return percentage
    
    async def _validate_duration(self, value: Any, field_def: FieldDefinition) -> float:
        """Validate duration field (in seconds)"""
        if isinstance(value, str):
            # Parse duration string (HH:MM:SS or MM:SS)
            parts = value.split(":")
            if len(parts) == 2:  # MM:SS
                try:
                    minutes, seconds = map(int, parts)
                    return minutes * 60 + seconds
                except ValueError:
                    raise ValidationError("Invalid duration format")
            elif len(parts) == 3:  # HH:MM:SS
                try:
                    hours, minutes, seconds = map(int, parts)
                    return hours * 3600 + minutes * 60 + seconds
                except ValueError:
                    raise ValidationError("Invalid duration format")
        
        try:
            duration = float(value)
            if duration < 0:
                raise ValidationError("Duration cannot be negative")
            return duration
        except (ValueError, TypeError):
            raise ValidationError("Duration must be a number or time string")
    
    async def _validate_geolocation(self, value: Any, field_def: FieldDefinition) -> Dict[str, float]:
        """Validate geolocation field"""
        if isinstance(value, dict):
            if "latitude" not in value or "longitude" not in value:
                raise ValidationError("Geolocation must have 'latitude' and 'longitude' fields")
            
            try:
                lat = float(value["latitude"])
                lng = float(value["longitude"])
            except (ValueError, TypeError):
                raise ValidationError("Latitude and longitude must be numbers")
            
            if not (-90 <= lat <= 90):
                raise ValidationError("Latitude must be between -90 and 90")
            
            if not (-180 <= lng <= 180):
                raise ValidationError("Longitude must be between -180 and 180")
            
            return {"latitude": lat, "longitude": lng}
        
        raise ValidationError("Geolocation must be an object with latitude and longitude")
    
    async def _validate_color(self, value: Any, field_def: FieldDefinition) -> str:
        """Validate color field"""
        if not isinstance(value, str):
            raise ValidationError("Color must be a string")
        
        # Support hex colors (#RRGGBB or #RGB)
        if value.startswith("#"):
            hex_color = value[1:]
            if len(hex_color) == 3:
                # Convert #RGB to #RRGGBB
                hex_color = "".join(c*2 for c in hex_color)
            
            if len(hex_color) != 6 or not all(c in "0123456789abcdefABCDEF" for c in hex_color):
                raise ValidationError("Invalid hex color format")
            
            return "#" + hex_color.upper()
        
        # Support RGB format
        if value.startswith("rgb(") and value.endswith(")"):
            rgb_values = value[4:-1].split(",")
            if len(rgb_values) != 3:
                raise ValidationError("Invalid RGB format")
            
            try:
                r, g, b = [int(v.strip()) for v in rgb_values]
                if not all(0 <= v <= 255 for v in [r, g, b]):
                    raise ValidationError("RGB values must be between 0 and 255")
                return f"rgb({r}, {g}, {b})"
            except ValueError:
                raise ValidationError("Invalid RGB values")
        
        raise ValidationError("Color must be in hex (#RRGGBB) or RGB format")
    
    async def _validate_rating(self, value: Any, field_def: FieldDefinition) -> int:
        """Validate rating field"""
        try:
            rating = int(value)
        except (ValueError, TypeError):
            raise ValidationError("Rating must be a number")
        
        constraints = field_def.constraints
        min_rating = constraints.get("min_value", 1)
        max_rating = constraints.get("max_value", 5)
        
        if rating < min_rating or rating > max_rating:
            raise ValidationError(f"Rating must be between {min_rating} and {max_rating}")
        
        return rating
    
    async def _validate_tags(self, value: Any, field_def: FieldDefinition) -> List[str]:
        """Validate tags field"""
        if isinstance(value, str):
            # Split comma-separated tags
            tags = [tag.strip() for tag in value.split(",") if tag.strip()]
        elif isinstance(value, list):
            tags = [str(tag).strip() for tag in value if str(tag).strip()]
        else:
            raise ValidationError("Tags must be a string or array")
        
        # Remove duplicates while preserving order
        unique_tags = []
        seen = set()
        for tag in tags:
            if tag not in seen:
                unique_tags.append(tag)
                seen.add(tag)
        
        constraints = field_def.constraints
        max_tags = constraints.get("max_length", 50)
        
        if len(unique_tags) > max_tags:
            raise ValidationError(f"Maximum {max_tags} tags allowed")
        
        return unique_tags
    
    async def _validate_rich_text(self, value: Any, field_def: FieldDefinition) -> str:
        """Validate rich text field"""
        if not isinstance(value, str):
            raise ValidationError("Rich text must be a string")
        
        # Basic HTML validation (simplified)
        constraints = field_def.constraints
        max_length = constraints.get("max_length", 10000)
        
        if len(value) > max_length:
            raise ValidationError(f"Rich text exceeds maximum length of {max_length}")
        
        return value
    
    async def _validate_code(self, value: Any, field_def: FieldDefinition) -> Dict[str, str]:
        """Validate code field"""
        if isinstance(value, dict):
            if "code" not in value:
                raise ValidationError("Code field must have 'code' property")
            
            code = value["code"]
            language = value.get("language", "text")
            
            if not isinstance(code, str):
                raise ValidationError("Code must be a string")
            
            return {"code": code, "language": language}
        
        if isinstance(value, str):
            return {"code": value, "language": "text"}
        
        raise ValidationError("Code must be a string or object with code and language")
    
    async def _validate_markdown(self, value: Any, field_def: FieldDefinition) -> str:
        """Validate markdown field"""
        if not isinstance(value, str):
            raise ValidationError("Markdown must be a string")
        
        constraints = field_def.constraints
        max_length = constraints.get("max_length", 10000)
        
        if len(value) > max_length:
            raise ValidationError(f"Markdown exceeds maximum length of {max_length}")
        
        return value
    
    async def _validate_timecode(self, value: Any, field_def: FieldDefinition) -> str:
        """Validate timecode field (HH:MM:SS:FF)"""
        if not isinstance(value, str):
            raise ValidationError("Timecode must be a string")
        
        # Validate timecode format
        if not re.match(r"^\d{2}:\d{2}:\d{2}:\d{2}$", value):
            raise ValidationError("Timecode must be in HH:MM:SS:FF format")
        
        parts = value.split(":")
        hours, minutes, seconds, frames = map(int, parts)
        
        if not (0 <= hours <= 23):
            raise ValidationError("Hours must be between 0 and 23")
        
        if not (0 <= minutes <= 59):
            raise ValidationError("Minutes must be between 0 and 59")
        
        if not (0 <= seconds <= 59):
            raise ValidationError("Seconds must be between 0 and 59")
        
        # Frame validation depends on frame rate
        constraints = field_def.constraints
        max_frames = constraints.get("max_frames", 29)  # Default to 30fps
        
        if not (0 <= frames <= max_frames):
            raise ValidationError(f"Frames must be between 0 and {max_frames}")
        
        return value
    
    async def _validate_resolution(self, value: Any, field_def: FieldDefinition) -> str:
        """Validate resolution field (1920x1080)"""
        if not isinstance(value, str):
            raise ValidationError("Resolution must be a string")
        
        if not re.match(r"^\d+x\d+$", value):
            raise ValidationError("Resolution must be in WIDTHxHEIGHT format")
        
        width, height = map(int, value.split("x"))
        
        if width <= 0 or height <= 0:
            raise ValidationError("Resolution dimensions must be positive")
        
        return value
    
    async def _validate_aspect_ratio(self, value: Any, field_def: FieldDefinition) -> str:
        """Validate aspect ratio field (16:9)"""
        if not isinstance(value, str):
            raise ValidationError("Aspect ratio must be a string")
        
        if not re.match(r"^\d+:\d+$", value):
            raise ValidationError("Aspect ratio must be in W:H format")
        
        width, height = map(int, value.split(":"))
        
        if width <= 0 or height <= 0:
            raise ValidationError("Aspect ratio dimensions must be positive")
        
        return value
    
    async def _validate_file_size(self, value: Any, field_def: FieldDefinition) -> int:
        """Validate file size field (in bytes)"""
        if isinstance(value, str):
            # Parse file size string (e.g., "1.5MB", "500KB")
            import re
            match = re.match(r"^([\d.]+)\s*([KMGT]?B?)$", value.upper())
            if not match:
                raise ValidationError("Invalid file size format")
            
            size, unit = match.groups()
            size = float(size)
            
            multipliers = {
                "B": 1,
                "KB": 1024,
                "MB": 1024**2,
                "GB": 1024**3,
                "TB": 1024**4
            }
            
            return int(size * multipliers.get(unit, 1))
        
        try:
            size = int(value)
            if size < 0:
                raise ValidationError("File size cannot be negative")
            return size
        except (ValueError, TypeError):
            raise ValidationError("File size must be a number or size string")
    
    async def _validate_mime_type(self, value: Any, field_def: FieldDefinition) -> str:
        """Validate MIME type field"""
        if not isinstance(value, str):
            raise ValidationError("MIME type must be a string")
        
        # Basic MIME type validation
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9!#$&\-\^]*\/[a-zA-Z0-9][a-zA-Z0-9!#$&\-\^]*$", value):
            raise ValidationError("Invalid MIME type format")
        
        return value.lower()
    
    async def _validate_ip_address(self, value: Any, field_def: FieldDefinition) -> str:
        """Validate IP address field"""
        if not isinstance(value, str):
            raise ValidationError("IP address must be a string")
        
        # Basic IPv4 validation
        if re.match(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$", value):
            parts = value.split(".")
            if all(0 <= int(part) <= 255 for part in parts):
                return value
        
        # Basic IPv6 validation (simplified)
        if re.match(r"^[0-9a-fA-F:]+$", value) and "::" in value or value.count(":") == 7:
            return value
        
        raise ValidationError("Invalid IP address format")
    
    async def _validate_mac_address(self, value: Any, field_def: FieldDefinition) -> str:
        """Validate MAC address field"""
        if not isinstance(value, str):
            raise ValidationError("MAC address must be a string")
        
        # Support different MAC address formats
        cleaned = value.replace(":", "").replace("-", "").replace(".", "")
        
        if len(cleaned) != 12 or not all(c in "0123456789abcdefABCDEF" for c in cleaned):
            raise ValidationError("Invalid MAC address format")
        
        # Return in standard format
        return ":".join(cleaned[i:i+2] for i in range(0, 12, 2)).upper()
    
    async def _validate_uuid_type(self, value: Any, field_def: FieldDefinition) -> str:
        """Validate UUID field"""
        if isinstance(value, UUID):
            return str(value)
        
        if isinstance(value, str):
            try:
                UUID(value)
                return value
            except ValueError:
                raise ValidationError("Invalid UUID format")
        
        raise ValidationError("UUID must be a string or UUID object")
    
    async def _validate_regex(self, value: Any, field_def: FieldDefinition) -> str:
        """Validate regex field"""
        if not isinstance(value, str):
            raise ValidationError("Regex must be a string")
        
        try:
            re.compile(value)
            return value
        except re.error as e:
            raise ValidationError(f"Invalid regex pattern: {str(e)}")
    
    async def _validate_slider(self, value: Any, field_def: FieldDefinition) -> float:
        """Validate slider field"""
        try:
            slider_value = float(value)
        except (ValueError, TypeError):
            raise ValidationError("Slider value must be a number")
        
        constraints = field_def.constraints
        min_val = constraints.get("min_value", 0)
        max_val = constraints.get("max_value", 100)
        
        if slider_value < min_val or slider_value > max_val:
            raise ValidationError(f"Slider value must be between {min_val} and {max_val}")
        
        return slider_value