"""
Plugin Certification Service
"""

import ast
import asyncio
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import aiofiles
import subprocess
from pathlib import Path

from ..core.logging import get_logger
from ..models.schemas import PluginValidationResponse

logger = get_logger(__name__)


class CertificationService:
    """Service for plugin certification and validation"""
    
    def __init__(self):
        self.test_categories = {
            "security": {
                "weight": 0.3,
                "tests": [
                    "check_code_injection",
                    "check_file_access",
                    "check_network_access",
                    "check_sensitive_imports",
                    "check_eval_usage"
                ]
            },
            "quality": {
                "weight": 0.25,
                "tests": [
                    "check_code_complexity",
                    "check_documentation",
                    "check_error_handling",
                    "check_type_hints",
                    "check_naming_conventions"
                ]
            },
            "performance": {
                "weight": 0.2,
                "tests": [
                    "check_memory_usage",
                    "check_execution_time",
                    "check_resource_cleanup",
                    "check_async_usage"
                ]
            },
            "functionality": {
                "weight": 0.15,
                "tests": [
                    "check_plugin_structure",
                    "check_required_methods",
                    "check_metadata_validity",
                    "check_hook_implementations"
                ]
            },
            "compatibility": {
                "weight": 0.1,
                "tests": [
                    "check_mams_version",
                    "check_dependencies",
                    "check_python_version",
                    "check_api_compatibility"
                ]
            }
        }
    
    async def validate_plugin(self, plugin) -> PluginValidationResponse:
        """Run comprehensive validation on a plugin"""
        errors = []
        warnings = []
        suggestions = []
        
        try:
            # Get plugin source code
            plugin_path = self._get_plugin_path(plugin)
            
            if not plugin_path.exists():
                errors.append("Plugin source code not found")
                return PluginValidationResponse(
                    valid=False,
                    errors=errors,
                    warnings=warnings,
                    suggestions=suggestions
                )
            
            # Read plugin files
            source_code = await self._read_plugin_source(plugin_path)
            
            # Run validation tests
            security_results = await self._run_security_tests(source_code, plugin)
            quality_results = await self._run_quality_tests(source_code, plugin)
            performance_results = await self._run_performance_tests(source_code, plugin)
            functionality_results = await self._run_functionality_tests(source_code, plugin)
            compatibility_results = await self._run_compatibility_tests(source_code, plugin)
            
            # Combine results
            all_results = {
                **security_results,
                **quality_results,
                **performance_results,
                **functionality_results,
                **compatibility_results
            }
            
            # Categorize issues
            for test_name, result in all_results.items():
                if result.get("status") == "error":
                    errors.extend(result.get("messages", []))
                elif result.get("status") == "warning":
                    warnings.extend(result.get("messages", []))
                elif result.get("status") == "suggestion":
                    suggestions.extend(result.get("messages", []))
            
            # Add general suggestions
            if len(errors) == 0:
                suggestions.append("Consider adding more comprehensive error handling")
                suggestions.append("Add performance monitoring hooks")
                suggestions.append("Include unit tests for better quality assurance")
            
            is_valid = len(errors) == 0
            
            return PluginValidationResponse(
                valid=is_valid,
                errors=errors,
                warnings=warnings,
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"Plugin validation failed: {e}")
            errors.append(f"Validation failed: {str(e)}")
            
            return PluginValidationResponse(
                valid=False,
                errors=errors,
                warnings=warnings,
                suggestions=suggestions
            )
    
    async def run_certification_tests(self, cert_request, db):
        """Run comprehensive certification tests"""
        from ..db.models import CertificationTest, Plugin
        import uuid
        
        try:
            # Get plugin
            plugin_result = await db.execute(
                db.select(Plugin).where(Plugin.id == cert_request.plugin_id)
            )
            plugin = plugin_result.scalar_one()
            
            # Get plugin source
            plugin_path = self._get_plugin_path(plugin)
            source_code = await self._read_plugin_source(plugin_path)
            
            overall_score = 0
            test_count = 0
            
            # Run tests for each category
            for category, config in self.test_categories.items():
                category_score = 0
                category_tests = 0
                
                for test_name in config["tests"]:
                    test_result = await self._run_single_test(test_name, source_code, plugin)
                    
                    # Create test record
                    cert_test = CertificationTest(
                        id=str(uuid.uuid4()),
                        certification_id=cert_request.id,
                        test_name=test_name,
                        test_type=category,
                        status=test_result["status"],
                        score=test_result["score"],
                        details=test_result.get("details", {}),
                        completed_at=datetime.utcnow()
                    )
                    
                    db.add(cert_test)
                    
                    category_score += test_result["score"]
                    category_tests += 1
                
                # Weight category score
                if category_tests > 0:
                    weighted_score = (category_score / category_tests) * config["weight"]
                    overall_score += weighted_score
                    test_count += 1
            
            # Update certification request
            cert_request.overall_score = overall_score
            
            # Determine certification status
            if overall_score >= 90:
                cert_request.status = "certified"
                cert_request.certification_level = "premium"
            elif overall_score >= 75:
                cert_request.status = "certified"
                cert_request.certification_level = "standard"
            elif overall_score >= 60:
                cert_request.status = "certified"
                cert_request.certification_level = "basic"
            else:
                cert_request.status = "rejected"
                cert_request.reviewer_notes = f"Overall score {overall_score:.1f} below minimum threshold of 60"
            
            # Set expiration date (1 year for certified plugins)
            if cert_request.status == "certified":
                cert_request.expires_at = datetime.utcnow() + timedelta(days=365)
                cert_request.reviewed_at = datetime.utcnow()
            
            await db.commit()
            
            logger.info(f"Certification tests completed for {cert_request.id}, score: {overall_score:.1f}")
            
        except Exception as e:
            logger.error(f"Certification tests failed: {e}")
            cert_request.status = "failed"
            cert_request.reviewer_notes = f"Test execution failed: {str(e)}"
            await db.commit()
    
    async def _run_security_tests(self, source_code: str, plugin) -> Dict[str, Any]:
        """Run security validation tests"""
        results = {}
        
        # Check for code injection vulnerabilities
        results["check_code_injection"] = self._check_code_injection(source_code)
        
        # Check file access patterns
        results["check_file_access"] = self._check_file_access(source_code)
        
        # Check network access
        results["check_network_access"] = self._check_network_access(source_code)
        
        # Check sensitive imports
        results["check_sensitive_imports"] = self._check_sensitive_imports(source_code)
        
        # Check eval usage
        results["check_eval_usage"] = self._check_eval_usage(source_code)
        
        return results
    
    async def _run_quality_tests(self, source_code: str, plugin) -> Dict[str, Any]:
        """Run code quality tests"""
        results = {}
        
        # Check code complexity
        results["check_code_complexity"] = self._check_code_complexity(source_code)
        
        # Check documentation
        results["check_documentation"] = self._check_documentation(source_code)
        
        # Check error handling
        results["check_error_handling"] = self._check_error_handling(source_code)
        
        # Check type hints
        results["check_type_hints"] = self._check_type_hints(source_code)
        
        # Check naming conventions
        results["check_naming_conventions"] = self._check_naming_conventions(source_code)
        
        return results
    
    async def _run_performance_tests(self, source_code: str, plugin) -> Dict[str, Any]:
        """Run performance tests"""
        results = {}
        
        # Check memory usage patterns
        results["check_memory_usage"] = self._check_memory_usage(source_code)
        
        # Check execution time patterns
        results["check_execution_time"] = self._check_execution_time(source_code)
        
        # Check resource cleanup
        results["check_resource_cleanup"] = self._check_resource_cleanup(source_code)
        
        # Check async usage
        results["check_async_usage"] = self._check_async_usage(source_code)
        
        return results
    
    async def _run_functionality_tests(self, source_code: str, plugin) -> Dict[str, Any]:
        """Run functionality tests"""
        results = {}
        
        # Check plugin structure
        results["check_plugin_structure"] = self._check_plugin_structure(source_code)
        
        # Check required methods
        results["check_required_methods"] = self._check_required_methods(source_code)
        
        # Check metadata validity
        results["check_metadata_validity"] = self._check_metadata_validity(plugin)
        
        # Check hook implementations
        results["check_hook_implementations"] = self._check_hook_implementations(source_code)
        
        return results
    
    async def _run_compatibility_tests(self, source_code: str, plugin) -> Dict[str, Any]:
        """Run compatibility tests"""
        results = {}
        
        # Check MAMS version compatibility
        results["check_mams_version"] = self._check_mams_version(plugin)
        
        # Check dependencies
        results["check_dependencies"] = self._check_dependencies(source_code)
        
        # Check Python version compatibility
        results["check_python_version"] = self._check_python_version(source_code)
        
        # Check API compatibility
        results["check_api_compatibility"] = self._check_api_compatibility(source_code)
        
        return results
    
    async def _run_single_test(self, test_name: str, source_code: str, plugin) -> Dict[str, Any]:
        """Run a single certification test"""
        try:
            if hasattr(self, f"_{test_name}"):
                test_method = getattr(self, f"_{test_name}")
                if test_name in ["check_metadata_validity", "check_mams_version"]:
                    return test_method(plugin)
                else:
                    return test_method(source_code)
            else:
                return {
                    "status": "error",
                    "score": 0,
                    "details": {"error": f"Test method {test_name} not found"}
                }
        except Exception as e:
            return {
                "status": "error",
                "score": 0,
                "details": {"error": str(e)}
            }
    
    def _get_plugin_path(self, plugin) -> Path:
        """Get the filesystem path for a plugin"""
        # This would need to be configured based on your plugin storage
        return Path(f"/plugins/{plugin.plugin_id}")
    
    async def _read_plugin_source(self, plugin_path: Path) -> str:
        """Read plugin source code"""
        source_files = []
        
        # Read all Python files in the plugin directory
        for py_file in plugin_path.glob("**/*.py"):
            try:
                async with aiofiles.open(py_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    source_files.append(content)
            except Exception as e:
                logger.warning(f"Failed to read {py_file}: {e}")
        
        return "\n".join(source_files)
    
    # Security test implementations
    def _check_code_injection(self, source_code: str) -> Dict[str, Any]:
        """Check for potential code injection vulnerabilities"""
        dangerous_patterns = [
            r'exec\s*\(',
            r'eval\s*\(',
            r'__import__\s*\(',
            r'compile\s*\(',
            r'globals\s*\(\)',
            r'locals\s*\(\)'
        ]
        
        issues = []
        for pattern in dangerous_patterns:
            if re.search(pattern, source_code, re.IGNORECASE):
                issues.append(f"Dangerous pattern found: {pattern}")
        
        if issues:
            return {
                "status": "error",
                "score": 0,
                "messages": issues,
                "details": {"dangerous_patterns": issues}
            }
        
        return {"status": "pass", "score": 100}
    
    def _check_file_access(self, source_code: str) -> Dict[str, Any]:
        """Check file access patterns"""
        suspicious_patterns = [
            r'open\s*\([^)]*["\']\/[^"\']*["\']',  # Absolute paths
            r'os\.system\s*\(',
            r'subprocess\.',
            r'\.\.\/.*'  # Parent directory access
        ]
        
        warnings = []
        for pattern in suspicious_patterns:
            if re.search(pattern, source_code):
                warnings.append(f"Potentially unsafe file access: {pattern}")
        
        if warnings:
            return {
                "status": "warning",
                "score": 70,
                "messages": warnings,
                "details": {"file_access_patterns": warnings}
            }
        
        return {"status": "pass", "score": 100}
    
    def _check_network_access(self, source_code: str) -> Dict[str, Any]:
        """Check network access patterns"""
        network_imports = [
            r'import\s+urllib',
            r'import\s+requests',
            r'import\s+socket',
            r'import\s+http',
            r'from\s+urllib',
            r'from\s+requests'
        ]
        
        network_usage = []
        for pattern in network_imports:
            if re.search(pattern, source_code):
                network_usage.append(pattern)
        
        if network_usage:
            return {
                "status": "warning",
                "score": 80,
                "messages": ["Plugin makes network requests - ensure proper error handling"],
                "details": {"network_imports": network_usage}
            }
        
        return {"status": "pass", "score": 100}
    
    def _check_sensitive_imports(self, source_code: str) -> Dict[str, Any]:
        """Check for sensitive or dangerous imports"""
        dangerous_imports = [
            r'import\s+os',
            r'import\s+sys',
            r'import\s+subprocess',
            r'from\s+os\s+import',
            r'from\s+sys\s+import',
            r'import\s+ctypes'
        ]
        
        found_imports = []
        for pattern in dangerous_imports:
            if re.search(pattern, source_code):
                found_imports.append(pattern)
        
        if found_imports:
            return {
                "status": "warning",
                "score": 60,
                "messages": ["Plugin uses potentially dangerous system imports"],
                "details": {"dangerous_imports": found_imports}
            }
        
        return {"status": "pass", "score": 100}
    
    def _check_eval_usage(self, source_code: str) -> Dict[str, Any]:
        """Check for eval/exec usage"""
        if re.search(r'\beval\s*\(|\bexec\s*\(', source_code):
            return {
                "status": "error",
                "score": 0,
                "messages": ["Plugin uses eval() or exec() which is prohibited"],
                "details": {"violation": "eval_exec_usage"}
            }
        
        return {"status": "pass", "score": 100}
    
    # Quality test implementations
    def _check_code_complexity(self, source_code: str) -> Dict[str, Any]:
        """Check code complexity"""
        try:
            tree = ast.parse(source_code)
            complexity_score = self._calculate_complexity(tree)
            
            if complexity_score > 20:
                return {
                    "status": "warning",
                    "score": 50,
                    "messages": [f"High code complexity: {complexity_score}"],
                    "details": {"complexity": complexity_score}
                }
            elif complexity_score > 10:
                return {
                    "status": "suggestion",
                    "score": 75,
                    "messages": ["Consider refactoring for better maintainability"],
                    "details": {"complexity": complexity_score}
                }
            
            return {"status": "pass", "score": 100, "details": {"complexity": complexity_score}}
            
        except SyntaxError:
            return {
                "status": "error",
                "score": 0,
                "messages": ["Code has syntax errors"],
                "details": {"error": "syntax_error"}
            }
    
    def _check_documentation(self, source_code: str) -> Dict[str, Any]:
        """Check documentation quality"""
        docstring_count = len(re.findall(r'""".*?"""', source_code, re.DOTALL))
        function_count = len(re.findall(r'def\s+\w+', source_code))
        class_count = len(re.findall(r'class\s+\w+', source_code))
        
        expected_docs = function_count + class_count
        doc_coverage = docstring_count / max(expected_docs, 1)
        
        if doc_coverage < 0.5:
            return {
                "status": "warning",
                "score": 60,
                "messages": ["Low documentation coverage"],
                "details": {"coverage": doc_coverage}
            }
        elif doc_coverage < 0.8:
            return {
                "status": "suggestion",
                "score": 80,
                "messages": ["Consider adding more documentation"],
                "details": {"coverage": doc_coverage}
            }
        
        return {"status": "pass", "score": 100, "details": {"coverage": doc_coverage}}
    
    def _check_error_handling(self, source_code: str) -> Dict[str, Any]:
        """Check error handling patterns"""
        try_count = len(re.findall(r'\btry\s*:', source_code))
        function_count = len(re.findall(r'def\s+\w+', source_code))
        
        if function_count > 5 and try_count == 0:
            return {
                "status": "warning",
                "score": 70,
                "messages": ["No error handling found in plugin"],
                "details": {"try_blocks": try_count, "functions": function_count}
            }
        
        return {"status": "pass", "score": 100}
    
    def _check_type_hints(self, source_code: str) -> Dict[str, Any]:
        """Check for type hints usage"""
        type_hint_patterns = [
            r'def\s+\w+\([^)]*:\s*\w+',
            r'->\s*\w+:',
            r':\s*\w+\s*=',
            r'from\s+typing\s+import'
        ]
        
        has_type_hints = any(re.search(pattern, source_code) for pattern in type_hint_patterns)
        
        if not has_type_hints:
            return {
                "status": "suggestion",
                "score": 85,
                "messages": ["Consider adding type hints for better code quality"],
                "details": {"has_type_hints": False}
            }
        
        return {"status": "pass", "score": 100}
    
    def _check_naming_conventions(self, source_code: str) -> Dict[str, Any]:
        """Check naming conventions"""
        # Check for PEP 8 naming conventions
        violations = []
        
        # Check class names (should be CamelCase)
        classes = re.findall(r'class\s+(\w+)', source_code)
        for class_name in classes:
            if not re.match(r'^[A-Z][a-zA-Z0-9]*$', class_name):
                violations.append(f"Class name '{class_name}' should be CamelCase")
        
        # Check function names (should be snake_case)
        functions = re.findall(r'def\s+(\w+)', source_code)
        for func_name in functions:
            if not re.match(r'^[a-z_][a-z0-9_]*$', func_name):
                violations.append(f"Function name '{func_name}' should be snake_case")
        
        if violations:
            return {
                "status": "suggestion",
                "score": 90,
                "messages": violations[:3],  # Limit to first 3 violations
                "details": {"violations": violations}
            }
        
        return {"status": "pass", "score": 100}
    
    # Performance test implementations
    def _check_memory_usage(self, source_code: str) -> Dict[str, Any]:
        """Check for potential memory issues"""
        memory_concerns = []
        
        # Check for large data structures
        if re.search(r'range\s*\(\s*\d{6,}', source_code):
            memory_concerns.append("Large range() usage detected")
        
        # Check for file reading without context managers
        if re.search(r'open\s*\([^)]*\)(?!\s*as\s|\s*\):\s*with)', source_code):
            memory_concerns.append("File operations without context managers")
        
        if memory_concerns:
            return {
                "status": "warning",
                "score": 75,
                "messages": memory_concerns,
                "details": {"concerns": memory_concerns}
            }
        
        return {"status": "pass", "score": 100}
    
    def _check_execution_time(self, source_code: str) -> Dict[str, Any]:
        """Check for potential performance issues"""
        performance_issues = []
        
        # Check for nested loops
        nested_loops = len(re.findall(r'for\s+.*?:\s*.*?for\s+', source_code, re.DOTALL))
        if nested_loops > 2:
            performance_issues.append(f"Multiple nested loops detected: {nested_loops}")
        
        # Check for synchronous I/O in async context
        if 'async def' in source_code and re.search(r'(?<!await\s)requests\.', source_code):
            performance_issues.append("Synchronous requests in async function")
        
        if performance_issues:
            return {
                "status": "warning",
                "score": 80,
                "messages": performance_issues,
                "details": {"issues": performance_issues}
            }
        
        return {"status": "pass", "score": 100}
    
    def _check_resource_cleanup(self, source_code: str) -> Dict[str, Any]:
        """Check for proper resource cleanup"""
        cleanup_score = 100
        issues = []
        
        # Check for context managers usage
        open_calls = len(re.findall(r'open\s*\(', source_code))
        with_statements = len(re.findall(r'with\s+.*?open\s*\(', source_code))
        
        if open_calls > 0 and with_statements == 0:
            cleanup_score = 70
            issues.append("File operations should use context managers")
        
        return {
            "status": "pass" if cleanup_score == 100 else "warning",
            "score": cleanup_score,
            "messages": issues,
            "details": {"open_calls": open_calls, "with_statements": with_statements}
        }
    
    def _check_async_usage(self, source_code: str) -> Dict[str, Any]:
        """Check async/await usage"""
        has_async = 'async def' in source_code
        has_await = 'await ' in source_code
        
        if has_async and not has_await:
            return {
                "status": "warning",
                "score": 80,
                "messages": ["Async functions should use await for I/O operations"],
                "details": {"has_async": has_async, "has_await": has_await}
            }
        
        return {"status": "pass", "score": 100}
    
    # Functionality test implementations
    def _check_plugin_structure(self, source_code: str) -> Dict[str, Any]:
        """Check plugin structure requirements"""
        required_elements = {
            "class": r'class\s+\w+.*Plugin',
            "init": r'def\s+__init__',
            "execute": r'def\s+execute'
        }
        
        missing = []
        for element, pattern in required_elements.items():
            if not re.search(pattern, source_code):
                missing.append(element)
        
        if missing:
            return {
                "status": "error",
                "score": 0,
                "messages": [f"Missing required elements: {', '.join(missing)}"],
                "details": {"missing": missing}
            }
        
        return {"status": "pass", "score": 100}
    
    def _check_required_methods(self, source_code: str) -> Dict[str, Any]:
        """Check for required plugin methods"""
        required_methods = ['initialize', 'execute', 'cleanup']
        missing_methods = []
        
        for method in required_methods:
            if not re.search(rf'def\s+{method}\s*\(', source_code):
                missing_methods.append(method)
        
        if missing_methods:
            return {
                "status": "error",
                "score": 0,
                "messages": [f"Missing required methods: {', '.join(missing_methods)}"],
                "details": {"missing_methods": missing_methods}
            }
        
        return {"status": "pass", "score": 100}
    
    def _check_metadata_validity(self, plugin) -> Dict[str, Any]:
        """Check plugin metadata validity"""
        required_fields = ['name', 'version', 'description', 'author']
        missing_fields = []
        
        for field in required_fields:
            if not getattr(plugin, field, None):
                missing_fields.append(field)
        
        if missing_fields:
            return {
                "status": "error",
                "score": 0,
                "messages": [f"Missing required metadata: {', '.join(missing_fields)}"],
                "details": {"missing_fields": missing_fields}
            }
        
        return {"status": "pass", "score": 100}
    
    def _check_hook_implementations(self, source_code: str) -> Dict[str, Any]:
        """Check hook implementations"""
        hook_patterns = [
            r'@hook\s*\(',
            r'register_hook\s*\(',
            r'def\s+on_\w+'
        ]
        
        has_hooks = any(re.search(pattern, source_code) for pattern in hook_patterns)
        
        if not has_hooks:
            return {
                "status": "suggestion",
                "score": 90,
                "messages": ["Consider implementing event hooks for better integration"],
                "details": {"has_hooks": False}
            }
        
        return {"status": "pass", "score": 100}
    
    # Compatibility test implementations
    def _check_mams_version(self, plugin) -> Dict[str, Any]:
        """Check MAMS version compatibility"""
        min_version = getattr(plugin, 'min_mams_version', None)
        max_version = getattr(plugin, 'max_mams_version', None)
        
        if not min_version:
            return {
                "status": "warning",
                "score": 80,
                "messages": ["No minimum MAMS version specified"],
                "details": {"min_version": None}
            }
        
        # Version format validation
        version_pattern = r'^\d+\.\d+\.\d+$'
        if not re.match(version_pattern, min_version):
            return {
                "status": "error",
                "score": 0,
                "messages": ["Invalid version format"],
                "details": {"min_version": min_version}
            }
        
        return {"status": "pass", "score": 100}
    
    def _check_dependencies(self, source_code: str) -> Dict[str, Any]:
        """Check plugin dependencies"""
        imports = re.findall(r'(?:from\s+(\w+)|import\s+(\w+))', source_code)
        external_imports = []
        
        stdlib_modules = {
            'os', 'sys', 'json', 'datetime', 'typing', 'asyncio', 'pathlib',
            're', 'math', 'random', 'collections', 'itertools', 'functools'
        }
        
        for from_import, direct_import in imports:
            module = from_import or direct_import
            if module and module not in stdlib_modules and not module.startswith('mams'):
                external_imports.append(module)
        
        if external_imports:
            return {
                "status": "warning",
                "score": 85,
                "messages": ["Plugin has external dependencies"],
                "details": {"external_imports": list(set(external_imports))}
            }
        
        return {"status": "pass", "score": 100}
    
    def _check_python_version(self, source_code: str) -> Dict[str, Any]:
        """Check Python version compatibility"""
        # Check for Python 3.8+ features
        modern_features = [
            r':=',  # Walrus operator (3.8+)
            r'typing\.TypedDict',  # TypedDict (3.8+)
            r'match\s+\w+:',  # Pattern matching (3.10+)
        ]
        
        advanced_features = []
        for feature in modern_features:
            if re.search(feature, source_code):
                advanced_features.append(feature)
        
        if advanced_features:
            return {
                "status": "suggestion",
                "score": 95,
                "messages": ["Plugin uses modern Python features"],
                "details": {"features": advanced_features}
            }
        
        return {"status": "pass", "score": 100}
    
    def _check_api_compatibility(self, source_code: str) -> Dict[str, Any]:
        """Check API compatibility"""
        # Check for proper MAMS API usage
        api_imports = re.findall(r'from\s+mams\.(\w+)', source_code)
        
        if not api_imports:
            return {
                "status": "warning",
                "score": 70,
                "messages": ["Plugin doesn't use MAMS API"],
                "details": {"api_imports": []}
            }
        
        return {"status": "pass", "score": 100}
    
    def _calculate_complexity(self, tree) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1  # Base complexity
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor,
                               ast.ExceptHandler, ast.With, ast.AsyncWith)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
        
        return complexity