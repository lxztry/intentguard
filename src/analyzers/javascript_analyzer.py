"""
IntentGuard - JavaScript/TypeScript Analyzer

基于 AST 的静态分析（使用正则 + 简单解析）
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict

from ..core.constraint import Constraint


@dataclass
class FunctionInfo:
    """函数信息"""
    name: str
    lineno: int
    end_lineno: int
    params: List[str] = field(default_factory=list)
    async_def: bool = False
    calls: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)
    
    def __str__(self):
        return f"Function {self.name} (line {self.lineno})"


@dataclass
class CallInfo:
    """函数调用信息"""
    name: str
    lineno: int
    module: Optional[str] = None
    method: Optional[str] = None


@dataclass
class ConditionInfo:
    """条件信息"""
    lineno: int
    condition_type: str  # if / while / try / switch
    condition_expr: str
    body_lines: List[int] = field(default_factory=list)


@dataclass
class CodeContext:
    """代码上下文"""
    file_path: str
    functions: List[FunctionInfo] = field(default_factory=list)
    calls: List[CallInfo] = field(default_factory=list)
    conditions: List[ConditionInfo] = field(default_factory=list)
    
    def find_calls(self, pattern: str) -> List[CallInfo]:
        pattern_lower = pattern.lower()
        return [c for c in self.calls if pattern_lower in c.name.lower()]
    
    def find_function(self, name: str) -> Optional[FunctionInfo]:
        for f in self.functions:
            if f.name == name:
                return f
        return None


class JavaScriptAnalyzer:
    """JavaScript/TypeScript 分析器"""
    
    def __init__(self):
        self.source_code: Optional[str] = None
        self.context: Optional[CodeContext] = None
    
    def parse_file(self, file_path: str) -> CodeContext:
        """解析 JS/TS 文件"""
        with open(file_path, "r", encoding="utf-8") as f:
            self.source_code = f.read()
        
        self.context = CodeContext(file_path=file_path)
        self._analyze()
        return self.context
    
    def parse_code(self, code: str) -> CodeContext:
        """解析代码字符串"""
        self.source_code = code
        self.context = CodeContext(file_path="<input>")
        self._analyze()
        return self.context
    
    def _analyze(self):
        """分析代码"""
        lines = self.source_code.split("\n")
        
        i = 0
        while i < len(lines):
            line = lines[i]
            lineno = i + 1
            
            # 函数定义
            func_match = re.match(r'\s*(?:async\s+)?function\s+(\w+)\s*\(', line)
            if func_match:
                func_info = self._parse_function(lines, i, lineno)
                self.context.functions.append(func_info)
                i = func_info.end_lineno
                continue
            
            # 箭头函数 const xxx = (...) => {...}
            arrow_match = re.match(r'\s*(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(', line)
            if arrow_match:
                func_info = self._parse_arrow_function(lines, i, lineno, arrow_match.group(1))
                self.context.functions.append(func_info)
                i = func_info.end_lineno
                continue
            
            # 类方法
            class_match = re.match(r'\s*(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{', line)
            if class_match and i > 0 and "class" in lines[i-1]:
                name = class_match.group(1)
                func_info = FunctionInfo(name=name, lineno=lineno, end_lineno=lineno)
                self.context.functions.append(func_info)
            
            # 函数调用
            call_match = re.search(r'(\w+)\s*\(', line)
            if call_match:
                call_name = call_match.group(1)
                if call_name not in ("if", "while", "for", "switch", "return", "throw"):
                    call = CallInfo(name=call_name, lineno=lineno)
                    self._parse_module_call(call, line)
                    self.context.calls.append(call)
            
            # 条件语句
            if re.match(r'\s*if\s*\(', line):
                cond_info = ConditionInfo(
                    lineno=lineno,
                    condition_type="if",
                    condition_expr=self._extract_condition_expr(line),
                    body_lines=[lineno + 1]
                )
                self.context.conditions.append(cond_info)
            
            elif re.match(r'\s*while\s*\(', line):
                cond_info = ConditionInfo(
                    lineno=lineno,
                    condition_type="while",
                    condition_expr=self._extract_condition_expr(line),
                    body_lines=[lineno + 1]
                )
                self.context.conditions.append(cond_info)
            
            elif re.match(r'\s*try\s*\{', line):
                cond_info = ConditionInfo(
                    lineno=lineno,
                    condition_type="try",
                    condition_expr="try",
                    body_lines=[lineno + 1]
                )
                self.context.conditions.append(cond_info)
            
            i += 1
    
    def _parse_function(self, lines: List[str], start_idx: int, start_lineno: int) -> FunctionInfo:
        """解析函数定义"""
        line = lines[start_idx]
        
        # 提取函数名
        func_match = re.search(r'(?:async\s+)?function\s+(\w+)', line)
        name = func_match.group(1) if func_match else "anonymous"
        
        # 提取参数
        params_match = re.search(r'\(([^)]*)\)', line)
        params = []
        if params_match and params_match.group(1).strip():
            params = [p.strip() for p in params_match.group(1).split(",")]
        
        # 计算结束行
        end_lineno = start_lineno
        brace_count = 0
        for i in range(start_idx, len(lines)):
            brace_count += lines[i].count("{") - lines[i].count("}")
            if brace_count <= 0 and "{" in lines[i]:
                end_lineno = i + 1
                break
        
        return FunctionInfo(
            name=name,
            lineno=start_lineno,
            end_lineno=end_lineno,
            params=params,
            async_def="async" in line
        )
    
    def _parse_arrow_function(self, lines: List[str], start_idx: int, start_lineno: int, name: str) -> FunctionInfo:
        """解析箭头函数"""
        end_lineno = start_lineno
        brace_count = 0
        for i in range(start_idx, len(lines)):
            brace_count += lines[i].count("{") - lines[i].count("}")
            if brace_count <= 0 and "{" in lines[i]:
                end_lineno = i + 1
                break
        
        return FunctionInfo(
            name=name,
            lineno=start_lineno,
            end_lineno=end_lineno,
            params=[],
            async_def="async" in lines[start_idx]
        )
    
    def _parse_module_call(self, call: CallInfo, line: str):
        """解析模块调用"""
        # a.b() -> module=a, method=b
        match = re.search(r'(\w+)\.(\w+)\s*\(', line)
        if match:
            call.module = match.group(1)
            call.method = match.group(2)
            call.name = f"{match.group(1)}.{match.group(2)}"
    
    def _extract_condition_expr(self, line: str) -> str:
        """提取条件表达式"""
        match = re.search(r'\(([^)]+)\)', line)
        return match.group(1) if match else ""
    
    def get_code_at_line(self, line_no: int) -> str:
        """获取指定行的源代码"""
        if not self.source_code:
            return ""
        
        lines = self.source_code.split("\n")
        if 0 < line_no <= len(lines):
            return lines[line_no - 1]
        return ""


class TypeScriptAnalyzer(JavaScriptAnalyzer):
    """TypeScript 分析器（继承自 JS，类型信息暂不处理）"""
    pass


# 便捷函数
def analyze_javascript_file(file_path: str) -> CodeContext:
    """分析 JavaScript 文件"""
    analyzer = JavaScriptAnalyzer()
    return analyzer.parse_file(file_path)


def analyze_typescript_file(file_path: str) -> CodeContext:
    """分析 TypeScript 文件"""
    analyzer = TypeScriptAnalyzer()
    return analyzer.parse_file(file_path)


def analyze_javascript_code(code: str) -> CodeContext:
    """分析 JavaScript 代码"""
    analyzer = JavaScriptAnalyzer()
    return analyzer.parse_code(code)


# 测试
if __name__ == "__main__":
    test_code = '''
import logger from 'logger';
import smsService from './sms';

class OrderService {
    async createOrder(userId, productId) {
        logger.info(`Creating order for user ${userId}`);
        
        if (userId <= 0) {
            throw new Error('Invalid user');
        }
        
        const order = await db.save({
            userId,
            productId
        });
        
        await this.sendNotification(order);
        
        return order;
    }
    
    async sendNotification(order) {
        const user = await db.fetchOne('SELECT phone FROM users WHERE id = ?', order.userId);
        if (user && user.phone) {
            smsService.send(user.phone, `Order ${order.id} created`);
        }
    }
    
    cancelOrder(orderId, reason) {
        logger.warn(`Cancelling order ${orderId}: ${reason}`);
        db.update('orders', { status: 'cancelled' }, `id = ${orderId}`);
    }
}

module.exports = new OrderService();
'''
    
    analyzer = JavaScriptAnalyzer()
    context = analyzer.parse_code(test_code)
    
    print("=== JavaScript Analysis ===")
    print(f"Functions: {len(context.functions)}")
    for f in context.functions:
        print(f"  {f.name} (lines {f.lineno}-{f.end_lineno})")
    
    print(f"\nCalls: {len(context.calls)}")
    for c in context.calls[:10]:
        print(f"  {c.name} (line {c.lineno})")
    
    print(f"\nConditions: {len(context.conditions)}")
    for cond in context.conditions:
        print(f"  {cond.condition_type} (line {cond.lineno}): {cond.condition_expr[:50]}")