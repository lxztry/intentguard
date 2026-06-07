"""
IntentGuard - Python 代码分析器

基于 Python AST 的静态分析
"""

import ast
import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from ..core.constraint import Constraint


@dataclass
class FunctionInfo:
    """函数信息"""
    name: str
    lineno: int
    end_lineno: int
    args: List[str]
    decorators: List[str] = field(default_factory=list)
    calls: List[str] = field(default_factory=list)  # 调用的函数/方法
    async_def: bool = False
    
    def __str__(self):
        return f"Function {self.name} (line {self.lineno})"


@dataclass
class CallInfo:
    """函数调用信息"""
    name: str           # 被调用的名称
    lineno: int         # 调用所在行
    col_offset: int
    module: Optional[str] = None  # 模块名（如 logger, sms_service）
    method: Optional[str] = None   # 方法名（如 info, send）


@dataclass
class ConditionInfo:
    """条件信息"""
    lineno: int
    condition_type: str  # if / elif / while / try
    condition_expr: str
    body_lines: List[int] = field(default_factory=list)


@dataclass
class CodeContext:
    """代码上下文 - 包含分析结果"""
    file_path: str
    functions: List[FunctionInfo] = field(default_factory=list)
    calls: List[CallInfo] = field(default_factory=list)
    conditions: List[ConditionInfo] = field(default_factory=list)
    data_flow: Dict[str, Any] = field(default_factory=dict)  # 变量传递关系
    
    def find_calls(self, pattern: str) -> List[CallInfo]:
        """查找匹配模式的调用"""
        pattern_lower = pattern.lower()
        return [c for c in self.calls if pattern_lower in c.name.lower()]
    
    def find_function(self, name: str) -> Optional[FunctionInfo]:
        """查找指定函数"""
        for f in self.functions:
            if f.name == name:
                return f
        return None
    
    def get_code_at_line(self, line_no: int) -> str:
        """获取指定行的代码（需要源码）"""
        # 这个方法需要源码，将在 Engine 中实现
        pass


class PythonAnalyzer:
    """Python AST 分析器"""
    
    def __init__(self):
        self.source_code: Optional[str] = None
        self.tree: Optional[ast.AST] = None
        self.context: Optional[CodeContext] = None
    
    def parse_file(self, file_path: str) -> CodeContext:
        """解析 Python 文件"""
        with open(file_path, "r", encoding="utf-8") as f:
            self.source_code = f.read()
        
        self.tree = ast.parse(self.source_code, filename=file_path)
        self.context = CodeContext(file_path=file_path)
        
        self._walk_ast()
        
        return self.context
    
    def parse_code(self, code: str) -> CodeContext:
        """解析代码字符串"""
        self.source_code = code
        self.tree = ast.parse(code)
        self.context = CodeContext(file_path="<input>")
        
        self._walk_ast()
        
        return self.context
    
    def _walk_ast(self):
        """遍历 AST"""
        visitor = CodeVisitor(self.source_code)
        visitor.visit(self.tree)
        
        self.context.functions = visitor.functions
        self.context.calls = visitor.calls
        self.context.conditions = visitor.conditions
    
    def get_code_at_line(self, line_no: int) -> str:
        """获取指定行的源代码"""
        if not self.source_code:
            return ""
        
        lines = self.source_code.split("\n")
        if 0 < line_no <= len(lines):
            return lines[line_no - 1]
        return ""
    
    def get_relevant_code(self, lineno: int, context_lines: int = 3) -> str:
        """获取指定行周围的代码上下文"""
        if not self.source_code:
            return ""
        
        lines = self.source_code.split("\n")
        start = max(0, lineno - context_lines - 1)
        end = min(len(lines), lineno + context_lines)
        
        return "\n".join(f"{i+1}: {lines[i]}" for i in range(start, end))


class CodeVisitor(ast.NodeVisitor):
    """AST 访问器"""
    
    def __init__(self, source: str):
        self.source = source
        self.functions: List[FunctionInfo] = []
        self.calls: List[CallInfo] = []
        self.conditions: List[ConditionInfo] = []
        self._current_function: Optional[str] = None
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """访问函数定义"""
        func_info = FunctionInfo(
            name=node.name,
            lineno=node.lineno,
            end_lineno=node.end_lineno,
            args=[a.arg for a in node.args.args],
            decorators=[self._get_decorator_name(d) for d in node.decorator_list],
            async_def=isinstance(node, ast.AsyncFunctionDef)
        )
        self.functions.append(func_info)
        
        old_func = self._current_function
        self._current_function = node.name
        
        # 遍历函数体
        self.generic_visit(node)
        
        self._current_function = old_func
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """访问异步函数定义"""
        self.visit_FunctionDef(node)  # 复用 FunctionDef 的逻辑
    
    def visit_Call(self, node: ast.Call):
        """访问函数调用"""
        call_info = self._parse_call(node)
        if call_info:
            self.calls.append(call_info)
        self.generic_visit(node)
    
    def _parse_call(self, node: ast.Call) -> Optional[CallInfo]:
        """解析函数调用"""
        name = ""
        module = None
        method = None
        
        if isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            # 处理 a.b() 或 a.b.c()
            attr_parts = []
            current = node.func
            
            while isinstance(current, ast.Attribute):
                attr_parts.insert(0, current.attr)
                current = current.value
            
            if isinstance(current, ast.Name):
                attr_parts.insert(0, current.id)
            
            if len(attr_parts) >= 2:
                module = attr_parts[0]
                method = attr_parts[-1]
                name = ".".join(attr_parts)
            elif len(attr_parts) == 1:
                name = attr_parts[0]
        
        return CallInfo(
            name=name,
            lineno=node.lineno,
            col_offset=node.col_offset,
            module=module,
            method=method
        )
    
    def visit_If(self, node: ast.If):
        """访问 if 语句"""
        condition_expr = ast.unparse(node.test) if hasattr(ast, 'unparse') else ""
        
        cond_info = ConditionInfo(
            lineno=node.lineno,
            condition_type="if",
            condition_expr=condition_expr,
            body_lines=[n.lineno for n in node.body]
        )
        self.conditions.append(cond_info)
        self.generic_visit(node)
    
    def visit_While(self, node: ast.While):
        """访问 while 循环"""
        cond_info = ConditionInfo(
            lineno=node.lineno,
            condition_type="while",
            condition_expr=ast.unparse(node.test) if hasattr(ast, 'unparse') else "",
            body_lines=[n.lineno for n in node.body]
        )
        self.conditions.append(cond_info)
        self.generic_visit(node)
    
    def visit_Try(self, node: ast.Try):
        """访问 try 语句"""
        for handler in node.handlers:
            # 检查 except 块
            for stmt in handler.body:
                if isinstance(stmt, ast.Raise):
                    pass  # 处理异常
            
            # 检查 finally 块
            for stmt in node.finalbody:
                pass  # finally 处理
        
        self.generic_visit(node)
    
    def _get_decorator_name(self, decorator: ast.expr) -> str:
        """获取装饰器名称"""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                return decorator.func.id
        elif isinstance(decorator, ast.Attribute):
            parts = []
            current = decorator
            while isinstance(current, ast.Attribute):
                parts.insert(0, current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.insert(0, current.id)
            return ".".join(parts)
        return ""


# 便捷函数
def analyze_python_file(file_path: str) -> CodeContext:
    """分析 Python 文件"""
    analyzer = PythonAnalyzer()
    return analyzer.parse_file(file_path)


def analyze_python_code(code: str) -> CodeContext:
    """分析 Python 代码字符串"""
    analyzer = PythonAnalyzer()
    return analyzer.parse_code(code)


# 测试
if __name__ == "__main__":
    test_code = '''
import logger

def send_sms(phone, message):
    """发送短信"""
    logger.info(f"发送短信到 {phone}")
    sms_service.send(phone, message)

def create_order(user_id, product_id):
    """创建订单"""
    if user_id <= 0:
        raise ValueError("无效用户")
    
    # 检查库存
    if not inventory.check(product_id):
        return None
    
    # 创建订单
    order = db.save({
        "user_id": user_id,
        "product_id": product_id
    })
    
    # 发送通知
    send_sms(user.phone, "订单创建成功")
    
    return order

async def process_payment(order_id, amount):
    """处理支付"""
    try:
        result = payment_gateway.charge(order_id, amount)
        return result
    except PaymentError as e:
        logger.error(f"支付失败: {e}")
        return None
'''
    
    analyzer = PythonAnalyzer()
    context = analyzer.parse_code(test_code)
    
    print("=== 函数 ===")
    for f in context.functions:
        print(f"  {f.name} (行{f.lineno}): args={f.args}")
    
    print("\n=== 调用 ===")
    for c in context.calls:
        print(f"  {c.name} (行{c.lineno})")
    
    print("\n=== 条件 ===")
    for cond in context.conditions:
        print(f"  {cond.condition_type} (行{cond.lineno}): {cond.condition_expr}")