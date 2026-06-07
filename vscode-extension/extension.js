/**
 * IntentGuard VSCode Extension
 * 
 * Provides code verification against natural language requirements
 */

const vscode = require('vscode');
const { spawn } = require('child_process');
const path = require('path');

// Configuration
let config = {
    requirementsFile: 'requirements.txt',
    verificationLevel: 'semantic',
    outputFormat: 'text'
};

/**
 * Load configuration from VSCode settings
 */
function loadConfig() {
    config.requirementsFile = vscode.workspace.getConfiguration('intentguard').get('requirementsFile', 'requirements.txt');
    config.verificationLevel = vscode.workspace.getConfiguration('intentguard').get('verificationLevel', 'semantic');
    config.outputFormat = vscode.workspace.getConfiguration('intentguard').get('outputFormat', 'text');
}

/**
 * Get the workspace root
 */
function getWorkspaceRoot() {
    if (vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders.length > 0) {
        return vscode.workspace.workspaceFolders[0].uri.fsPath;
    }
    return vscode.workspace.rootPath;
}

/**
 * Run IntentGuard verification
 */
async function runVerification(filePath, requirementsPath) {
    loadConfig();
    
    // Get IntentGuard path (assumes it's installed in workspace or we use the local version)
    const workspaceRoot = getWorkspaceRoot();
    const intentguardPath = path.join(workspaceRoot, '..', 'intentguard');
    
    // Build command
    const args = [
        '-m', 'src.cli.main',
        'verify',
        '-f', filePath,
        '-r', requirementsPath,
        '-o', config.outputFormat,
        '--level', config.verificationLevel
    ];
    
    return new Promise((resolve, reject) => {
        const proc = spawn('python', args, {
            cwd: intentguardPath,
            shell: true
        });
        
        let stdout = '';
        let stderr = '';
        
        proc.stdout.on('data', (data) => {
            stdout += data.toString();
        });
        
        proc.stderr.on('data', (data) => {
            stderr += data.toString();
        });
        
        proc.on('close', (code) => {
            if (code === 0) {
                resolve(stdout);
            } else {
                reject(new Error(stderr || `Exit code: ${code}`));
            }
        });
        
        proc.on('error', (err) => {
            reject(err);
        });
    });
}

/**
 * Show verification results in a Webview panel
 */
function showResults(results) {
    const panel = vscode.window.createWebviewPanel(
        'intentguardResults',
        'IntentGuard Verification',
        vscode.ViewColumn.Beside,
        {}
    );
    
    // Convert results to HTML
    const html = `
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: monospace; padding: 20px; }
        .passed { color: green; }
        .failed { color: red; }
        .uncertain { color: orange; }
        pre { background: #f4f4f4; padding: 10px; overflow-x: auto; }
    </style>
</head>
<body>
    <h1>IntentGuard Results</h1>
    <pre>${results.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</pre>
</body>
</html>
    `;
    
    panel.webview.html = html;
}

/**
 * Command: Verify Current File
 */
async function verifyCurrentFile() {
    const editor = vscode.window.activeTextEditor;
    
    if (!editor) {
        vscode.window.showErrorMessage('No active file to verify');
        return;
    }
    
    const filePath = editor.document.uri.fsPath;
    
    // Ask for requirements file (use config default)
    const requirementsPath = path.join(path.dirname(filePath), config.requirementsFile);
    
    // Check if requirements file exists
    const fs = require('fs');
    if (!fs.existsSync(requirementsPath)) {
        const selected = await vscode.window.showOpenDialog({
            canSelectMany: false,
            filters: { 'Text': ['txt', 'md'] },
            defaultUri: vscode.Uri.file(path.dirname(filePath))
        });
        
        if (!selected || selected.length === 0) {
            vscode.window.showErrorMessage('Requirements file not specified');
            return;
        }
        
        await vscode.window.showInformationMessage(`Using requirements: ${selected[0].fsPath}`);
    }
    
    try {
        vscode.window.showInformationMessage('Running IntentGuard verification...');
        const results = await runVerification(filePath, fs.existsSync(requirementsPath) ? requirementsPath : selected[0].fsPath);
        showResults(results);
    } catch (err) {
        vscode.window.showErrorMessage(`Verification failed: ${err.message}`);
    }
}

/**
 * Command: Verify with Requirements File
 */
async function verifyWithRequirements() {
    const editor = vscode.window.activeTextEditor;
    
    if (!editor) {
        vscode.window.showErrorMessage('No active file to verify');
        return;
    }
    
    const filePath = editor.document.uri.fsPath;
    
    // Open file picker for requirements
    const selected = await vscode.window.showOpenDialog({
        canSelectMany: false,
        filters: { 'Text': ['txt', 'md'] },
        defaultUri: vscode.Uri.file(path.dirname(filePath))
    });
    
    if (!selected || selected.length === 0) {
        return;
    }
    
    try {
        vscode.window.showInformationMessage('Running IntentGuard verification...');
        const results = await runVerification(filePath, selected[0].fsPath);
        showResults(results);
    } catch (err) {
        vscode.window.showErrorMessage(`Verification failed: ${err.message}`);
    }
}

/**
 * Command: Configure IntentGuard
 */
async function configure() {
    await vscode.commands.executeCommand('workbench.action.openSettings', 'intentguard');
}

/**
 * Activate extension
 */
function activate(context) {
    console.log('IntentGuard extension activated');
    
    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('intentguard.verify', verifyCurrentFile),
        vscode.commands.registerCommand('intentguard.verifyFile', verifyWithRequirements),
        vscode.commands.registerCommand('intentguard.configure', configure)
    );
    
    // Register status bar item
    const statusBarItem = vscode.window.createStatusBarItem(0, 100);
    statusBarItem.text = 'IntentGuard';
    statusBarItem.tooltip = 'Click to verify current file';
    statusBarItem.command = 'intentguard.verify';
    statusBarItem.show();
    
    context.subscriptions.push(statusBarItem);
}

/**
 * Deactivate extension
 */
function deactivate() {}

module.exports = { activate, deactivate };