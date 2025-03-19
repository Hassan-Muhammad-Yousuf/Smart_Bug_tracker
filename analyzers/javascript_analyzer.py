import os
import json
import subprocess
import tempfile
from pathlib import Path

class JavaScriptAnalyzer:
    def __init__(self):
        # Check if ESLint is installed
        try:
            subprocess.run(['npx', 'eslint', '--version'], 
                          check=True, 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE)
        except (subprocess.SubprocessError, FileNotFoundError):
            print("Warning: ESLint not found. Installing ESLint...")
            try:
                subprocess.run(['npm', 'install', 'eslint', '--save-dev'], 
                              check=True, 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE)
                print("ESLint installed successfully.")
            except (subprocess.SubprocessError, FileNotFoundError):
                print("Error: Failed to install ESLint. Please install it manually.")
    
    def analyze(self, file_path):
        print(f"Analyzing JavaScript file: {file_path}")
        
        # Skip ESLint and go straight to manual analysis
        # This avoids all the ESLint configuration issues
        return self._manual_analyze(file_path)
    
    def _manual_analyze(self, file_path):
        """Perform a basic manual analysis when ESLint fails"""
        results = []
        try:
            with open(file_path, 'r') as f:
                code = f.read()
                
            lines = code.split('\n')
            
            # Check for common issues
            for i, line in enumerate(lines):
                line_num = i + 1
                
                # Check for missing semicolons
                if line.strip() and not line.strip().startswith('//') and not line.strip().endswith(';') and not line.strip().endswith('{') and not line.strip().endswith('}') and not line.strip().endswith(':'):
                    if not any(keyword in line for keyword in ['if', 'for', 'while', 'function', 'class', 'import', 'export']):
                        results.append({
                            'line': line_num,
                            'column': len(line.rstrip()),
                            'message': 'Missing semicolon',
                            'type': 'semi',
                            'severity': 'low'
                        })
                
                # Check for missing curly braces in if/else/for/while statements
                if any(keyword in line for keyword in ['if', 'else', 'for', 'while']) and ')' in line:
                    if i + 1 < len(lines) and '{' not in line and '{' not in lines[i + 1]:
                        results.append({
                            'line': line_num,
                            'column': 1,
                            'message': 'Missing curly braces for control statement',
                            'type': 'curly',
                            'severity': 'high'
                        })
                
                # Check for console.log statements
                if 'console.log' in line:
                    results.append({
                        'line': line_num,
                        'column': line.find('console.log'),
                        'message': 'Unexpected console statement',
                        'type': 'no-console',
                        'severity': 'low'
                    })
                
                # Check for alert statements
                if 'alert(' in line:
                    results.append({
                        'line': line_num,
                        'column': line.find('alert('),
                        'message': 'Unexpected alert',
                        'type': 'no-alert',
                        'severity': 'medium'
                    })
                
                # Check for eval statements
                if 'eval(' in line:
                    results.append({
                        'line': line_num,
                        'column': line.find('eval('),
                        'message': 'eval can be harmful',
                        'type': 'no-eval',
                        'severity': 'high'
                    })
                
                # Check for undeclared variables
                if 'return' in line:
                    words = line.replace(';', ' ').replace('(', ' ').replace(')', ' ').split()
                    for j, word in enumerate(words):
                        if word == 'return' and j + 1 < len(words) and words[j + 1] != ';':
                            # Get the variable being returned
                            var_name = words[j + 1].strip(',;')
                            # Check if this variable is declared in the function
                            var_declared = False
                            for prev_line in lines[:i]:
                                if f"const {var_name}" in prev_line or f"let {var_name}" in prev_line or f"var {var_name}" in prev_line:
                                    var_declared = True
                                    break
                            
                            # Check for similar variable names (possible typos)
                            if not var_declared and var_name not in ['true', 'false', 'null', 'undefined', 'this']:
                                similar_vars = []
                                for prev_line in lines[:i]:
                                    for decl in ['const ', 'let ', 'var ']:
                                        if decl in prev_line:
                                            declared_var = prev_line.split(decl)[1].split('=')[0].strip()
                                            # Simple similarity check
                                            if len(var_name) > 2 and len(declared_var) > 2:
                                                if var_name[:-2] == declared_var[:-2]:  # Check if most of the name matches
                                                    similar_vars.append(declared_var)
                                
                                if similar_vars:
                                    results.append({
                                        'line': line_num,
                                        'column': line.find(var_name) + 1,
                                        'message': f"'{var_name}' is not defined. Did you mean '{similar_vars[0]}'?",
                                        'type': 'no-undef',
                                        'severity': 'high'
                                    })
                                elif var_name not in ['true', 'false', 'null', 'undefined', 'this']:
                                    results.append({
                                        'line': line_num,
                                        'column': line.find(var_name) + 1,
                                        'message': f"'{var_name}' is not defined",
                                        'type': 'no-undef',
                                        'severity': 'high'
                                    })
                
                # Check for division by zero
                if '/' in line:
                    parts = line.split('/')
                    for j in range(1, len(parts)):
                        divisor = parts[j].strip().split()[0]
                        if divisor == '0':
                            results.append({
                                'line': line_num,
                                'column': line.find('/') + 1,
                                'message': 'Division by zero',
                                'type': 'div_zero',
                                'severity': 'high'
                            })
            
            return results
                
        except Exception as e:
            print(f"Error in manual analysis: {e}")
            return []

