"""
IntentGuard - Go Analyzer

基于正则的 Go 语言静态分析
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional

from ..core.constraint import Constraint


@dataclass
class FunctionInfo:
    """函数信息"""
    name: str
    lineno: int
    end_lineno: int
    params: List[str] = field(default_factory=list)
    returns: List[str] = field(default_factory=list)
    is_method: bool = False
    receiver: str = ""
    calls: List[str] = field(default_factory=list)
    
    def __str__(self):
        prefix = f"{self.receiver}." if self.receiver else ""
        return f"Function {prefix}{self.name} (line {self.lineno})"


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
    condition_type: str  # if / for / switch
    condition_expr: str
    body_lines: List[int] = field(default_factory=list)


@dataclass
class CodeContext:
    """代码上下文"""
    file_path: str
    functions: List[FunctionInfo] = field(default_factory=list)
    calls: List[CallInfo] = field(default_factory=list)
    conditions: List[ConditionInfo] = field(default_factory=list)
    goroutines: List[int] = field(default_factory=list)  # go 语句行号
    
    def find_calls(self, pattern: str) -> List[CallInfo]:
        pattern_lower = pattern.lower()
        return [c for c in self.calls if pattern_lower in c.name.lower()]
    
    def find_function(self, name: str) -> Optional[FunctionInfo]:
        for f in self.functions:
            if f.name == name:
                return f


class GoAnalyzer:
    """Go 语言分析器"""
    
    def __init__(self):
        self.source_code: Optional[str] = None
        self.context: Optional[CodeContext] = None
    
    def parse_file(self, file_path: str) -> CodeContext:
        """解析 Go 文件"""
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
            stripped = line.strip()
            lineno = i + 1
            
            # 跳过注释和空行
            if not stripped or stripped.startswith("//") or stripped.startswith("/*"):
                i += 1
                continue
            
            # 函数定义
            func_match = re.match(r'func\s+(\([^)]+\))?\s*(\w+)\s*\(', stripped)
            if func_match:
                receiver = ""
                if func_match.group(1):
                    receiver = func_match.group(1)[1:-1]  # 去掉括号
                
                name = func_match.group(2)
                func_info = self._parse_function(lines, i, lineno, receiver)
                self.context.functions.append(func_info)
                i = func_info.end_lineno
                continue
            
            # goroutine
            if re.match(r'\s*go\s+', stripped):
                self.context.goroutines.append(lineno)
            
            # 函数调用
            call_match = re.search(r'(\w+)\s*\(', stripped)
            if call_match:
                call_name = call_match.group(1)
                # 排除关键字
                if call_name not in ("if", "for", "switch", "return", "break", "continue", "go", "defer", "select"):
                    call = CallInfo(name=call_name, lineno=lineno)
                    self._parse_module_call(call, stripped)
                    self.context.calls.append(call)
            
            # 条件语句
            if re.match(r'\s*if\s+', stripped):
                cond_info = ConditionInfo(
                    lineno=lineno,
                    condition_type="if",
                    condition_expr=self._extract_condition_expr(stripped),
                    body_lines=[lineno + 1]
                )
                self.context.conditions.append(cond_info)
            
            elif re.match(r'\s*for\s+', stripped):
                cond_info = ConditionInfo(
                    lineno=lineno,
                    condition_type="for",
                    condition_expr=self._extract_condition_expr(stripped),
                    body_lines=[lineno + 1]
                )
                self.context.conditions.append(cond_info)
            
            elif re.match(r'\s*switch\s+', stripped):
                cond_info = ConditionInfo(
                    lineno=lineno,
                    condition_type="switch",
                    condition_expr=self._extract_condition_expr(stripped),
                    body_lines=[lineno + 1]
                )
                self.context.conditions.append(cond_info)
            
            i += 1
    
    def _parse_function(self, lines: List[str], start_idx: int, start_lineno: int, receiver: str = "") -> FunctionInfo:
        """解析函数定义"""
        line = lines[start_idx]
        
        # 提取函数名
        func_match = re.search(r'func\s+(?:\([^)]+\)\s*)?(\w+)', line)
        name = func_match.group(1) if func_match else "unknown"
        
        # 提取参数
        params_match = re.search(r'\(([^)]*)\)', line)
        params = []
        if params_match and params_match.group(1).strip():
            params = self._parse_params(params_match.group(1))
        
        # 提取返回值
        returns_match = re.search(r'\)\s*\(?([^)]*)\)?\s*\{', line)
        returns = []
        if returns_match and returns_match.group(1).strip():
            returns = self._parse_params(returns_match.group(1))
        
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
            returns=returns,
            is_method=bool(receiver),
            receiver=receiver,
            calls=[]
        )
    
    def _parse_params(self, param_str: str) -> List[str]:
        """解析参数列表"""
        params = []
        for p in param_str.split(","):
            p = p.strip()
            if not p:
                continue
            # 提取参数名（忽略类型）
            parts = p.split()
            if parts:
                params.append(parts[-1])  # 取最后一个词作为参数名
        return params
    
    def _parse_module_call(self, call: CallInfo, line: str):
        """解析模块调用"""
        # obj.Method() -> module=obj, method=Method
        match = re.search(r'(\w+)\.(\w+)\s*\(', line)
        if match:
            call.module = match.group(1)
            call.method = match.group(2)
            call.name = f"{match.group(1)}.{match.group(2)}"
    
    def _extract_condition_expr(self, line: str) -> str:
        """提取条件表达式"""
        # for i := 0; i < n; i++ { -> i < n
        if ";" in line:
            parts = line.split(";")
            if len(parts) >= 2:
                return parts[1].strip()
        
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


# 便捷函数
def analyze_go_file(file_path: str) -> CodeContext:
    """分析 Go 文件"""
    analyzer = GoAnalyzer()
    return analyzer.parse_file(file_path)


def analyze_go_code(code: str) -> CodeContext:
    """分析 Go 代码"""
    analyzer = GoAnalyzer()
    return analyzer.parse_code(code)


# 测试
if __name__ == "__main__":
    test_code = '''
package main

import (
    "log"
    "database/sql"
    "fmt"
)

type OrderService struct {
    db *sql.DB
}

func NewOrderService(db *sql.DB) *OrderService {
    return &OrderService{db: db}
}

func (s *OrderService) CreateOrder(userID, productID int) (*Order, error) {
    log.Printf("Creating order for user %d", userID)
    
    if userID <= 0 {
        return nil, fmt.Errorf("invalid user ID")
    }
    
    order := &Order{
        UserID:    userID,
        ProductID: productID,
        Status:    "pending",
    }
    
    err := s.db.Save(order)
    if err != nil {
        return nil, err
    }
    
    go s.sendNotification(order.ID)
    
    return order, nil
}

func (s *OrderService) sendNotification(orderID int) {
    log.Printf("Sending notification for order %d", orderID)
    
    user, err := s.db.FetchOne("SELECT phone FROM users WHERE id = ?", orderID)
    if err != nil {
        log.Printf("Failed to fetch user: %v", err)
        return
    }
    
    smsService.Send(user.Phone, fmt.Sprintf("Order %d created", orderID))
}

func (s *OrderService) CancelOrder(orderID int, reason string) error {
    log.Printf("Cancelling order %d: %s", orderID, reason)
    
    _, err := s.db.Exec("UPDATE orders SET status = 'cancelled' WHERE id = ?", orderID)
    return err
}

type Order struct {
    ID        int
    UserID    int
    ProductID int
    Status    string
}
'''
    
    analyzer = GoAnalyzer()
    context = analyzer.parse_code(test_code)
    
    print("=== Go Analysis ===")
    print(f"Functions: {len(context.functions)}")
    for f in context.functions:
        print(f"  {f.name} (lines {f.lineno}-{f.end_lineno})" + (f" [receiver: {f.receiver}]" if f.receiver else ""))
    
    print(f"\nGoroutines: {len(context.goroutines)}")
    for g in context.goroutines:
        print(f"  go statement at line {g}")
    
    print(f"\nCalls: {len(context.calls)}")
    for c in context.calls[:10]:
        print(f"  {c.name} (line {c.lineno})")
    
    print(f"\nConditions: {len(context.conditions)}")
    for cond in context.conditions:
        print(f"  {cond.condition_type} (line {cond.lineno})")