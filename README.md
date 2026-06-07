# IntentGuard

**AI-Era Code Verification Tool** — Verify that AI-generated code actually satisfies your requirements.

> "Stop trusting AI-generated code without proof. IntentGuard validates that your code does what you asked for."

---

## Overview

IntentGuard bridges the gap between **natural language requirements** and **actual code implementation**. 

Instead of writing tests after the fact, you describe what your code must do, and IntentGuard automatically verifies whether the implementation satisfies those requirements.

### Core Concept

```
Requirements (Natural Language)
    |
    v
+------------------+
| Requirement      |  Extract
| Parser           |------> Constraint List
+------------------+
    |
    v
+------------------+
| Code Analyzer    |  Parse
| (Python/JS/Go)   |------> AST + Call Graph
+------------------+
    |
    v
+------------------+
| Constraint       |  Verify
| Engine           |------> Verification Report
+------------------+
    |
    v
Verification Report (JSON/Text/Markdown)
```

---

## Quick Start

### Installation

```bash
cd D:\code\intentguard
pip install -r requirements.txt

# For LLM semantic verification (optional)
export SILICONFLOW_API_KEY=your_key_here
# or
export DEEPSEEK_API_KEY=your_key_here
# or
export OPENAI_API_KEY=your_key_here
```

### Basic Usage

**Verify code string:**
```bash
python -m src.cli.main verify -c "def send_sms(): sms_service.send()" -r "必须发送短信通知"
```

**Verify file:**
```bash
python -m src.cli.main verify -f path/to/code.py -r requirements.txt
```

**Verification levels:**
```bash
# Level 1: Static only (fast, no LLM)
python -m src.cli.main verify -f app.py -r req.txt --level static

# Level 2: Static + LLM (balanced)
python -m src.cli.main verify -f app.py -r req.txt --level semantic

# Level 3: LLM deep analysis (slow, thorough)
python -m src.cli.main verify -f app.py -r req.txt --level deep
```

---

## Architecture

```
intentguard/
├── src/
│   ├── core/
│   │   ├── constraint.py    # Constraint data model
│   │   ├── engine.py        # Core verification logic (multi-level)
│   │   └── report.py        # Report generation
│   ├── parser/
│   │   └── pattern_parser.py # Natural language → constraints
│   ├── analyzers/
│   │   ├── python_analyzer.py  # Python AST analysis
│   │   ├── javascript_analyzer.py # JS/TS analysis
│   │   └── go_analyzer.py      # Go analysis
│   ├── llm/
│   │   ├── factory.py       # LLM provider factory
│   │   └── semantic.py      # LLM semantic verification
│   └── cli/
│       └── main.py          # CLI entry point
├── tests/
│   ├── test_intentguard.py
│   └── fixtures/
├── vscode-extension/        # VSCode plugin
├── requirements.txt
└── README.md
```

### Core Components

| Component | Responsibility |
|-----------|---------------|
| `RequirementParser` | Parse natural language requirements into structured `Constraint` objects |
| `PythonAnalyzer` | Parse Python code into AST, extract functions/calls/conditions |
| `JavaScriptAnalyzer` | Parse JS/TS code (regex-based) |
| `GoAnalyzer` | Parse Go code (regex-based) |
| `LLMFactory` | Unified interface for multiple LLM providers |
| `SemanticVerifier` | LLM-based deep semantic verification |
| `EnhancedConstraintEngine` | Multi-level verification (static/semantic/deep) |
| `ReportGenerator` | Format results as text/JSON/markdown |

---

## Language Support

| Language | Analyzer | Status |
|----------|----------|--------|
| Python | AST-based | ✅ Complete |
| JavaScript | Regex-based | ✅ Complete |
| TypeScript | Regex-based | ✅ Complete |
| Go | Regex-based | ✅ Complete |

---

## Constraint Types

| Type | Description | Example |
|------|-------------|---------|
| `MUST` | Must be implemented | "必须发送短信通知" |
| `MUST_NOT` | Must not appear | "禁止直接操作数据库" |
| `CONDITIONAL` | Must happen when X occurs | "当订单失败时必须重试3次" |
| `EXISTS` | Must exist | "必须有权限校验" |
| `LTE` | Must be <= value | "响应时间不超过200ms" |
| `GTE` | Must be >= value | "至少重试3次" |

---

## Requirement Syntax

IntentGuard recognizes these patterns in natural language:

```
MUST patterns:
  "必须" / "一定要" / "应当" / "应该"
  "X后必须Y" / "每当X必须Y"

MUST_NOT patterns:
  "禁止" / "不得" / "不能" / "不允许"
  "X时不能Y"

Priority indicators:
  "关键" / "重要" → CRITICAL
  "建议" → HIGH
  "尽量" → MEDIUM
```

---

## Example

### Input Code (`order.py`)
```python
import logger

def create_order(user_id, product_id):
    if user_id <= 0:
        raise ValueError("Invalid user")
    
    order = db.save({"user_id": user_id})
    
    # 发送短信通知
    sms_service.send(user.phone, "Order created")
    
    logger.info(f"Order {order['id']} created")
    
    return order
```

### Requirements (`requirements.txt`)
```
用户下单后必须发送短信通知
每次API调用必须记录日志
禁止直接操作数据库，必须通过Repository层
```

### Verification Command
```bash
python -m src.cli.main verify -f order.py -r requirements.txt --level semantic
```

### Output
```
============================================================
IntentGuard Verification Report
============================================================

[SCORE] 67%
   Passed: 2 | Failed: 1 | Uncertain: 0

------------------------------------------------------------
Details
------------------------------------------------------------

[+] [MUST] [CRITICAL] 用户下单后必须发送短信通知
   [OK] Satisfied: line 12
   Code: sms_service.send(user.phone, "Order created")

[+] [MUST] [CRITICAL] 每次API调用必须记录日志
   [OK] Satisfied: line 14
   Code: logger.info(f"Order {order['id']} created")

[X] [MUST] [CRITICAL] 禁止直接操作数据库，必须通过Repository层
   [FAIL] Not satisfied
   Reason: Found direct database operation: db.save()
   Suggestion: Use repository pattern: order_repo.create()
   Location: line 8

============================================================
```

---

## LLM Integration

IntentGuard supports multiple LLM providers for deep semantic verification:

### Supported Providers

| Provider | Environment Variable | Model |
|----------|---------------------|-------|
| SiliconFlow | `SILICONFLOW_API_KEY` | DeepSeek-V3 (default) |
| DeepSeek | `DEEPSEEK_API_KEY` | deepseek-chat |
| OpenAI | `OPENAI_API_KEY` | gpt-4o-mini |
| Ollama (local) | - | qwen2.5:7b (default) |

### Verification Levels

1. **Static** (`--level static`): Fast pattern matching, no LLM
2. **Semantic** (`--level semantic`): Static + LLM for complex constraints
3. **Deep** (`--level deep`): LLM-first analysis for thorough verification

### Caching

LLM responses are cached to avoid repeated API calls. Cache location: `~/.intentguard/cache/`

---

## VSCode Extension

See `vscode-extension/README.md` for installation and usage.

**Quick install:**
```bash
cd vscode-extension
code --install-extension intentguard-*.vsix
```

**Keyboard shortcut:** `Ctrl+Shift+V` to verify current file

---

## Development Status

### Phase 1 — Completed ✅
- [x] Constraint model
- [x] Pattern-based requirement parser
- [x] Python AST analyzer
- [x] Constraint verification engine (Level 1: static)
- [x] Text/JSON/Markdown report output
- [x] CLI interface
- [x] Basic test suite

### Phase 2 — Completed ✅
- [x] LLM factory (SiliconFlow/DeepSeek/OpenAI/Ollama)
- [x] Semantic verification layer
- [x] Multi-level verification engine (static/semantic/deep)
- [x] Response caching
- [x] JavaScript/TypeScript analyzer
- [x] Go analyzer

### Phase 3 — VSCode Extension ✅
- [x] VSCode extension framework
- [x] Commands (verify, configure)
- [x] Configuration support
- [x] Results Webview display

### Future
- [ ] Publish to VSCode Marketplace
- [ ] JetBrains IDE plugin
- [ ] Intent description language (custom DSL)
- [ ] CI/CD pipeline integration (GitHub Actions, GitLab CI)
- [ ] Real-time verification on file save

---

## Why IntentGuard?

| Traditional Testing | IntentGuard |
|---------------------|-------------|
| Write tests after coding | Describe requirements before/during coding |
| Test what code does | Verify what code should do |
| Brittle assertions | Semantic matching |
| Manual maintenance | Auto-generated from requirements |
| No LLM integration | LLM-powered deep verification |

---

## Limitations

1. **JS/Go analyzers are regex-based** — Less precise than full parsers
2. **Pattern matching is limited** — Complex natural language may not parse correctly
3. **LLM requires API key** — Semantic verification needs external service
4. **No runtime behavior analysis** — Only static/code analysis

---

## License

MIT