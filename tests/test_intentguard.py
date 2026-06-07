"""
IntentGuard - Test Suite
"""

import sys
from pathlib import Path

# Add intentguard root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.engine import verify_code, verify_file
from src.core.report import format_report
from src.analyzers.javascript_analyzer import JavaScriptAnalyzer, analyze_javascript_code
from src.analyzers.go_analyzer import GoAnalyzer, analyze_go_code


def test_basic_must_constraint():
    """Test MUST constraint"""
    code = '''
def send_sms(phone, message):
    sms_service.send(phone, message)
'''
    requirements = "必须发送短信通知"
    
    report = verify_code(code, requirements)
    
    assert report.summary["total"] == 1
    print("[PASS] test_basic_must_constraint")


def test_must_not_constraint():
    """Test MUST_NOT constraint"""
    code = '''
# Direct database operation
cursor.execute("SELECT * FROM users")
'''
    requirements = "禁止直接操作数据库"
    
    report = verify_code(code, requirements)
    
    assert report.summary["total"] == 1
    print("[PASS] test_must_not_constraint")


def test_conditional_constraint():
    """Test CONDITIONAL constraint"""
    code = '''
def create_order(user_id):
    if user_id <= 0:
        raise ValueError("Invalid user")
    
    order = save_order(user_id)
    send_sms(user.phone, "Order created")
'''
    requirements = "当订单创建时必须发送短信通知"
    
    report = verify_code(code, requirements)
    
    assert report.summary["total"] == 1
    print("[PASS] test_conditional_constraint")


def test_ecommerce_integration():
    """Integration test: E-commerce order service"""
    fixtures_dir = Path(__file__).parent / "fixtures"
    code_file = fixtures_dir / "ecommerce_order.py"
    req_file = fixtures_dir / "ecommerce_requirements.txt"
    
    report = verify_file(str(code_file), open(req_file, encoding="utf-8").read())
    
    print("\n" + "="*60)
    print("E-commerce Order Service Verification Report")
    print("="*60)
    print(format_report(report, "text"))
    
    assert report.summary["total"] > 0
    print("[PASS] test_ecommerce_integration")


def test_javascript_analyzer():
    """Test JavaScript analyzer"""
    code = '''
import logger from 'logger';

function sendSMS(phone, message) {
    logger.info(`Sending SMS to ${phone}`);
    smsService.send(phone, message);
}

async function createOrder(userId) {
    if (userId <= 0) {
        throw new Error("Invalid user");
    }
    
    const order = await db.save({ userId });
    sendSMS(user.phone, "Order created");
    
    return order;
}
'''
    
    context = analyze_javascript_code(code)
    
    assert len(context.functions) >= 2, f"Expected at least 2 functions, got {len(context.functions)}"
    assert len(context.calls) > 0, "Expected function calls"
    
    print(f"[PASS] test_javascript_analyzer (found {len(context.functions)} functions, {len(context.calls)} calls)")


def test_go_analyzer():
    """Test Go analyzer"""
    code = '''
package main

import "log"

type OrderService struct {
    db *DB
}

func NewOrderService(db *DB) *OrderService {
    return &OrderService{db: db}
}

func (s *OrderService) CreateOrder(userID, productID int) error {
    log.Printf("Creating order for user %d", userID)
    
    if userID <= 0 {
        return fmt.Errorf("invalid user ID")
    }
    
    err := s.db.Save(&Order{UserID: userID, ProductID: productID})
    if err != nil {
        return err
    }
    
    go s.sendNotification(userID)
    
    return nil
}

func (s *OrderService) sendNotification(userID int) {
    log.Printf("Sending notification for user %d", userID)
    smsService.Send(user.Phone, "Order created")
}
'''
    
    context = analyze_go_code(code)
    
    assert len(context.functions) >= 3, f"Expected at least 3 functions, got {len(context.functions)}"
    assert len(context.goroutines) >= 1, "Expected at least 1 goroutine"
    
    print(f"[PASS] test_go_analyzer (found {len(context.functions)} functions, {len(context.goroutines)} goroutines)")


def test_llm_factory():
    """Test LLM factory (without actually calling LLM)"""
    from src.llm.factory import LLMFactory, SiliconFlowProvider, DeepSeekProvider
    
    # Test provider registration
    sf = SiliconFlowProvider(api_key="test")
    LLMFactory.register("siliconflow", sf)
    
    provider = LLMFactory.get("siliconflow")
    assert provider is not None, "Provider should be registered"
    assert provider.name() == "SiliconFlow"
    
    # Test auto-detect (should return None without real API key)
    # provider = LLMFactory.auto_detect()  # Uncomment to test with real keys
    
    print("[PASS] test_llm_factory")


if __name__ == "__main__":
    print("Running IntentGuard tests...\n")
    
    test_basic_must_constraint()
    test_must_not_constraint()
    test_conditional_constraint()
    test_ecommerce_integration()
    test_javascript_analyzer()
    test_go_analyzer()
    test_llm_factory()
    
    print("\n[SUCCESS] All tests passed!")