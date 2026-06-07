"""
IntentGuard - 模式匹配需求解析器

将自然语言需求转换为结构化约束列表
"""

import re
from typing import List

from ..core.constraint import Constraint, ConstraintType, Priority


# 关键词模式定义
PATTERNS = [
    # MUST 模式
    (r"(必须|一定要|应当|应该|需要|不能没有)", ConstraintType.MUST),
    (r"(\w+)后(必须|要|应该)", ConstraintType.MUST),
    (r"(每当|每次|每次当)", ConstraintType.CONDITIONAL),
    
    # MUST_NOT 模式
    (r"(禁止|不得|不能|不允许|不应该|严禁)", ConstraintType.MUST_NOT),
    (r"(\w+)时(不能|禁止|不得)", ConstraintType.MUST_NOT),
    
    # 数量/范围约束
    (r"不超过|最多|不大于", ConstraintType.LTE),
    (r"不少于|至少|大于等于", ConstraintType.GTE),
    
    # EXISTS 模式
    (r"必须有|需要包含|应当有", ConstraintType.EXISTS),
]

# 谓词关键词映射
PREDICATE_PATTERNS = {
    r"(发短信|发送短信|通知用户|短信通知)": "发送短信通知",
    r"(记录日志|写日志|打日志|log)": "记录日志",
    r"(校验|验证|检查|确认)": "校验数据",
    r"(异常|错误|失败)": "处理异常",
    r"(超时|timeout)": "处理超时",
    r"(重试|retry)": "重试机制",
    r"(事务|transaction)": "事务处理",
    r"(权限|permission|auth)": "权限检查",
    r"(日志|log)": "记录日志",
    r"(数据库|db|存储)": "数据库操作",
    r"(缓存|cache)": "缓存处理",
    r"(事务)": "事务处理",
    r"(幂等|idempotent)": "幂等性保证",
}


class RequirementParser:
    """需求解析器 - 将自然语言转换为约束"""
    
    def __init__(self):
        self.compiled_patterns = [(re.compile(p, re.IGNORECASE), t) for p, t in PATTERNS]
    
    def parse(self, text: str) -> List[Constraint]:
        """
        解析自然语言需求
        
        Args:
            text: 多行需求文本
            
        Returns:
            约束列表
        """
        constraints = []
        lines = text.strip().split("\n")
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            parsed = self._parse_line(line)
            if parsed:
                constraints.extend(parsed)
        
        return constraints
    
    def _parse_line(self, line: str) -> List[Constraint]:
        """解析单行需求"""
        constraints = []
        line_lower = line.lower()
        
        # 跳过注释行
        if line_lower.startswith("#") or line_lower.startswith("//"):
            return []
        
        # 检测约束类型
        constraint_type = None
        for pattern, ctype in self.compiled_patterns:
            match = pattern.search(line)
            if match:
                constraint_type = ctype
                break
        
        if not constraint_type:
            # 默认当作 MUST
            constraint_type = ConstraintType.MUST
        
        # 提取主体和谓词
        subject, predicate = self._extract_subject_predicate(line)
        
        # 提取条件（如果存在）
        condition = self._extract_condition(line)
        
        # 提取优先级
        priority = self._extract_priority(line)
        
        # 提取验证提示（关键词）
        hints = self._extract_hints(line)
        
        constraint = Constraint(
            type=constraint_type,
            subject=subject,
            predicate=predicate,
            condition=condition,
            priority=priority,
            source_line=line,
            verification_hints=hints
        )
        constraints.append(constraint)
        
        return constraints
    
    def _extract_subject_predicate(self, line: str) -> tuple:
        """提取主体和谓词"""
        # 常见句式：主体 + 必须/应该 + 谓词
        # 例如："用户下单后必须发送短信通知"
        
        predicate_keywords = list(PREDICATE_PATTERNS.keys())
        
        for pattern in predicate_keywords:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                predicate_text = PREDICATE_PATTERNS[pattern]
                # 主体是匹配位置之前的文本
                subject = line[:match.start()].strip()
                # 清理主体
                subject = re.sub(r"(当|每次|每当|如果|若)", "", subject)
                subject = subject.strip("，,。. ")
                return subject or "系统", predicate_text
        
        # 默认：主体=系统，谓词=整个句子
        return "系统", line.strip()
    
    def _extract_condition(self, line: str) -> str:
        """提取触发条件"""
        # 条件句式：X发生后/时/后
        condition_patterns = [
            r"当(.+?)(发生|时|后)",
            r"每次(.+?)(发生|时|后)",
            r"每当(.+?)(发生|时|后)",
            r"如果(.+?)则",
        ]
        
        for pattern in condition_patterns:
            match = re.search(pattern, line)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_priority(self, line: str) -> Priority:
        """提取优先级"""
        line_lower = line.lower()
        
        if "关键" in line or "重要" in line or "必须" in line:
            return Priority.CRITICAL
        if "重要" in line or "建议" in line:
            return Priority.HIGH
        if "尽量" in line or "最好" in line:
            return Priority.MEDIUM
        return Priority.LOW
    
    def _extract_hints(self, line: str) -> list:
        """提取验证提示（代码关键词）"""
        hints = []
        
        # 常见的代码关键词
        code_keywords = [
            r"log\w*", r"logger", r"logging",
            r"print", r"console",
            r"send\w*", r"sms", r"email", r"notify",
            r"assert", r"check", r"validate", r"verify",
            r"try", r"catch", r"except", r"finally",
            r"retry", r"timeout",
            r"transaction", r"commit", r"rollback",
            r"cache", r"redis", r"memcached",
            r"db", r"sql", r"query",
            r"auth", r"permission", r"authorize",
        ]
        
        for keyword in code_keywords:
            if re.search(keyword, line, re.IGNORECASE):
                hints.append(keyword)
        
        return hints


# 便捷函数
def parse_requirements(text: str) -> List[Constraint]:
    """解析需求文本为约束列表"""
    parser = RequirementParser()
    return parser.parse(text)


# 测试
if __name__ == "__main__":
    test_requirements = """
用户下单后必须发送短信通知
每次API调用必须记录日志
禁止直接操作数据库，必须通过ORM层
促销价格不能超过原价
当订单失败时必须重试3次
系统必须处理超时异常
重要：所有接口必须进行权限校验
    """
    
    parser = RequirementParser()
    constraints = parser.parse(test_requirements)
    
    for c in constraints:
        print(f"[{c.type.value}] {c.subject} | {c.predicate} | 条件:{c.condition} | 优先级:{c.priority.value}")
        print(f"  原始: {c.source_line}")
        print(f"  提示: {c.verification_hints}")
        print()