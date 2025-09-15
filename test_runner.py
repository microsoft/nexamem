#!/usr/bin/env python3
"""Simple test runner to validate the existence tests."""

import sys
import traceback

def run_basic_tests():
    """Run basic tests to verify classes and methods exist."""
    print("Starting basic existence tests...")
    
    try:
        # Test 1: Package import
        print("✓ Test 1: Package import")
        import nexamem
        print(f"  - Package version: {nexamem.__version__}")
        
        # Test 2: Core classes
        print("✓ Test 2: Core classes")
        from nexamem import AIMemory, AsyncAIMemory, MemoryScope, ChatHistory
        print(f"  - AIMemory: {AIMemory}")
        print(f"  - AsyncAIMemory: {AsyncAIMemory}")
        print(f"  - MemoryScope: {MemoryScope}")
        print(f"  - ChatHistory: {ChatHistory}")
        
        # Test 3: Channel classes
        print("✓ Test 3: Channel classes")
        from nexamem import ChannelConfig, ChannelManager, ChannelAlreadyExists
        print(f"  - ChannelConfig: {ChannelConfig}")
        print(f"  - ChannelManager: {ChannelManager}")
        print(f"  - ChannelAlreadyExists: {ChannelAlreadyExists}")
        
        # Test 4: Policy classes
        print("✓ Test 4: Policy classes")
        from nexamem import PolicyEngine, PIIDetector, PolicyViolation, QuotaExceeded, EncryptionRequired, TTLViolation
        print(f"  - PolicyEngine: {PolicyEngine}")
        print(f"  - PIIDetector: {PIIDetector}")
        print(f"  - PolicyViolation: {PolicyViolation}")
        print(f"  - QuotaExceeded: {QuotaExceeded}")
        print(f"  - EncryptionRequired: {EncryptionRequired}")
        print(f"  - TTLViolation: {TTLViolation}")
        
        # Test 5: Content processing classes
        print("✓ Test 5: Content processing classes")
        from nexamem import ContentProcessorChain, PIIRedactor, ContentEnricher
        print(f"  - ContentProcessorChain: {ContentProcessorChain}")
        print(f"  - PIIRedactor: {PIIRedactor}")
        print(f"  - ContentEnricher: {ContentEnricher}")
        
        # Test 6: Audit classes
        print("✓ Test 6: Audit classes")
        from nexamem import AuditSink, AsyncAuditSink
        print(f"  - AuditSink: {AuditSink}")
        print(f"  - AsyncAuditSink: {AsyncAuditSink}")
        
        # Test 7: Metrics module
        print("✓ Test 7: Metrics module")
        from nexamem import metrics
        print(f"  - metrics module: {metrics}")
        
        # Test 8: Method existence on key classes
        print("✓ Test 8: Method existence")
        
        # AIMemory methods
        aimemory_methods = ['write', 'read', 'checkpoint', 'bulk_erase', 'count_bytes']
        for method in aimemory_methods:
            assert hasattr(AIMemory, method), f"AIMemory missing method: {method}"
        print(f"  - AIMemory has all expected methods: {aimemory_methods}")
        
        # MemoryScope methods
        scope_methods = ['get_key_prefix', 'get_index_key']
        for method in scope_methods:
            assert hasattr(MemoryScope, method), f"MemoryScope missing method: {method}"
        print(f"  - MemoryScope has all expected methods: {scope_methods}")
        
        # PolicyEngine methods
        policy_methods = ['validate_write', 'post_write_update']
        for method in policy_methods:
            assert hasattr(PolicyEngine, method), f"PolicyEngine missing method: {method}"
        print(f"  - PolicyEngine has all expected methods: {policy_methods}")
        
        # Test 9: Constants and enums
        print("✓ Test 9: Constants and enums")
        
        # PII patterns
        from nexamem.policy import PIIDetector
        assert hasattr(PIIDetector, 'PII_PATTERNS'), "PIIDetector missing PII_PATTERNS"
        patterns = PIIDetector.PII_PATTERNS
        expected_patterns = ['email', 'phone', 'ssn', 'credit_card']
        for pattern in expected_patterns:
            assert pattern in patterns, f"Missing PII pattern: {pattern}"
        print(f"  - PIIDetector has all expected patterns: {list(patterns.keys())}")
        
        # Test 10: Exception hierarchy
        print("✓ Test 10: Exception hierarchy")
        
        # Policy exceptions
        assert issubclass(QuotaExceeded, PolicyViolation), "QuotaExceeded should inherit from PolicyViolation"
        assert issubclass(EncryptionRequired, PolicyViolation), "EncryptionRequired should inherit from PolicyViolation"
        assert issubclass(TTLViolation, PolicyViolation), "TTLViolation should inherit from PolicyViolation"
        print("  - Policy exception hierarchy is correct")
        
        # Channel exceptions
        assert issubclass(ChannelAlreadyExists, Exception), "ChannelAlreadyExists should inherit from Exception"
        print("  - Channel exception hierarchy is correct")
        
        print("\n🎉 ALL TESTS PASSED! All expected classes, methods, and constants exist.")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_basic_tests()
    sys.exit(0 if success else 1)
