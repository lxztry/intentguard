"""
IntentGuard - Enhanced Constraint Engine

支持多层级验证（静态 + LLM语义）
"""

import os
from typing import List, Optional, Literal

from .constraint import Constraint, ConstraintType, VerificationResult, VerificationReport, Priority
from ..analyzers.python_analyzer import PythonAnalyzer, CodeContext
from ..parser.pattern_parser import RequirementParser, parse_requirements
from ..llm.semantic import SemanticVerifier


class VerificationLevel:
    """验证级别"""
    STATIC = "static"           # Level 1: 静态模式匹配
    SEMANTIC = "semantic"       # Level 2: LLM语义验证
    DEEP = "deep"              # Level 3: 深度推理


class EnhancedConstraintEngine:
    """增强约束引擎 - 支持多层级验证"""
    
    def __init__(self, analyzer: PythonAnalyzer, llm_enabled: bool = True):
        self.analyzer = analyzer
        self.context: Optional[CodeContext] = None
        self.llm_enabled = llm_enabled and self._check_llm_available()
        self.semantic_verifier: Optional[SemanticVerifier] = None
        
        if self.llm_enabled:
            from ..llm.factory import setup_llm
            provider = setup_llm()
            if provider:
                self.semantic_verifier = SemanticVerifier(provider)
    
    def _check_llm_available(self) -> bool:
        """检查LLM是否可用"""
        return bool(
            os.getenv("SILICONFLOW_API_KEY") or
            os.getenv("DEEPSEEK_API_KEY") or
            os.getenv("OPENAI_API_KEY")
        )
    
    def verify(
        self, 
        constraints: List[Constraint], 
        code_context: CodeContext,
        level: Literal["static", "semantic", "deep"] = "semantic"
    ) -> VerificationReport:
        """
        验证约束
        
        Args:
            constraints: 约束列表
            code_context: 代码上下文
            level: 验证级别
                      - static: 只用静态分析（快速）
                      - semantic: 静态+LLM（平衡）
                      - deep: 以LLM为主（深度但慢）
        """
        self.context = code_context
        results = []
        
        for constraint in constraints:
            result = self._check_constraint(constraint, level)
            results.append(result)
        
        return VerificationReport(
            constraints=constraints,
            results=results,
            code_path=code_context.file_path,
            requirements_text="\n".join(c.source_line for c in constraints)
        )
    
    def _check_constraint(self, constraint: Constraint, level: str) -> VerificationResult:
        """检查单个约束"""
        
        # 首先尝试静态验证
        static_result = self._static_verify(constraint)
        
        if static_result.status == "passed":
            return static_result
        
        # 如果静态未通过且指定了semantic/deep级别，尝试LLM
        if level in ("semantic", "deep") and self.llm_enabled and self.semantic_verifier:
            relevant_code = self._get_relevant_code(constraint)
            llm_result = self.semantic_verifier.verify(constraint, self.context, relevant_code)
            
            return VerificationResult(
                constraint=constraint,
                status=llm_result["status"],
                reason=llm_result.get("reason"),
                suggestion=llm_result.get("suggestion"),
                matched_code=None,
                line_number=None
            )
        
        # 降级到静态结果
        return static_result
    
    def _static_verify(self, constraint: Constraint) -> VerificationResult:
        """静态验证（Level 1）"""
        
        if constraint.type == ConstraintType.MUST:
            return self._verify_must(constraint)
        elif constraint.type == ConstraintType.MUST_NOT:
            return self._verify_must_not(constraint)
        elif constraint.type == ConstraintType.CONDITIONAL:
            return self._verify_conditional(constraint)
        elif constraint.type == ConstraintType.EXISTS:
            return self._verify_exists(constraint)
        elif constraint.type == ConstraintType.LTE:
            return self._verify_lte(constraint)
        elif constraint.type == ConstraintType.GTE:
            return self._verify_gte(constraint)
        else:
            return VerificationResult(
                constraint=constraint,
                status="uncertain",
                reason=f"Unknown constraint type: {constraint.type}"
            )
    
    def _verify_must(self, constraint: Constraint) -> VerificationResult:
        """验证 MUST 约束"""
        keywords = set()
        keywords.update(constraint.verification_hints)
        keywords.add(constraint.predicate.lower())
        
        # 搜索匹配的调用
        matched_calls = []
        for keyword in keywords:
            for call in self.context.calls:
                if keyword.lower() in call.name.lower():
                    matched_calls.append(call)
        
        # 去重
        seen_lines = set()
        unique_calls = []
        for call in matched_calls:
            if call.lineno not in seen_lines:
                seen_lines.add(call.lineno)
                unique_calls.append(call)
        
        if unique_calls:
            best_call = unique_calls[0]
            return VerificationResult(
                constraint=constraint,
                status="passed",
                matched_code=self.analyzer.get_code_at_line(best_call.lineno),
                line_number=best_call.lineno,
                reason=f"Found {constraint.predicate} call: {best_call.name}"
            )
        
        # 尝试用函数名匹配
        for func in self.context.functions:
            func_name_lower = func.name.lower()
            if any(k in func_name_lower for k in keywords):
                return VerificationResult(
                    constraint=constraint,
                    status="passed",
                    matched_code=f"def {func.name}(...)",
                    line_number=func.lineno,
                    reason=f"Found function: {func.name}"
                )
        
        return VerificationResult(
            constraint=constraint,
            status="failed",
            reason=f"未找到 '{constraint.predicate}' 相关实现",
            suggestion=f"请确保代码中包含 {constraint.predicate} 的实现"
        )
    
    def _verify_must_not(self, constraint: Constraint) -> VerificationResult:
        """验证 MUST_NOT 约束"""
        keywords = constraint.verification_hints.copy()
        
        forbidden_patterns = []
        for hint in keywords:
            if "db" in hint.lower() or "database" in hint.lower() or "sql" in hint.lower():
                forbidden_patterns.extend(["db.", "sql", "cursor", "execute"])
            if "直接" in constraint.source_line.lower():
                forbidden_patterns.extend(["cursor.execute", "db.execute", "raw_sql"])
        
        for call in self.context.calls:
            for pattern in forbidden_patterns:
                if pattern.lower() in call.name.lower():
                    return VerificationResult(
                        constraint=constraint,
                        status="failed",
                        matched_code=self.analyzer.get_code_at_line(call.lineno),
                        line_number=call.lineno,
                        reason=f"Found forbidden pattern: {call.name}",
                        suggestion="请通过 ORM 或 Repository 层访问数据库"
                    )
        
        return VerificationResult(
            constraint=constraint,
            status="passed",
            reason="No forbidden patterns found"
        )
    
    def _verify_conditional(self, constraint: Constraint) -> VerificationResult:
        """验证 CONDITIONAL 约束"""
        condition_keyword = constraint.condition or ""
        
        for cond in self.context.conditions:
            if condition_keyword.lower() in cond.condition_expr.lower():
                body_calls = [c for c in self.context.calls 
                             if cond.body_lines[0] <= c.lineno <= (cond.body_lines[-1] if cond.body_lines else cond.lineno)]
                
                for call in body_calls:
                    if any(k in call.name.lower() for k in constraint.verification_hints):
                        return VerificationResult(
                            constraint=constraint,
                            status="passed",
                            matched_code=self.analyzer.get_code_at_line(call.lineno),
                            line_number=call.lineno,
                            reason=f"Condition satisfied, {constraint.predicate} executed"
                        )
                
                return VerificationResult(
                    constraint=constraint,
                    status="failed",
                    reason=f"Condition '{condition_keyword}' found but {constraint.predicate} not executed",
                    suggestion=f"在 {cond.condition_type} 条件体内添加 {constraint.predicate}",
                    line_number=cond.lineno
                )
        
        return VerificationResult(
            constraint=constraint,
            status="failed",
            reason=f"Condition not found: {condition_keyword}",
            suggestion=f"请添加条件：当 {condition_keyword} 时执行 {constraint.predicate}"
        )
    
    def _verify_exists(self, constraint: Constraint) -> VerificationResult:
        """验证 EXISTS 约束"""
        return self._verify_must(constraint)
    
    def _verify_lte(self, constraint: Constraint) -> VerificationResult:
        """验证 LTE 约束"""
        return VerificationResult(
            constraint=constraint,
            status="uncertain",
            reason="LTE constraint requires numeric analysis (use LLM for deep verification)"
        )
    
    def _verify_gte(self, constraint: Constraint) -> VerificationResult:
        """验证 GTE 约束"""
        return VerificationResult(
            constraint=constraint,
            status="uncertain",
            reason="GTE constraint requires numeric analysis (use LLM for deep verification)"
        )
    
    def _get_relevant_code(self, constraint: Constraint) -> str:
        """获取相关代码片段"""
        lines = []
        
        # 获取匹配的函数
        for func in self.context.functions:
            lines.append(self.analyzer.get_code_at_line(func.lineno))
        
        # 获取匹配的调用
        for call in self.context.calls:
            lines.append(self.analyzer.get_code_at_line(call.lineno))
        
        return "\n".join(lines[:50])  # 限制长度


# 兼容旧接口
class ConstraintEngine(EnhancedConstraintEngine):
    """约束引擎（兼容旧接口）"""
    pass


def verify_code(code: str, requirements: str, level: str = "semantic") -> VerificationReport:
    """验证代码是否满足需求"""
    constraints = parse_requirements(requirements)
    analyzer = PythonAnalyzer()
    context = analyzer.parse_code(code)
    engine = EnhancedConstraintEngine(analyzer)
    return engine.verify(constraints, context, level)


def verify_file(file_path: str, requirements: str, level: str = "semantic") -> VerificationReport:
    """验证文件是否满足需求"""
    constraints = parse_requirements(requirements)
    analyzer = PythonAnalyzer()
    context = analyzer.parse_file(file_path)
    engine = EnhancedConstraintEngine(analyzer)
    return engine.verify(constraints, context, level)


# 测试
if __name__ == "__main__":
    test_code = '''
import logger

def send_sms(phone, message):
    logger.info(f"Sending SMS to {phone}")
    sms_service.send(phone, message)

def create_order(user_id, product_id):
    if user_id <= 0:
        raise ValueError("Invalid user")
    
    order = db.save({"user_id": user_id, "product_id": product_id})
    send_sms(user.phone, "Order created")
    return order
'''
    
    test_requirements = '''
用户下单后必须发送短信通知
每次API调用必须记录日志
促销价格不能大于原价
'''
    
    print("Testing Enhanced Engine...")
    print(f"LLM enabled: {os.getenv('SILICONFLOW_API_KEY') or os.getenv('DEEPSEEK_API_KEY') or 'No'}")
    print()
    
    report = verify_code(test_code, test_requirements, level="semantic")
    
    print(f"Score: {report.summary['score']}%")
    print(f"Passed: {report.summary['passed']}/{report.summary['total']}")
    
    for result in report.results:
        status = "PASS" if result.status == "passed" else "FAIL" if result.status == "failed" else "?"
        print(f"  [{status}] {result.constraint.source_line}")