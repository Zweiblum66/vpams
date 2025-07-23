"""
Custom Rule Engine for WAF Protection
"""

import re
import yaml
import json
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import structlog

from .waf_engine import WAFRequest, WAFResult

logger = structlog.get_logger()


class RuleAction(str, Enum):
    """Rule action types"""
    ALLOW = "allow"
    BLOCK = "block"
    LOG = "log"
    RATE_LIMIT = "rate_limit"
    CHALLENGE = "challenge"


class RuleTarget(str, Enum):
    """Rule target types"""
    URL = "url"
    HEADER = "header"
    BODY = "body"
    IP = "ip"
    USER_AGENT = "user_agent"
    METHOD = "method"
    QUERY_STRING = "query_string"
    COOKIE = "cookie"


class OperatorType(str, Enum):
    """Rule operator types"""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"
    LENGTH_GT = "length_gt"
    LENGTH_LT = "length_lt"
    IN_LIST = "in_list"
    NOT_IN_LIST = "not_in_list"
    IP_IN_RANGE = "ip_in_range"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"


@dataclass
class RuleCondition:
    """Individual rule condition"""
    target: RuleTarget
    operator: OperatorType
    value: Union[str, int, float, List[str]]
    header_name: Optional[str] = None  # For header-specific rules
    case_sensitive: bool = False
    
    def matches(self, request: WAFRequest) -> bool:
        """Check if condition matches the request"""
        try:
            target_value = self._extract_target_value(request)
            if target_value is None:
                return False
            
            return self._apply_operator(target_value, self.value)
            
        except Exception as e:
            logger.error("Rule condition evaluation failed", error=str(e), condition=self)
            return False
    
    def _extract_target_value(self, request: WAFRequest) -> Optional[str]:
        """Extract target value from request"""
        if self.target == RuleTarget.URL:
            return request.url
        elif self.target == RuleTarget.METHOD:
            return request.method
        elif self.target == RuleTarget.IP:
            return request.ip
        elif self.target == RuleTarget.USER_AGENT:
            return request.user_agent
        elif self.target == RuleTarget.BODY:
            return request.body
        elif self.target == RuleTarget.HEADER:
            if self.header_name:
                return request.headers.get(self.header_name.lower())
            return None
        elif self.target == RuleTarget.QUERY_STRING:
            # Extract query string from URL
            from urllib.parse import urlparse
            parsed = urlparse(request.url)
            return parsed.query
        elif self.target == RuleTarget.COOKIE:
            # Extract cookies from headers
            cookie_header = request.headers.get('cookie', '')
            if self.header_name:
                # Look for specific cookie
                import re
                pattern = rf'{re.escape(self.header_name)}\s*=\s*([^;]+)'
                match = re.search(pattern, cookie_header)
                return match.group(1) if match else None
            return cookie_header
        
        return None
    
    def _apply_operator(self, target_value: str, expected_value: Union[str, int, float, List[str]]) -> bool:
        """Apply operator to compare values"""
        if not self.case_sensitive and isinstance(target_value, str):
            target_value = target_value.lower()
            if isinstance(expected_value, str):
                expected_value = expected_value.lower()
            elif isinstance(expected_value, list):
                expected_value = [v.lower() if isinstance(v, str) else v for v in expected_value]
        
        if self.operator == OperatorType.EQUALS:
            return target_value == expected_value
        elif self.operator == OperatorType.NOT_EQUALS:
            return target_value != expected_value
        elif self.operator == OperatorType.CONTAINS:
            return str(expected_value) in target_value
        elif self.operator == OperatorType.NOT_CONTAINS:
            return str(expected_value) not in target_value
        elif self.operator == OperatorType.STARTS_WITH:
            return target_value.startswith(str(expected_value))
        elif self.operator == OperatorType.ENDS_WITH:
            return target_value.endswith(str(expected_value))
        elif self.operator == OperatorType.REGEX:
            try:
                pattern = re.compile(str(expected_value), re.IGNORECASE if not self.case_sensitive else 0)
                return bool(pattern.search(target_value))
            except re.error:
                logger.error("Invalid regex pattern", pattern=expected_value)
                return False
        elif self.operator == OperatorType.LENGTH_GT:
            return len(target_value) > int(expected_value)
        elif self.operator == OperatorType.LENGTH_LT:
            return len(target_value) < int(expected_value)
        elif self.operator == OperatorType.IN_LIST:
            return target_value in expected_value
        elif self.operator == OperatorType.NOT_IN_LIST:
            return target_value not in expected_value
        elif self.operator == OperatorType.IP_IN_RANGE:
            try:
                import ipaddress
                return ipaddress.ip_address(target_value) in ipaddress.ip_network(str(expected_value), strict=False)
            except ValueError:
                return False
        elif self.operator == OperatorType.GREATER_THAN:
            try:
                return float(target_value) > float(expected_value)
            except ValueError:
                return False
        elif self.operator == OperatorType.LESS_THAN:
            try:
                return float(target_value) < float(expected_value)
            except ValueError:
                return False
        
        return False


@dataclass
class CustomRule:
    """Custom WAF rule"""
    id: str
    name: str
    description: str
    enabled: bool
    action: RuleAction
    conditions: List[RuleCondition]
    priority: int = 100
    threat_level: str = "medium"
    score: int = 50
    rate_limit_window: Optional[int] = None  # seconds
    rate_limit_threshold: Optional[int] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
    
    def matches(self, request: WAFRequest) -> bool:
        """Check if rule matches the request"""
        if not self.enabled or not self.conditions:
            return False
        
        # All conditions must match (AND logic)
        for condition in self.conditions:
            if not condition.matches(request):
                return False
        
        return True


class RuleEngine:
    """Custom rule engine for WAF"""
    
    def __init__(self, rules_file: Optional[str] = None):
        self.rules: List[CustomRule] = []
        self.rule_stats: Dict[str, Dict[str, int]] = {}
        
        if rules_file:
            self.load_rules_from_file(rules_file)
    
    def load_rules_from_file(self, file_path: str) -> bool:
        """Load rules from YAML or JSON file"""
        try:
            with open(file_path, 'r') as f:
                if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            self.load_rules_from_dict(data)
            logger.info("Rules loaded successfully", file=file_path, count=len(self.rules))
            return True
            
        except FileNotFoundError:
            logger.warning("Rules file not found", file=file_path)
            return False
        except Exception as e:
            logger.error("Failed to load rules", file=file_path, error=str(e))
            return False
    
    def load_rules_from_dict(self, data: Dict[str, Any]):
        """Load rules from dictionary"""
        self.rules = []
        
        for rule_data in data.get('rules', []):
            try:
                conditions = []
                for cond_data in rule_data.get('conditions', []):
                    condition = RuleCondition(
                        target=RuleTarget(cond_data['target']),
                        operator=OperatorType(cond_data['operator']),
                        value=cond_data['value'],
                        header_name=cond_data.get('header_name'),
                        case_sensitive=cond_data.get('case_sensitive', False)
                    )
                    conditions.append(condition)
                
                rule = CustomRule(
                    id=rule_data['id'],
                    name=rule_data['name'],
                    description=rule_data['description'],
                    enabled=rule_data.get('enabled', True),
                    action=RuleAction(rule_data['action']),
                    conditions=conditions,
                    priority=rule_data.get('priority', 100),
                    threat_level=rule_data.get('threat_level', 'medium'),
                    score=rule_data.get('score', 50),
                    rate_limit_window=rule_data.get('rate_limit_window'),
                    rate_limit_threshold=rule_data.get('rate_limit_threshold'),
                    tags=rule_data.get('tags', [])
                )
                
                self.rules.append(rule)
                self.rule_stats[rule.id] = {"matches": 0, "blocks": 0}
                
            except Exception as e:
                logger.error("Failed to parse rule", rule_data=rule_data, error=str(e))
    
    def evaluate_request(self, request: WAFRequest) -> List[CustomRule]:
        """Evaluate request against all rules"""
        matched_rules = []
        
        # Sort rules by priority (lower number = higher priority)
        sorted_rules = sorted(self.rules, key=lambda r: r.priority)
        
        for rule in sorted_rules:
            if rule.matches(request):
                matched_rules.append(rule)
                self.rule_stats[rule.id]["matches"] += 1
                
                # If rule action is BLOCK, we can stop evaluation
                if rule.action == RuleAction.BLOCK:
                    self.rule_stats[rule.id]["blocks"] += 1
                    break
        
        return matched_rules
    
    def add_rule(self, rule: CustomRule):
        """Add a new rule"""
        self.rules.append(rule)
        self.rule_stats[rule.id] = {"matches": 0, "blocks": 0}
        logger.info("Rule added", rule_id=rule.id, rule_name=rule.name)
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID"""
        for i, rule in enumerate(self.rules):
            if rule.id == rule_id:
                del self.rules[i]
                if rule_id in self.rule_stats:
                    del self.rule_stats[rule_id]
                logger.info("Rule removed", rule_id=rule_id)
                return True
        
        return False
    
    def update_rule(self, rule_id: str, updated_rule: CustomRule) -> bool:
        """Update an existing rule"""
        for i, rule in enumerate(self.rules):
            if rule.id == rule_id:
                self.rules[i] = updated_rule
                logger.info("Rule updated", rule_id=rule_id)
                return True
        
        return False
    
    def get_rule(self, rule_id: str) -> Optional[CustomRule]:
        """Get a rule by ID"""
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        return None
    
    def list_rules(self, enabled_only: bool = False) -> List[CustomRule]:
        """List all rules"""
        if enabled_only:
            return [rule for rule in self.rules if rule.enabled]
        return self.rules.copy()
    
    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule"""
        rule = self.get_rule(rule_id)
        if rule:
            rule.enabled = True
            logger.info("Rule enabled", rule_id=rule_id)
            return True
        return False
    
    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule"""
        rule = self.get_rule(rule_id)
        if rule:
            rule.enabled = False
            logger.info("Rule disabled", rule_id=rule_id)
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rule engine statistics"""
        total_rules = len(self.rules)
        enabled_rules = len([r for r in self.rules if r.enabled])
        
        return {
            "total_rules": total_rules,
            "enabled_rules": enabled_rules,
            "disabled_rules": total_rules - enabled_rules,
            "rule_stats": self.rule_stats.copy()
        }
    
    def export_rules(self) -> Dict[str, Any]:
        """Export rules to dictionary format"""
        rules_data = []
        
        for rule in self.rules:
            conditions_data = []
            for condition in rule.conditions:
                cond_data = {
                    "target": condition.target.value,
                    "operator": condition.operator.value,
                    "value": condition.value,
                    "case_sensitive": condition.case_sensitive
                }
                if condition.header_name:
                    cond_data["header_name"] = condition.header_name
                conditions_data.append(cond_data)
            
            rule_data = {
                "id": rule.id,
                "name": rule.name,
                "description": rule.description,
                "enabled": rule.enabled,
                "action": rule.action.value,
                "conditions": conditions_data,
                "priority": rule.priority,
                "threat_level": rule.threat_level,
                "score": rule.score,
                "tags": rule.tags
            }
            
            if rule.rate_limit_window:
                rule_data["rate_limit_window"] = rule.rate_limit_window
            if rule.rate_limit_threshold:
                rule_data["rate_limit_threshold"] = rule.rate_limit_threshold
            
            rules_data.append(rule_data)
        
        return {"rules": rules_data}
    
    def save_rules_to_file(self, file_path: str) -> bool:
        """Save rules to file"""
        try:
            data = self.export_rules()
            
            with open(file_path, 'w') as f:
                if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                    yaml.dump(data, f, default_flow_style=False)
                else:
                    json.dump(data, f, indent=2)
            
            logger.info("Rules saved to file", file=file_path, count=len(self.rules))
            return True
            
        except Exception as e:
            logger.error("Failed to save rules", file=file_path, error=str(e))
            return False


# Default rules for common attacks
DEFAULT_RULES = {
    "rules": [
        {
            "id": "SQL_INJECTION_BASIC",
            "name": "Basic SQL Injection Detection",
            "description": "Detects common SQL injection patterns",
            "enabled": True,
            "action": "block",
            "priority": 10,
            "threat_level": "high",
            "score": 90,
            "tags": ["sql_injection", "injection"],
            "conditions": [
                {
                    "target": "url",
                    "operator": "regex",
                    "value": r"(\b(union|select|insert|update|delete|drop)\b|'.*'.*=.*'.*')",
                    "case_sensitive": False
                }
            ]
        },
        {
            "id": "XSS_SCRIPT_TAG",
            "name": "XSS Script Tag Detection",
            "description": "Detects script tags in requests",
            "enabled": True,
            "action": "block",
            "priority": 10,
            "threat_level": "high",
            "score": 85,
            "tags": ["xss", "script_injection"],
            "conditions": [
                {
                    "target": "url",
                    "operator": "regex",
                    "value": r"<script[^>]*>.*?</script>",
                    "case_sensitive": False
                }
            ]
        },
        {
            "id": "SUSPICIOUS_USER_AGENT",
            "name": "Suspicious User Agent",
            "description": "Blocks requests with suspicious user agents",
            "enabled": True,
            "action": "block",
            "priority": 50,
            "threat_level": "medium",
            "score": 60,
            "tags": ["bot", "scanner"],
            "conditions": [
                {
                    "target": "user_agent",
                    "operator": "regex",
                    "value": r"(sqlmap|nmap|nikto|dirb|gobuster|wfuzz|burp|owasp)",
                    "case_sensitive": False
                }
            ]
        },
        {
            "id": "ADMIN_PATH_ACCESS",
            "name": "Admin Path Access",
            "description": "Monitors access to admin paths",
            "enabled": True,
            "action": "log",
            "priority": 30,
            "threat_level": "medium",
            "score": 40,
            "tags": ["admin", "privileged_access"],
            "conditions": [
                {
                    "target": "url",
                    "operator": "regex",
                    "value": r"/(admin|administrator|wp-admin|phpmyadmin|cpanel)",
                    "case_sensitive": False
                }
            ]
        },
        {
            "id": "LARGE_REQUEST_BODY",
            "name": "Large Request Body",
            "description": "Detects unusually large request bodies",
            "enabled": True,
            "action": "rate_limit",
            "priority": 40,
            "threat_level": "low",
            "score": 30,
            "rate_limit_window": 300,
            "rate_limit_threshold": 5,
            "tags": ["size_limit", "dos"],
            "conditions": [
                {
                    "target": "body",
                    "operator": "length_gt",
                    "value": 1048576  # 1MB
                }
            ]
        }
    ]
}