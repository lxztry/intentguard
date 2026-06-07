"""
IntentGuard - LLM Semantic Layer

使用LLM进行深层语义验证
"""

import hashlib
import json
import os
from typing import Optional, List, Dict, Any
from pathlib import Path

from .factory import get_llm, setup_llm, LLMProvider


class SemanticVerifier:
    """语义验证器 - 使用LLM验证复杂约束"""
    
    def __init__(self, provider: Optional[LLMProvider] = None, cache_dir: str = None):
        self.provider = provider or setup_llm()
        self.cache_dir = cache_dir or (Path.home() / ".intentguard" / "cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def verify(self, constraint, code_context, relevant_code: str) -> Dict[str, Any]:
        """
        验证约束是否满足
        
        Returns:
            {
                "status": "passed" / "failed" / "uncertain",
                "reason": str,
                "suggestion": str,
                "confidence": float (0-1)
            }
        """
        if not self.provider:
            return {
                "status": "uncertain",
                "reason": "No LLM provider available",
                "suggestion": "Set SILICONFLOW_API_KEY or other LLM API key",
                "confidence": 0.0
            }
        
        # 检查缓存
        cache_key = self._get_cache_key(constraint, relevant_code)
        cached = self._load_from_cache(cache_key)
        if cached:
            return cached
        
        # 构建prompt
        prompt = self._build_prompt(constraint, code_context, relevant_code)
        
        # 调用LLM
        response = self.provider.generate(prompt)
        
        # 解析响应
        result = self._parse_response(response)
        
        # 缓存结果
        self._save_to_cache(cache_key, result)
        
        return result
    
    def _build_prompt(self, constraint, code_context, relevant_code: str) -> str:
        """构建验证prompt"""
        
        prompt = f"""你是代码审查助手。请验证以下代码是否满足需求约束。

## 需求约束
类型: {constraint.type.value}
主体: {constraint.subject}
动作: {constraint.predicate}
条件: {constraint.condition or "无"}
优先级: {constraint.priority.value}
原始需求: {constraint.source_line}

## 代码上下文
文件: {code_context.file_path}
函数数量: {len(code_context.functions)}
调用数量: {len(code_context.calls)}
条件语句数量: {len(code_context.conditions)}

## 相关代码片段
```python
{relevant_code}
```

## 验证要求
请仔细分析代码，判断是否满足上述需求。如果不满足，说明原因并给出修复建议。

请按以下JSON格式输出（只输出JSON，不要其他内容）：
{{
    "status": "passed|failed|uncertain",
    "reason": "具体原因，引用代码行号",
    "suggestion": "如果failed，给出具体修复建议",
    "confidence": 0.0-1.0之间的小数
}}
"""
        return prompt
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析LLM响应"""
        try:
            # 尝试提取JSON
            import re
            json_match = re.search(r'\{[^{}]*"status"[^{}]*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "status": result.get("status", "uncertain"),
                    "reason": result.get("reason", ""),
                    "suggestion": result.get("suggestion", ""),
                    "confidence": result.get("confidence", 0.5)
                }
            
            # 降级处理：根据关键词判断
            response_lower = response.lower()
            if "passed" in response_lower and "failed" not in response_lower:
                return {"status": "passed", "reason": response[:500], "suggestion": "", "confidence": 0.7}
            elif "failed" in response_lower:
                return {"status": "failed", "reason": response[:500], "suggestion": "LLM detected issue", "confidence": 0.6}
            else:
                return {"status": "uncertain", "reason": response[:500], "suggestion": "", "confidence": 0.3}
                
        except Exception as e:
            return {
                "status": "uncertain",
                "reason": f"Failed to parse LLM response: {str(e)}",
                "suggestion": "",
                "confidence": 0.0
            }
    
    def _get_cache_key(self, constraint, relevant_code: str) -> str:
        """生成缓存键"""
        content = f"{constraint.source_line}|{relevant_code[:1000]}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _load_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """从缓存加载"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return None
    
    def _save_to_cache(self, cache_key: str, result: Dict[str, Any]):
        """保存到缓存"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def clear_cache(self):
        """清除缓存"""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, cache_dir: str = None):
        self.cache_dir = cache_dir or (Path.home() / ".intentguard" / "cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """获取缓存"""
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return None
    
    def set(self, key: str, value: Dict[str, Any]):
        """设置缓存"""
        cache_file = self.cache_dir / f"{key}.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(value, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def clear(self):
        """清除所有缓存"""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
    
    def size(self) -> int:
        """缓存大小（文件数）"""
        return len(list(self.cache_dir.glob("*.json")))
    
    def size_bytes(self) -> int:
        """缓存大小（字节）"""
        total = 0
        for cache_file in self.cache_dir.glob("*.json"):
            total += cache_file.stat().st_size
        return total


# 便捷函数
def semantic_verify(constraint, code_context, relevant_code: str) -> Dict[str, Any]:
    """语义验证便捷函数"""
    verifier = SemanticVerifier()
    return verifier.verify(constraint, code_context, relevant_code)


# 测试
if __name__ == "__main__":
    print("Testing Semantic Verifier...")
    
    verifier = SemanticVerifier()
    
    # 检查provider
    if verifier.provider:
        print(f"Using provider: {verifier.provider.name()}")
        
        # 测试验证
        from src.core.constraint import Constraint, ConstraintType, Priority
        
        test_constraint = Constraint(
            type=ConstraintType.MUST,
            subject="用户下单",
            predicate="发送短信通知",
            priority=Priority.CRITICAL,
            source_line="用户下单后必须发送短信通知"
        )
        
        class MockCodeContext:
            file_path = "test.py"
            functions = []
            calls = []
            conditions = []
        
        test_code = """
def send_sms(phone, message):
    sms_service.send(phone, message)

def create_order(user_id):
    order = db.save({"user_id": user_id})
    send_sms(user.phone, "Order created")
    return order
"""
        
        result = verifier.verify(test_constraint, MockCodeContext(), test_code)
        print(f"Result: {result}")
    else:
        print("No LLM provider. Set SILICONFLOW_API_KEY to test.")