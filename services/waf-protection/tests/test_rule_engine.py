"""
Tests for Rule Engine
"""

import pytest
from src.core.rule_engine import (
    RuleEngine, CustomRule, RuleCondition, RuleAction, RuleTarget, 
    OperatorType, DEFAULT_RULES
)
from src.core.waf_engine import WAFRequest


@pytest.fixture
def rule_engine():
    """Create rule engine for testing"""
    engine = RuleEngine()
    engine.load_rules_from_dict(DEFAULT_RULES)
    return engine


@pytest.fixture
def test_request():
    """Create test request"""
    return WAFRequest(
        ip="192.168.1.100",
        method="GET",
        url="/search?q=test",
        headers={"User-Agent": "Mozilla/5.0", "Host": "example.com"},
        body=None
    )


@pytest.fixture
def malicious_request():
    """Create malicious request"""
    return WAFRequest(
        ip="192.168.1.100",
        method="GET",
        url="/search?q=' OR 1=1 --",
        headers={"User-Agent": "sqlmap/1.4.9"},
        body="<script>alert('xss')</script>"
    )


class TestRuleCondition:
    """Test rule condition matching"""
    
    def test_url_equals_condition(self, test_request):
        """Test URL equals condition"""
        condition = RuleCondition(
            target=RuleTarget.URL,
            operator=OperatorType.EQUALS,
            value="/search?q=test"
        )
        
        assert condition.matches(test_request)
        
        # Test non-matching
        condition.value = "/different/path"
        assert not condition.matches(test_request)
    
    def test_url_contains_condition(self, test_request):
        """Test URL contains condition"""
        condition = RuleCondition(
            target=RuleTarget.URL,
            operator=OperatorType.CONTAINS,
            value="search"
        )
        
        assert condition.matches(test_request)
        
        # Test non-matching
        condition.value = "nonexistent"
        assert not condition.matches(test_request)
    
    def test_url_regex_condition(self, malicious_request):
        """Test URL regex condition"""
        condition = RuleCondition(
            target=RuleTarget.URL,
            operator=OperatorType.REGEX,
            value=r"(\b(union|select|or)\b|'.*'.*=.*'.*')"
        )
        
        assert condition.matches(malicious_request)
    
    def test_header_condition(self, test_request):
        """Test header condition"""
        condition = RuleCondition(
            target=RuleTarget.HEADER,
            operator=OperatorType.CONTAINS,
            value="Mozilla",
            header_name="User-Agent"
        )
        
        assert condition.matches(test_request)
        
        # Test non-existent header
        condition.header_name = "NonExistent"
        assert not condition.matches(test_request)
    
    def test_ip_in_range_condition(self, test_request):
        """Test IP in range condition"""
        condition = RuleCondition(
            target=RuleTarget.IP,
            operator=OperatorType.IP_IN_RANGE,
            value="192.168.1.0/24"
        )
        
        assert condition.matches(test_request)
        
        # Test different range
        condition.value = "10.0.0.0/8"
        assert not condition.matches(test_request)
    
    def test_method_condition(self, test_request):
        """Test HTTP method condition"""
        condition = RuleCondition(
            target=RuleTarget.METHOD,
            operator=OperatorType.EQUALS,
            value="GET"
        )
        
        assert condition.matches(test_request)
        
        # Test non-matching method
        condition.value = "POST"
        assert not condition.matches(test_request)
    
    def test_body_condition(self, malicious_request):
        """Test body condition"""
        condition = RuleCondition(
            target=RuleTarget.BODY,
            operator=OperatorType.CONTAINS,
            value="script"
        )
        
        assert condition.matches(malicious_request)
    
    def test_length_conditions(self, test_request):
        """Test length-based conditions"""
        # URL length greater than
        condition = RuleCondition(
            target=RuleTarget.URL,
            operator=OperatorType.LENGTH_GT,
            value=5
        )
        
        assert condition.matches(test_request)
        
        # URL length less than
        condition.operator = OperatorType.LENGTH_LT
        condition.value = 100
        
        assert condition.matches(test_request)
    
    def test_in_list_condition(self, test_request):
        """Test in list condition"""
        condition = RuleCondition(
            target=RuleTarget.METHOD,
            operator=OperatorType.IN_LIST,
            value=["GET", "POST", "PUT"]
        )
        
        assert condition.matches(test_request)
        
        # Test not in list
        condition.operator = OperatorType.NOT_IN_LIST
        condition.value = ["DELETE", "PATCH"]
        
        assert condition.matches(test_request)
    
    def test_case_sensitivity(self, test_request):
        """Test case sensitivity option"""
        # Case insensitive (default)
        condition = RuleCondition(
            target=RuleTarget.URL,
            operator=OperatorType.CONTAINS,
            value="SEARCH",
            case_sensitive=False
        )
        
        assert condition.matches(test_request)
        
        # Case sensitive
        condition.case_sensitive = True
        assert not condition.matches(test_request)  # URL contains 'search', not 'SEARCH'


class TestCustomRule:
    """Test custom rule functionality"""
    
    def test_simple_rule_matching(self, test_request):
        """Test simple rule with single condition"""
        condition = RuleCondition(
            target=RuleTarget.URL,
            operator=OperatorType.CONTAINS,
            value="search"
        )
        
        rule = CustomRule(
            id="TEST_RULE_001",
            name="Test Search Rule",
            description="Test rule for search endpoints",
            enabled=True,
            action=RuleAction.LOG,
            conditions=[condition],
            priority=100,
            threat_level="low",
            score=30
        )
        
        assert rule.matches(test_request)
    
    def test_multiple_conditions_and_logic(self, malicious_request):
        """Test rule with multiple conditions (AND logic)"""
        condition1 = RuleCondition(
            target=RuleTarget.URL,
            operator=OperatorType.REGEX,
            value=r"(\bor\b|'.*'.*=.*'.*')"
        )
        
        condition2 = RuleCondition(
            target=RuleTarget.USER_AGENT,
            operator=OperatorType.CONTAINS,
            value="sqlmap"
        )
        
        rule = CustomRule(
            id="SQL_INJECTION_ADVANCED",
            name="Advanced SQL Injection Detection",
            description="Detects SQL injection with bot user agent",
            enabled=True,
            action=RuleAction.BLOCK,
            conditions=[condition1, condition2],
            priority=10,
            threat_level="high",
            score=90
        )
        
        assert rule.matches(malicious_request)
        
        # Test with request that matches only one condition
        legitimate_request = WAFRequest(
            ip="192.168.1.100",
            method="GET",
            url="/search?q=normal search",
            headers={"User-Agent": "sqlmap/1.4.9"},  # Only this matches
            body=None
        )
        
        assert not rule.matches(legitimate_request)  # AND logic - both must match
    
    def test_disabled_rule(self, test_request):
        """Test that disabled rules don't match"""
        condition = RuleCondition(
            target=RuleTarget.URL,
            operator=OperatorType.CONTAINS,
            value="search"
        )
        
        rule = CustomRule(
            id="DISABLED_RULE",
            name="Disabled Rule",
            description="This rule is disabled",
            enabled=False,  # Disabled
            action=RuleAction.BLOCK,
            conditions=[condition],
            priority=100,
            threat_level="medium",
            score=50
        )
        
        assert not rule.matches(test_request)


class TestRuleEngine:
    """Test rule engine functionality"""
    
    def test_load_default_rules(self, rule_engine):
        """Test loading default rules"""
        rules = rule_engine.list_rules()
        
        assert len(rules) > 0
        assert any(rule.id == "SQL_INJECTION_BASIC" for rule in rules)
        assert any(rule.id == "XSS_SCRIPT_TAG" for rule in rules)
    
    def test_evaluate_malicious_request(self, rule_engine, malicious_request):
        """Test evaluating malicious request against rules"""
        matched_rules = rule_engine.evaluate_request(malicious_request)
        
        assert len(matched_rules) > 0
        
        # Should match SQL injection rule
        sql_rule = next((rule for rule in matched_rules if "SQL_INJECTION" in rule.id), None)
        assert sql_rule is not None
        
        # Should match suspicious user agent rule
        bot_rule = next((rule for rule in matched_rules if "SUSPICIOUS_USER_AGENT" in rule.id), None)
        assert bot_rule is not None
    
    def test_evaluate_legitimate_request(self, rule_engine, test_request):
        """Test evaluating legitimate request"""
        matched_rules = rule_engine.evaluate_request(test_request)
        
        # Should not match blocking rules
        blocking_rules = [rule for rule in matched_rules if rule.action == RuleAction.BLOCK]
        assert len(blocking_rules) == 0
    
    def test_rule_priority_ordering(self, rule_engine):
        """Test that rules are evaluated in priority order"""
        # Add high priority rule
        high_priority_condition = RuleCondition(
            target=RuleTarget.URL,
            operator=OperatorType.CONTAINS,
            value="test"
        )
        
        high_priority_rule = CustomRule(
            id="HIGH_PRIORITY",
            name="High Priority Rule",
            description="High priority test rule",
            enabled=True,
            action=RuleAction.BLOCK,
            conditions=[high_priority_condition],
            priority=1,  # Very high priority
            threat_level="critical",
            score=100
        )
        
        rule_engine.add_rule(high_priority_rule)
        
        # Test request that matches both rules
        test_request = WAFRequest(
            ip="192.168.1.100",
            method="GET",
            url="/test?q=' OR 1=1 --",  # Matches both rules
            headers={"User-Agent": "Mozilla/5.0"},
            body=None
        )
        
        matched_rules = rule_engine.evaluate_request(test_request)
        
        # High priority rule should be first
        assert len(matched_rules) > 0
        assert matched_rules[0].id == "HIGH_PRIORITY"
        assert matched_rules[0].priority == 1
    
    def test_add_remove_rules(self, rule_engine):
        """Test adding and removing rules"""
        initial_count = len(rule_engine.list_rules())
        
        # Add new rule
        condition = RuleCondition(
            target=RuleTarget.URL,
            operator=OperatorType.CONTAINS,
            value="admin"
        )
        
        new_rule = CustomRule(
            id="ADMIN_ACCESS",
            name="Admin Access Rule",
            description="Monitors admin access",
            enabled=True,
            action=RuleAction.LOG,
            conditions=[condition],
            priority=50,
            threat_level="medium",
            score=40
        )
        
        rule_engine.add_rule(new_rule)
        assert len(rule_engine.list_rules()) == initial_count + 1
        
        # Verify rule was added
        retrieved_rule = rule_engine.get_rule("ADMIN_ACCESS")
        assert retrieved_rule is not None
        assert retrieved_rule.name == "Admin Access Rule"
        
        # Remove rule
        success = rule_engine.remove_rule("ADMIN_ACCESS")
        assert success
        assert len(rule_engine.list_rules()) == initial_count
        
        # Verify rule was removed
        retrieved_rule = rule_engine.get_rule("ADMIN_ACCESS")
        assert retrieved_rule is None
    
    def test_update_rule(self, rule_engine):
        """Test updating existing rule"""
        # Get existing rule
        original_rule = rule_engine.get_rule("SQL_INJECTION_BASIC")
        assert original_rule is not None
        
        # Create updated rule
        updated_rule = CustomRule(
            id="SQL_INJECTION_BASIC",
            name="Updated SQL Injection Rule",  # Changed name
            description="Updated description",  # Changed description
            enabled=False,  # Changed enabled status
            action=original_rule.action,
            conditions=original_rule.conditions,
            priority=original_rule.priority,
            threat_level=original_rule.threat_level,
            score=original_rule.score
        )
        
        # Update rule
        success = rule_engine.update_rule("SQL_INJECTION_BASIC", updated_rule)
        assert success
        
        # Verify update
        retrieved_rule = rule_engine.get_rule("SQL_INJECTION_BASIC")
        assert retrieved_rule.name == "Updated SQL Injection Rule"
        assert retrieved_rule.description == "Updated description"
        assert retrieved_rule.enabled == False
    
    def test_enable_disable_rules(self, rule_engine):
        """Test enabling and disabling rules"""
        rule_id = "SQL_INJECTION_BASIC"
        
        # Disable rule
        success = rule_engine.disable_rule(rule_id)
        assert success
        
        rule = rule_engine.get_rule(rule_id)
        assert not rule.enabled
        
        # Enable rule
        success = rule_engine.enable_rule(rule_id)
        assert success
        
        rule = rule_engine.get_rule(rule_id)
        assert rule.enabled
    
    def test_list_rules_filtering(self, rule_engine):
        """Test listing rules with filtering"""
        all_rules = rule_engine.list_rules()
        enabled_rules = rule_engine.list_rules(enabled_only=True)
        
        assert len(enabled_rules) <= len(all_rules)
        assert all(rule.enabled for rule in enabled_rules)
    
    def test_rule_statistics(self, rule_engine, malicious_request):
        """Test rule statistics collection"""
        # Get initial stats
        initial_stats = rule_engine.get_stats()
        initial_total = initial_stats["total_rules"]
        
        # Evaluate request to trigger rules
        matched_rules = rule_engine.evaluate_request(malicious_request)
        
        # Check updated stats
        updated_stats = rule_engine.get_stats()
        assert updated_stats["total_rules"] == initial_total
        assert updated_stats["enabled_rules"] <= updated_stats["total_rules"]
        
        # Check individual rule stats
        rule_stats = updated_stats["rule_stats"]
        for rule in matched_rules:
            if rule.id in rule_stats:
                assert rule_stats[rule.id]["matches"] > 0
    
    def test_export_import_rules(self, rule_engine):
        """Test exporting and importing rules"""
        # Export rules
        exported_data = rule_engine.export_rules()
        
        assert "rules" in exported_data
        assert len(exported_data["rules"]) > 0
        
        # Create new rule engine and import
        new_engine = RuleEngine()
        new_engine.load_rules_from_dict(exported_data)
        
        # Compare rule counts
        original_rules = rule_engine.list_rules()
        imported_rules = new_engine.list_rules()
        
        assert len(imported_rules) == len(original_rules)
        
        # Verify specific rule
        original_rule = rule_engine.get_rule("SQL_INJECTION_BASIC")
        imported_rule = new_engine.get_rule("SQL_INJECTION_BASIC")
        
        assert imported_rule is not None
        assert imported_rule.name == original_rule.name
        assert imported_rule.enabled == original_rule.enabled
    
    def test_invalid_regex_handling(self, rule_engine, test_request):
        """Test handling of invalid regex patterns"""
        # Create rule with invalid regex
        condition = RuleCondition(
            target=RuleTarget.URL,
            operator=OperatorType.REGEX,
            value="[invalid regex pattern"  # Invalid regex
        )
        
        rule = CustomRule(
            id="INVALID_REGEX",
            name="Invalid Regex Rule",
            description="Rule with invalid regex",
            enabled=True,
            action=RuleAction.BLOCK,
            conditions=[condition],
            priority=100,
            threat_level="medium",
            score=50
        )
        
        rule_engine.add_rule(rule)
        
        # Should not crash when evaluating
        matched_rules = rule_engine.evaluate_request(test_request)
        
        # Invalid regex rule should not match
        invalid_rule = next((r for r in matched_rules if r.id == "INVALID_REGEX"), None)
        assert invalid_rule is None
    
    def test_empty_conditions(self, rule_engine, test_request):
        """Test rule with empty conditions"""
        rule = CustomRule(
            id="EMPTY_CONDITIONS",
            name="Empty Conditions Rule",
            description="Rule with no conditions",
            enabled=True,
            action=RuleAction.LOG,
            conditions=[],  # Empty conditions
            priority=100,
            threat_level="low",
            score=10
        )
        
        rule_engine.add_rule(rule)
        
        # Should not match any request
        matched_rules = rule_engine.evaluate_request(test_request)
        empty_rule = next((r for r in matched_rules if r.id == "EMPTY_CONDITIONS"), None)
        assert empty_rule is None