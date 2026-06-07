"""
IntentGuard CLI

命令行入口
"""

import os
import sys
import argparse
from pathlib import Path

# 添加 src 目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ..core.engine import verify_code, verify_file
from ..core.report import format_report


def main():
    parser = argparse.ArgumentParser(
        prog="intentguard",
        description="IntentGuard - AI时代代码验证工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 验证代码
  intentguard verify -c "import logger..." -r "必须记录日志"

  # 验证文件
  intentguard verify -f app.py -r requirements.txt

  # 输出 JSON 格式
  intentguard verify -f app.py -r "需求..." -o json
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # verify 命令
    verify_parser = subparsers.add_parser("verify", help="验证代码是否满足需求")
    verify_parser.add_argument("-c", "--code", help="代码字符串（与 -f 二选一）")
    verify_parser.add_argument("-f", "--file", help="代码文件路径（与 -c 二选一）")
    verify_parser.add_argument("-r", "--requirements", required=True, help="需求文本或需求文件路径")
    verify_parser.add_argument("-o", "--output", choices=["text", "json", "markdown"], default="text", help="输出格式")
    verify_parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == "verify":
        run_verify(args)


def run_verify(args):
    """执行验证"""
    
    # 读取需求
    if os.path.isfile(args.requirements):
        with open(args.requirements, "r", encoding="utf-8") as f:
            requirements = f.read()
    else:
        requirements = args.requirements
    
    # 读取代码
    if args.code:
        code = args.code
    elif args.file:
        if not os.path.isfile(args.file):
            print(f"❌ 错误: 文件不存在: {args.file}")
            return
        with open(args.file, "r", encoding="utf-8") as f:
            code = f.read()
    else:
        print("❌ 错误: 请提供 -c 代码或 -f 文件")
        return
    
    # 验证
    if args.file and os.path.isfile(args.file):
        report = verify_file(args.file, requirements)
    else:
        report = verify_code(code, requirements)
    
    # 输出
    output = format_report(report, args.output)
    print(output)
    
    # 返回码
    if report.summary["failed"] > 0:
        sys.exit(1)


# 便捷命令
def verify_cli(code: str, requirements: str, output: str = "text") -> str:
    """CLI 调用接口"""
    report = verify_code(code, requirements)
    return format_report(report, output)


if __name__ == "__main__":
    main()