# IntentGuard VSCode Extension

Provides IDE integration for IntentGuard code verification.

## Features

- **Quick Verify**: Press `Ctrl+Shift+V` to verify the current file
- **Requirements File**: Configure default requirements file in settings
- **Multi-level Verification**: Choose between static, semantic, or deep analysis
- **Multiple Output Formats**: Text, JSON, or Markdown output
- **Inline Results**: Results displayed in a Webview panel

## Installation

1. Open this folder in VSCode
2. Press `F5` to launch the extension in development mode

Or publish to VSCode marketplace:
```bash
npm install -g vsce
vsce package
```

## Configuration

In VSCode settings (`settings.json`):

```json
{
    "intentguard.requirementsFile": "requirements.txt",
    "intentguard.llmProvider": "siliconflow",
    "intentguard.verificationLevel": "semantic",
    "intentguard.outputFormat": "text"
}
```

## Commands

| Command | Description | Shortcut |
|---------|-------------|----------|
| `IntentGuard: Verify Current File` | Verify the current file | `Ctrl+Shift+V` |
| `IntentGuard: Verify with Requirements File` | Verify with specific requirements | |
| `IntentGuard: Configure` | Open settings | |

## Requirements

- Python 3.8+
- IntentGuard package (`pip install intentguard`)
- LLM API key (optional, for semantic verification): `SILICONFLOW_API_KEY`, `DEEPSEEK_API_KEY`, or `OPENAI_API_KEY`