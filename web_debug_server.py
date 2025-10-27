#!/bin/bash
# web_debug_server.py - Web üzerinden terminal komutları çalıştırma

from flask import Flask, request, jsonify, render_template_string
import subprocess
import os

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Raspberry Pi Debug Terminal</title>
    <style>
        body { font-family: monospace; margin: 20px; background: #1e1e1e; color: #fff; }
        .terminal { background: #000; padding: 20px; border-radius: 5px; }
        input[type="text"] { width: 80%; padding: 10px; background: #333; color: #fff; border: 1px solid #555; }
        button { padding: 10px 20px; background: #007acc; color: white; border: none; cursor: pointer; }
        .output { background: #222; padding: 10px; margin: 10px 0; border-left: 3px solid #007acc; }
        .error { border-left-color: #ff4444; }
    </style>
</head>
<body>
    <h1>🔧 Raspberry Pi Debug Terminal</h1>
    <div class="terminal">
        <form onsubmit="runCommand(event)">
            <input type="text" id="command" placeholder="Enter command..." autofocus>
            <button type="submit">Run</button>
        </form>
        <div id="output"></div>
    </div>
    
    <h2>🚀 Quick Debug Commands</h2>
    <button onclick="runQuick('systemctl status ssh')">SSH Status</button>
    <button onclick="runQuick('netstat -tlnp | grep :22')">SSH Port</button>
    <button onclick="runQuick('ip addr')">IP Address</button>
    <button onclick="runQuick('curl ifconfig.me')">External IP</button>
    <button onclick="runQuick('ps aux | grep python')">Python Processes</button>
    <button onclick="runQuick('journalctl -u ssh -n 20')">SSH Logs</button>
    
    <script>
        function runCommand(event) {
            event.preventDefault();
            const command = document.getElementById('command').value;
            if (command.trim()) {
                executeCommand(command);
                document.getElementById('command').value = '';
            }
        }
        
        function runQuick(command) {
            executeCommand(command);
        }
        
        function executeCommand(command) {
            fetch('/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: command })
            })
            .then(response => response.json())
            .then(data => {
                const output = document.getElementById('output');
                const div = document.createElement('div');
                div.className = data.success ? 'output' : 'output error';
                div.innerHTML = `
                    <strong>$ ${command}</strong><br>
                    <pre>${data.output}</pre>
                `;
                output.insertBefore(div, output.firstChild);
            })
            .catch(error => {
                console.error('Error:', error);
            });
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/execute', methods=['POST'])
def execute_command():
    try:
        data = request.get_json()
        command = data.get('command', '')
        
        # Güvenlik için komut filtreleme
        dangerous_commands = ['rm -rf', 'format', 'fdisk', 'mkfs', 'dd if=']
        if any(dangerous in command.lower() for dangerous in dangerous_commands):
            return jsonify({
                'success': False,
                'output': 'Command blocked for security reasons'
            })
        
        # Komutu çalıştır
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
            
        return jsonify({
            'success': result.returncode == 0,
            'output': output,
            'returncode': result.returncode
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'output': 'Command timeout (30s limit)'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'output': f'Error: {str(e)}'
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)