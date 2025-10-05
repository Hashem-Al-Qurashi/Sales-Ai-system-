#!/usr/bin/env python3
"""
Architecture Validation Script

Validates that the implemented system follows ARCHITECTURE.md and DEVELOPMENT_RULES.md.
This is the "validation script" mentioned in DEVELOPMENT_RULES.md.
"""

import sys
import inspect
import importlib
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

@dataclass
class ValidationResult:
    """Validation result."""
    check_name: str
    passed: bool
    message: str
    severity: str = "ERROR"  # ERROR, WARNING, INFO


class ArchitectureValidator:
    """
    Validates system against ARCHITECTURE.md specifications.
    
    Implements the architectural compliance checking mentioned in
    DEVELOPMENT_RULES.md.
    """
    
    def __init__(self):
        self.results: List[ValidationResult] = []
    
    def validate_all(self) -> Tuple[bool, List[ValidationResult]]:
        """Run all architecture validations."""
        print("🔍 ARCHITECTURE VALIDATION - SENIOR ENGINEERING MODE")
        print("=" * 60)
        
        # Check 1: Configuration Over Code
        self.validate_configuration_system()
        
        # Check 2: Single Responsibility
        self.validate_single_responsibility()
        
        # Check 3: Data Flow Architecture
        self.validate_data_flow()
        
        # Check 4: Health Check Implementation
        self.validate_health_checks()
        
        # Check 5: Error Handling Hierarchy
        self.validate_error_handling()
        
        # Check 6: Storage Layer Interfaces
        self.validate_storage_interfaces()
        
        # Check 7: API Contracts
        self.validate_api_contracts()
        
        # Summary
        self.print_summary()
        
        passed = all(result.passed for result in self.results if result.severity == "ERROR")
        return passed, self.results
    
    def validate_configuration_system(self):
        """Validate Configuration Over Code principle."""
        print("\n📋 Validating Configuration System...")
        
        try:
            from hormozi_rag.config.settings import Settings, settings
            
            # Check: Simple class, not complex dataclasses
            if hasattr(Settings, '__dataclass_fields__'):
                self.results.append(ValidationResult(
                    "config_complexity",
                    False,
                    "Configuration uses complex dataclasses - violates simplicity principle",
                    "ERROR"
                ))
            else:
                self.results.append(ValidationResult(
                    "config_simplicity",
                    True,
                    "Configuration is simple class-based ✅",
                    "INFO"
                ))
            
            # Check: Environment-based configuration
            env_based = hasattr(settings, 'OPENAI_API_KEY') and hasattr(settings, 'CHUNK_SIZE')
            self.results.append(ValidationResult(
                "config_environment_based",
                env_based,
                "Configuration is environment-based ✅" if env_based else "Configuration not environment-based ❌",
                "ERROR" if not env_based else "INFO"
            ))
            
            # Check: Validation method exists
            has_validation = hasattr(Settings, 'validate')
            self.results.append(ValidationResult(
                "config_validation",
                has_validation,
                "Configuration has validation method ✅" if has_validation else "Missing validation method ❌",
                "ERROR" if not has_validation else "INFO"
            ))
            
            print("   ✅ Configuration system validated")
            
        except Exception as e:
            self.results.append(ValidationResult(
                "config_import",
                False,
                f"Failed to import configuration: {e}",
                "ERROR"
            ))
    
    def validate_single_responsibility(self):
        """Validate Single Responsibility Principle."""
        print("\n🎯 Validating Single Responsibility...")
        
        modules_to_check = [
            ('hormozi_rag.storage.interfaces', 'Storage interfaces'),
            ('hormozi_rag.generation.interfaces', 'Generation interfaces'),
            ('hormozi_rag.api.app', 'API application'),
        ]
        
        for module_name, description in modules_to_check:
            try:
                module = importlib.import_module(module_name)
                
                # Count classes - should be focused
                classes = [name for name, obj in inspect.getmembers(module, inspect.isclass)]
                
                if len(classes) > 10:
                    self.results.append(ValidationResult(
                        f"single_responsibility_{module_name}",
                        False,
                        f"{description} has too many classes ({len(classes)}) - violates SRP",
                        "WARNING"
                    ))
                else:
                    self.results.append(ValidationResult(
                        f"single_responsibility_{module_name}",
                        True,
                        f"{description} has focused responsibility ✅",
                        "INFO"
                    ))
                
            except ImportError as e:
                self.results.append(ValidationResult(
                    f"single_responsibility_{module_name}",
                    False,
                    f"Failed to import {module_name}: {e}",
                    "ERROR"
                ))
        
        print("   ✅ Single responsibility validated")
    
    def validate_data_flow(self):
        """Validate Data Flows One Way principle."""
        print("\n🔄 Validating Data Flow Architecture...")
        
        # Check: Storage interfaces exist
        try:
            from hormozi_rag.storage.interfaces import VectorDBInterface, DocumentStoreInterface, CacheInterface
            
            required_methods = {
                VectorDBInterface: ['search', 'add_documents', 'health_check'],
                CacheInterface: ['get', 'set', 'health_check'],
            }
            
            for interface, methods in required_methods.items():
                for method in methods:
                    has_method = hasattr(interface, method)
                    self.results.append(ValidationResult(
                        f"interface_{interface.__name__}_{method}",
                        has_method,
                        f"{interface.__name__}.{method} exists ✅" if has_method else f"Missing {interface.__name__}.{method} ❌",
                        "ERROR" if not has_method else "INFO"
                    ))
            
            print("   ✅ Data flow interfaces validated")
            
        except ImportError as e:
            self.results.append(ValidationResult(
                "data_flow_interfaces",
                False,
                f"Failed to import storage interfaces: {e}",
                "ERROR"
            ))
    
    def validate_health_checks(self):
        """Validate Health Check implementation."""
        print("\n🏥 Validating Health Check System...")
        
        try:
            from hormozi_rag.api.app import app
            
            # Check required health endpoints exist
            required_endpoints = ['/health/live', '/health/ready', '/health/startup']
            
            # Get all routes from FastAPI app
            routes = [route.path for route in app.routes if hasattr(route, 'path')]
            
            for endpoint in required_endpoints:
                exists = endpoint in routes
                self.results.append(ValidationResult(
                    f"health_endpoint_{endpoint.replace('/', '_')}",
                    exists,
                    f"Health endpoint {endpoint} exists ✅" if exists else f"Missing health endpoint {endpoint} ❌",
                    "ERROR" if not exists else "INFO"
                ))
            
            print("   ✅ Health check system validated")
            
        except Exception as e:
            self.results.append(ValidationResult(
                "health_checks",
                False,
                f"Failed to validate health checks: {e}",
                "ERROR"
            ))
    
    def validate_error_handling(self):
        """Validate Error Handling Hierarchy."""
        print("\n🚨 Validating Error Handling...")
        
        try:
            from hormozi_rag.generation.openai_provider import OpenAIProvider
            
            # Check if error handling methods exist
            provider = OpenAIProvider.__new__(OpenAIProvider)  # Don't call __init__
            
            # Check for retry logic
            has_retry = hasattr(provider, '_generate_with_retry')
            self.results.append(ValidationResult(
                "error_handling_retry",
                has_retry,
                "Error handling with retry logic exists ✅" if has_retry else "Missing retry logic ❌",
                "ERROR" if not has_retry else "INFO"
            ))
            
            print("   ✅ Error handling validated")
            
        except Exception as e:
            self.results.append(ValidationResult(
                "error_handling",
                False,
                f"Failed to validate error handling: {e}",
                "WARNING"
            ))
    
    def validate_storage_interfaces(self):
        """Validate Storage Layer implementation."""
        print("\n🗄️ Validating Storage Layer...")
        
        try:
            from hormozi_rag.storage.factory import StorageFactory
            
            # Check factory methods exist
            factory_methods = ['create_vector_db', 'create_cache']
            
            for method in factory_methods:
                has_method = hasattr(StorageFactory, method)
                self.results.append(ValidationResult(
                    f"storage_factory_{method}",
                    has_method,
                    f"StorageFactory.{method} exists ✅" if has_method else f"Missing StorageFactory.{method} ❌",
                    "ERROR" if not has_method else "INFO"
                ))
            
            print("   ✅ Storage layer validated")
            
        except ImportError as e:
            self.results.append(ValidationResult(
                "storage_layer",
                False,
                f"Failed to import storage layer: {e}",
                "ERROR"
            ))
    
    def validate_api_contracts(self):
        """Validate API Contracts."""
        print("\n📡 Validating API Contracts...")
        
        try:
            from hormozi_rag.api.app import QueryRequest, QueryResponse
            
            # Check Pydantic models exist
            contracts = [QueryRequest, QueryResponse]
            
            for contract in contracts:
                has_fields = hasattr(contract, '__fields__')
                self.results.append(ValidationResult(
                    f"api_contract_{contract.__name__}",
                    has_fields,
                    f"API contract {contract.__name__} properly defined ✅" if has_fields else f"Invalid API contract {contract.__name__} ❌",
                    "ERROR" if not has_fields else "INFO"
                ))
            
            print("   ✅ API contracts validated")
            
        except ImportError as e:
            self.results.append(ValidationResult(
                "api_contracts",
                False,
                f"Failed to import API contracts: {e}",
                "ERROR"
            ))
    
    def print_summary(self):
        """Print validation summary."""
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        
        errors = [r for r in self.results if r.severity == "ERROR" and not r.passed]
        warnings = [r for r in self.results if r.severity == "WARNING" and not r.passed]
        passed = [r for r in self.results if r.passed]
        
        print(f"   ✅ Passed: {len(passed)}")
        print(f"   ⚠️ Warnings: {len(warnings)}")
        print(f"   ❌ Errors: {len(errors)}")
        
        if errors:
            print("\n🔴 CRITICAL ERRORS:")
            for error in errors:
                print(f"   ❌ {error.check_name}: {error.message}")
        
        if warnings:
            print("\n🟡 WARNINGS:")
            for warning in warnings:
                print(f"   ⚠️ {warning.check_name}: {warning.message}")
        
        if not errors:
            print("\n🎉 ARCHITECTURE COMPLIANCE: PASSED")
            print("   All critical validations passed!")
        else:
            print("\n❌ ARCHITECTURE COMPLIANCE: FAILED")
            print(f"   {len(errors)} critical errors must be fixed")


def main():
    """Run architecture validation."""
    validator = ArchitectureValidator()
    passed, results = validator.validate_all()
    
    # Exit with appropriate code
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()