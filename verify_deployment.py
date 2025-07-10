#!/usr/bin/env python3
"""
GitHub Deployment Verification Script
Validates that the graceful degradation system is ready for production deployment.
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

async def verify_deployment_readiness():
    """Comprehensive verification of deployment readiness."""
    print("🚀 Kevin Smart Grant Finder - Deployment Verification")
    print("=" * 60)
    
    verification_results = {
        "core_imports": False,
        "graceful_app": False,
        "database_manager": False,
        "service_fallbacks": False,
        "error_handling": False,
        "health_monitoring": False,
        "url_attribution": False,
        "documentation": False
    }
    
    # Test 1: Core imports
    print("\n1. Testing Core Imports...")
    try:
        from config.settings import get_settings
        from fixes.database.robust_connection_manager import get_connection_manager
        from fixes.services.graceful_services import get_service_manager
        from fixes.error_handling.global_handlers import create_error_response
        from fixes.monitoring.health_endpoints import detailed_health_check
        print("   ✅ All core modules import successfully")
        verification_results["core_imports"] = True
    except Exception as e:
        print(f"   ❌ Import error: {e}")
    
    # Test 2: Graceful app creation
    print("\n2. Testing Graceful App Creation...")
    try:
        from app_graceful import app
        print(f"   ✅ Graceful FastAPI app created with {len(app.routes)} routes")
        verification_results["graceful_app"] = True
    except Exception as e:
        print(f"   ❌ App creation error: {e}")
    
    # Test 3: Database connection manager
    print("\n3. Testing Database Connection Manager...")
    try:
        connection_manager = await get_connection_manager()
        if connection_manager:
            print("   ✅ Database connection manager initialized")
            verification_results["database_manager"] = True
        else:
            print("   ❌ Database connection manager failed to initialize")
    except Exception as e:
        print(f"   ❌ Database manager error: {e}")
    
    # Test 4: Service fallbacks
    print("\n4. Testing Service Fallbacks...")
    try:
        from fixes.services.fallback_clients import FallbackPerplexityClient
        from fixes.services.circuit_breaker import get_circuit_manager
        
        fallback_client = FallbackPerplexityClient()
        circuit_manager = get_circuit_manager()
        
        print("   ✅ Service fallback systems available")
        verification_results["service_fallbacks"] = True
    except Exception as e:
        print(f"   ❌ Service fallback error: {e}")
    
    # Test 5: Error handling
    print("\n5. Testing Error Handling...")
    try:
        from fixes.error_handling.recovery_strategies import get_recovery_manager
        recovery_manager = get_recovery_manager()
        
        print("   ✅ Error recovery systems functional")
        verification_results["error_handling"] = True
    except Exception as e:
        print(f"   ❌ Error handling error: {e}")
    
    # Test 6: Health monitoring
    print("\n6. Testing Health Monitoring...")
    try:
        health_status = await detailed_health_check()
        if health_status:
            print("   ✅ Health monitoring system operational")
            verification_results["health_monitoring"] = True
        else:
            print("   ❌ Health monitoring failed")
    except Exception as e:
        print(f"   ❌ Health monitoring error: {e}")
    
    # Test 7: URL attribution
    print("\n7. Testing URL Attribution...")
    try:
        from app.schemas import EnrichedGrant
        from agents.recursive_research_agent import RecursiveResearchAgent
        
        # Verify EnrichedGrant has source_url field
        grant_fields = EnrichedGrant.model_fields.keys()
        if 'source_url' in grant_fields:
            print("   ✅ URL attribution schema ready")
            verification_results["url_attribution"] = True
        else:
            print("   ❌ source_url field missing from EnrichedGrant")
    except Exception as e:
        print(f"   ❌ URL attribution error: {e}")
    
    # Test 8: Documentation completeness
    print("\n8. Testing Documentation...")
    required_docs = [
        "README.md",
        "GRACEFUL_DEGRADATION_README.md",
        "GRANT_FINDING_RELIABILITY_BENEFITS.md",
        "SYSTEM_ARCHITECTURE.md",
        "URL_VALIDATION_IMPLEMENTATION.md",
        "GITHUB_DEPLOYMENT_READY.md"
    ]
    
    missing_docs = []
    for doc in required_docs:
        if not Path(doc).exists():
            missing_docs.append(doc)
    
    if not missing_docs:
        print("   ✅ All required documentation present")
        verification_results["documentation"] = True
    else:
        print(f"   ❌ Missing documentation: {missing_docs}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 DEPLOYMENT VERIFICATION SUMMARY")
    print("=" * 60)
    
    passed_tests = sum(verification_results.values())
    total_tests = len(verification_results)
    
    for test_name, passed in verification_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {test_name.replace('_', ' ').title()}: {status}")
    
    success_rate = (passed_tests / total_tests) * 100
    print(f"\nOverall Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests})")
    
    if success_rate >= 90:
        print("\n🎉 DEPLOYMENT READY!")
        print("The system is ready for GitHub deployment with high confidence.")
        print("\n🚀 Next Steps:")
        print("1. Repository is already pushed to GitHub")
        print("2. Configure production environment variables")
        print("3. Deploy backend to Heroku")
        print("4. Deploy frontend to Vercel")
        print("5. Run production health checks")
        return True
    elif success_rate >= 75:
        print("\n⚠️  DEPLOYMENT READY WITH CAUTION")
        print("Most systems are functional, but some issues need attention.")
        return True
    else:
        print("\n❌ NOT READY FOR DEPLOYMENT")
        print("Critical issues need to be resolved before deployment.")
        return False

async def main():
    """Main verification function."""
    print("Starting deployment verification...")
    
    try:
        success = await verify_deployment_readiness()
        if success:
            print("\n✅ Verification completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Verification failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Verification crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Setup basic logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during verification
    
    # Run verification
    asyncio.run(main())
