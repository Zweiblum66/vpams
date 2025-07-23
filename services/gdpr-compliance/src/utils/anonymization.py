"""Anonymization utilities for GDPR compliance"""

import hashlib
import random
import string
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid


def anonymize_data(
    data: Dict[str, Any],
    method: str,
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Apply anonymization method to data record"""
    params = params or {}
    anonymized = data.copy()
    
    if method == "hash":
        return _hash_anonymize(anonymized, params)
    elif method == "mask":
        return _mask_anonymize(anonymized, params)
    elif method == "pseudonymize":
        return _pseudonymize(anonymized, params)
    elif method == "generalize":
        return _generalize(anonymized, params)
    elif method == "remove":
        return _remove_fields(anonymized, params)
    elif method == "random":
        return _randomize(anonymized, params)
    else:
        raise ValueError(f"Unknown anonymization method: {method}")


def _hash_anonymize(data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """Hash sensitive fields using SHA-256"""
    fields = params.get("fields", [])
    salt = params.get("salt", "gdpr-compliance")
    
    for field in fields:
        if field in data and data[field] is not None:
            value_str = str(data[field])
            hashed = hashlib.sha256(f"{salt}{value_str}".encode()).hexdigest()
            data[field] = hashed[:16] if params.get("truncate") else hashed
    
    return data


def _mask_anonymize(data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """Mask parts of sensitive fields"""
    fields = params.get("fields", [])
    mask_char = params.get("mask_char", "*")
    
    for field in fields:
        if field in data and data[field] is not None:
            value = str(data[field])
            
            # Email masking
            if "@" in value:
                local, domain = value.split("@", 1)
                if len(local) > 2:
                    masked_local = local[0] + mask_char * (len(local) - 2) + local[-1]
                else:
                    masked_local = mask_char * len(local)
                data[field] = f"{masked_local}@{domain}"
            
            # Phone number masking
            elif re.match(r"^\+?\d{10,15}$", value.replace(" ", "").replace("-", "")):
                clean_phone = re.sub(r"[^\d+]", "", value)
                if len(clean_phone) > 6:
                    data[field] = clean_phone[:3] + mask_char * (len(clean_phone) - 6) + clean_phone[-3:]
                else:
                    data[field] = mask_char * len(clean_phone)
            
            # General string masking
            else:
                mask_percentage = params.get("mask_percentage", 0.7)
                mask_length = int(len(value) * mask_percentage)
                if mask_length > 0 and len(value) > 3:
                    start_visible = (len(value) - mask_length) // 2
                    end_visible = start_visible + mask_length
                    data[field] = value[:start_visible] + mask_char * mask_length + value[end_visible:]
                else:
                    data[field] = mask_char * len(value)
    
    return data


def _pseudonymize(data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """Replace identifiers with pseudonyms"""
    fields = params.get("fields", [])
    mapping = params.get("mapping", {})
    
    for field in fields:
        if field in data and data[field] is not None:
            original_value = str(data[field])
            
            # Use existing mapping or create new pseudonym
            if original_value in mapping:
                data[field] = mapping[original_value]
            else:
                # Generate consistent pseudonym based on field type
                if field.lower() in ["name", "username", "first_name", "last_name"]:
                    data[field] = _generate_pseudonym_name()
                elif field.lower() in ["email"]:
                    data[field] = _generate_pseudonym_email()
                elif field.lower() in ["id", "user_id", "customer_id"]:
                    data[field] = _generate_pseudonym_id()
                else:
                    data[field] = f"ANON_{uuid.uuid4().hex[:8].upper()}"
    
    return data


def _generalize(data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """Generalize specific values to broader categories"""
    fields = params.get("fields", [])
    
    for field in fields:
        if field in data and data[field] is not None:
            value = data[field]
            
            # Age generalization
            if field.lower() in ["age", "birth_year"]:
                if isinstance(value, (int, float)):
                    age = int(value)
                    if age < 18:
                        data[field] = "Under 18"
                    elif age < 30:
                        data[field] = "18-29"
                    elif age < 40:
                        data[field] = "30-39"
                    elif age < 50:
                        data[field] = "40-49"
                    elif age < 65:
                        data[field] = "50-64"
                    else:
                        data[field] = "65+"
            
            # Date generalization
            elif field.lower().endswith("_date") or field.lower().endswith("_at"):
                if isinstance(value, datetime):
                    data[field] = value.strftime("%Y-%m")  # Keep only year and month
                elif isinstance(value, str):
                    try:
                        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                        data[field] = dt.strftime("%Y-%m")
                    except:
                        data[field] = "Unknown"
            
            # Location generalization
            elif field.lower() in ["zip_code", "postal_code"]:
                if isinstance(value, str) and len(value) >= 3:
                    data[field] = value[:3] + "XX"  # Keep only first 3 digits
            
            # IP address generalization
            elif field.lower() in ["ip_address", "ip"]:
                if isinstance(value, str) and "." in value:
                    parts = value.split(".")
                    if len(parts) == 4:
                        data[field] = f"{parts[0]}.{parts[1]}.XXX.XXX"
    
    return data


def _remove_fields(data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """Remove specified fields entirely"""
    fields = params.get("fields", [])
    
    for field in fields:
        data.pop(field, None)
    
    return data


def _randomize(data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """Replace values with random data of the same type"""
    fields = params.get("fields", [])
    
    for field in fields:
        if field in data and data[field] is not None:
            value = data[field]
            
            if isinstance(value, str):
                # Generate random string of same length
                length = len(value)
                if field.lower() in ["email"]:
                    data[field] = _generate_random_email()
                elif field.lower() in ["phone", "telephone", "mobile"]:
                    data[field] = _generate_random_phone()
                else:
                    data[field] = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
            
            elif isinstance(value, int):
                # Generate random number in similar range
                magnitude = len(str(abs(value)))
                data[field] = random.randint(10**(magnitude-1), 10**magnitude - 1)
            
            elif isinstance(value, float):
                # Generate random float in similar range
                data[field] = round(random.uniform(0, value * 2), 2)
            
            elif isinstance(value, bool):
                # Random boolean
                data[field] = random.choice([True, False])
    
    return data


# Helper functions for generating pseudonyms
def _generate_pseudonym_name() -> str:
    """Generate a realistic-looking pseudonym name"""
    first_names = ["Alex", "Jordan", "Casey", "Morgan", "Taylor", "Jamie", "Riley", "Avery"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
    return f"{random.choice(first_names)} {random.choice(last_names)}"


def _generate_pseudonym_email() -> str:
    """Generate a pseudonym email address"""
    username = ''.join(random.choices(string.ascii_lowercase, k=8))
    domains = ["example.com", "test.com", "anonymous.org", "private.net"]
    return f"{username}@{random.choice(domains)}"


def _generate_pseudonym_id() -> str:
    """Generate a pseudonym ID"""
    return f"USER_{uuid.uuid4().hex[:12].upper()}"


def _generate_random_email() -> str:
    """Generate a random email address"""
    username_length = random.randint(5, 12)
    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=username_length))
    domains = ["email.com", "mail.net", "provider.org", "service.io"]
    return f"{username}@{random.choice(domains)}"


def _generate_random_phone() -> str:
    """Generate a random phone number"""
    country_code = random.choice(["+1", "+44", "+49", "+33", "+61"])
    area_code = random.randint(100, 999)
    number = random.randint(1000000, 9999999)
    return f"{country_code} {area_code} {number}"


def batch_anonymize(
    records: List[Dict[str, Any]],
    method: str,
    params: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Apply anonymization to a batch of records"""
    # If using pseudonymization, maintain consistent mapping across batch
    if method == "pseudonymize" and params:
        params = params.copy()
        params["mapping"] = params.get("mapping", {})
    
    return [anonymize_data(record, method, params) for record in records]


def validate_anonymization(
    original: Dict[str, Any],
    anonymized: Dict[str, Any],
    method: str,
    params: Optional[Dict[str, Any]] = None
) -> bool:
    """Validate that anonymization was applied correctly"""
    params = params or {}
    fields = params.get("fields", [])
    
    if method == "remove":
        # Check that fields were removed
        for field in fields:
            if field in anonymized:
                return False
    else:
        # Check that specified fields were modified
        for field in fields:
            if field in original and field in anonymized:
                if original[field] == anonymized[field] and original[field] is not None:
                    return False
    
    return True