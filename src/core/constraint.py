"""
IntentGuard - 约束模型定义

定义需求的结构化表示
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ConstraintType(Enum):
    """约束类型枚举"""
    MUST = "MUST"                    # 必须满足
    MUST_NOT = "MUST_NOT"           # 禁止出现
    LTE = "LTE"                     # 小于等于
    GTE = "GTE"                     # 大于等于
    EQ = "EQ"                       # 等于
    CONTAINS = "CONTAINS"           # 必须包含
    EXISTS = "EXISTS"               # 必须存在
    CONDITIONAL = "CONDITIONAL"      # 条件约束（当X发生时，Y必须满足）


class Priority(Enum):
    """优先级"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Constraint:
    """
    单个约束的结构化表示
    
    Example:
        约束: "用户下单后必须发送短信通知"
        
        type: MUST
        subject: "用户下单"
        action: "发送短信通知"
        condition: None  (无条件)
        priority: HIGH
        source_line: "用户下单后必须发送短信通知"
    """
    type: ConstraintType
    subject: str                     # 约束主体（谁/什么）
    predicate: str                  # 谓词（做什么/是什么）
    condition: Optional[str] = None # 触发条件（当X发生时）
    operator: str = "=="            # 比较操作符
    value: Optional[Any] = None     # 期望值
    priority: Priority = Priority.MEDIUM
    source_line: str = ""           # 原始需求文本
    verification_hints: list = field(default_factory=list)  # 验证提示（关键词等）
    
    def __str__(self):
        cond = f"当{self.condition}时，" if self.condition else ""
        return f"[{self.type.value}] {cond}{self.subject}必须{self.predicate}"
    
    def to_dict(self):
        return {
            "type": self.type.value,
            "subject": self.subject,
            "predicate": self.predicate,
            "condition": self.condition,
            "operator": self.operator,
            "value": self.value,
            "priority": self.priority.value,
            "source_line": self.source_line,
            "verification_hints": self.verification_hints
        }


@dataclass
class VerificationResult:
    """单个约束的验证结果"""
    constraint: Constraint
    status: str                      # passed / failed / uncertain / skipped
    matched_code: Optional[str] = None
    line_number: Optional[int] = None
    reason: Optional[str] = None
    suggestion: Optional[str] = None
    
    def to_dict(self):
        return {
            "constraint": str(self.constraint),
            "status": self.status,
            "matched_code": self.matched_code,
            "line_number": self.line_number,
            "reason": self.reason,
            "suggestion": self.suggestion
        }


@dataclass
class VerificationReport:
    """完整验证报告"""
    constraints: list[Constraint]
    results: list[VerificationResult]
    code_path: str
    requirements_text: str
    
    @property
    def summary(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "passed")
        failed = sum(1 for r in self.results if r.status == "failed")
        uncertain = sum(1 for r in self.results if r.status == "uncertain")
        score = round(passed / total * 100) if total > 0 else 0
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "uncertain": uncertain,
            "skipped": total - passed - failed - uncertain,
            "score": score
        }
    
    def to_dict(self):
        return {
            "summary": self.summary,
            "details": [r.to_dict() for r in self.results],
            "code_path": self.code_path,
            "requirements_text": self.requirements_text
        }