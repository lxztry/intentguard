from .python_analyzer import PythonAnalyzer, CodeContext, analyze_python_file, analyze_python_code
from .javascript_analyzer import JavaScriptAnalyzer, TypeScriptAnalyzer, analyze_javascript_file, analyze_typescript_file, analyze_javascript_code
from .go_analyzer import GoAnalyzer, analyze_go_file, analyze_go_code

# 语言检测
import os
from typing import Optional

def detect_language(file_path: str) -> Optional[str]:
    """根据文件扩展名检测语言"""
    ext = os.path.splitext(file_path)[1].lower()
    lang_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
        ".go": "go",
    }
    return lang_map.get(ext)


def analyze_file(file_path: str):
    """自动检测语言并分析文件"""
    lang = detect_language(file_path)
    
    if lang == "python":
        return analyze_python_file(file_path)
    elif lang == "javascript":
        return analyze_javascript_file(file_path)
    elif lang == "typescript":
        return analyze_typescript_file(file_path)
    elif lang == "go":
        return analyze_go_file(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_path}")