import os
import json
import subprocess
import tempfile
import re

class GoAnalyzer:
    def __init__(self):
        # Check if Go is installed
        try:
            subprocess.run(['go', 'version'], 
                          check=True, 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE)
        except (subprocess.SubprocessError, FileNotFoundError):
            print("Warning: Go not found. Please install Go to analyze Go files.")
        
        # Check if golint is installed
        try:
            subprocess.run(['golint', '-h'], 
                          check=True, 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE)
        except (subprocess.SubprocessError, FileNotFoundError):
            print("Warning: golint not found. Installing golint...")
            try:
                subprocess.run(['go', 'install', 'golang.org/x/lint/golint@latest'], 
                              check=True, 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE)
                print("golint installed successfully.")
            except (subprocess.SubprocessError, FileNotFoundError):
                print("Error: Failed to install golint. Please install it manually.")
        
        # Check if staticcheck is installed
        try:
            subprocess.run(['staticcheck', '-h'], 
                          check=True, 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE)
        except (subprocess.SubprocessError, FileNotFoundError):
            print("Warning: staticcheck not found. Installing staticcheck...")
            try:
                subprocess.run(['go', 'install', 'honnef.co/go/tools/cmd/staticcheck@latest'], 
                              check=True, 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE)
                print("staticcheck installed successfully.")
            except (subprocess.SubprocessError, FileNotFoundError):
                print("Error: Failed to install staticcheck. Please install it manually.")
    
    def analyze(self, file_path):
        print(f"Analyzing Go file: {file_path}")
        
        results = []
        
        # Run go vet
        vet_results = self._run_go_vet(file_path)
        results.extend(vet_results)
        
        # Run golint
        lint_results = self._run_golint(file_path)
        results.extend(lint_results)
        
        # Run staticcheck
        staticcheck_results = self._run_staticcheck(file_path)
        results.extend(staticcheck_results)
        
        # Perform manual analysis
        manual_results = self._manual_analyze(file_path)
        results.extend(manual_results)
        
        # If no results from tools, rely on manual analysis
        if not results:
            return manual_results
        
        return results
    
    def _run_go_vet(self, file_path):
        results = []
        try:
            # Create a temporary directory for go vet
            with tempfile.TemporaryDirectory() as temp_dir:
                # Copy the file to the temp directory
                temp_file = os.path.join(temp_dir, os.path.basename(file_path))
                with open(file_path, 'r') as src, open(temp_file, 'w') as dst:
                    dst.write(src.read())
                
                # Run go vet
                process = subprocess.run(
                    ['go', 'vet', temp_file],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Parse go vet output
                if process.stderr:
                    lines = process.stderr.strip().split('\n')
                    for line in lines:
                        if line and os.path.basename(file_path) in line:
                            # Extract line number and message
                            match = re.search(r'(\d+):\s*(.*)', line)
                            if match:
                                line_num = int(match.group(1))
                                message = match.group(2)
                                results.append({
                                    'line': line_num,
                                    'column': 1,
                                    'message': message,
                                    'type': 'go_vet',
                                    'severity': 'high'
                                })
        except Exception as e:
            print(f"Error running go vet: {e}")
        
        return results
    
    def _run_golint(self, file_path):
        results = []
        try:
            process = subprocess.run(
                ['golint', file_path],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Parse golint output
            if process.stdout:
                lines = process.stdout.strip().split('\n')
                for line in lines:
                    if line:
                        # Extract line number and message
                        match = re.search(r'(\d+):\d+:\s*(.*)', line)
                        if match:
                            line_num = int(match.group(1))
                            message = match.group(2)
                            results.append({
                                'line': line_num,
                                'column': 1,
                                'message': message,
                                'type': 'golint',
                                'severity': 'medium'
                            })
        except Exception as e:
            print(f"Error running golint: {e}")
        
        return results
    
    def _run_staticcheck(self, file_path):
        results = []
        try:
            # Create a temporary directory for staticcheck
            with tempfile.TemporaryDirectory() as temp_dir:
                # Copy the file to the temp directory
                temp_file = os.path.join(temp_dir, os.path.basename(file_path))
                with open(file_path, 'r') as src, open(temp_file, 'w') as dst:
                    dst.write(src.read())
                
                # Initialize a Go module in the temp directory
                subprocess.run(
                    ['go', 'mod', 'init', 'tempmod'],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=temp_dir
                )
                
                # Run staticcheck
                process = subprocess.run(
                    ['staticcheck', '.'],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=temp_dir
                )
                
                # Parse staticcheck output
                if process.stdout:
                    lines = process.stdout.strip().split('\n')
                    for line in lines:
                        if line and os.path.basename(file_path) in line:
                            # Extract line number and message
                            match = re.search(r'(\d+):\d+:\s*(.*)', line)
                            if match:
                                line_num = int(match.group(1))
                                message = match.group(2)
                                results.append({
                                    'line': line_num,
                                    'column': 1,
                                    'message': message,
                                    'type': 'staticcheck',
                                    'severity': 'high'
                                })
        except Exception as e:
            print(f"Error running staticcheck: {e}")
        
        return results
    
    def _manual_analyze(self, file_path):
        """Perform a basic manual analysis for Go files"""
        results = []
        try:
            with open(file_path, 'r') as f:
                code = f.read()
                
            lines = code.split('\n')
            
            # Check for common issues
            for i, line in enumerate(lines):
                line_num = i + 1
                
                # Check for error handling
                if 'err :=' in line or ', err :=' in line or 'err =' in line or ', err =' in line:
                    # Check if the next line checks for errors
                    if i + 1 < len(lines) and 'if err != nil' not in lines[i+1] and 'if err != nil' not in line:
                        results.append({
                            'line': line_num,
                            'column': line.find('err'),
                            'message': 'Error not checked',
                            'type': 'error_check',
                            'severity': 'high'
                        })
                
                # Check for unused variables
                if ':=' in line:
                    var_name = line.split(':=')[0].strip()
                    if ',' in var_name:
                        # Multiple assignment
                        vars = [v.strip() for v in var_name.split(',')]
                        for v in vars:
                            if v != '_' and v not in ' '.join(lines[i+1:]):
                                results.append({
                                    'line': line_num,
                                    'column': line.find(v),
                                    'message': f"Variable '{v}' declared but not used",
                                    'type': 'unused_var',
                                    'severity': 'medium'
                                })
                    else:
                        # Single assignment
                        if var_name != '_' and var_name not in ' '.join(lines[i+1:]):
                            results.append({
                                'line': line_num,
                                'column': line.find(var_name),
                                'message': f"Variable '{var_name}' declared but not used",
                                'type': 'unused_var',
                                'severity': 'medium'
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
                
                # Check for missing defer for file operations
                if 'os.Open(' in line or 'os.Create(' in line:
                    # Extract variable name
                    var_match = re.search(r'(\w+)\s*:?=\s*os\.(Open|Create)', line)
                    if var_match:
                        var_name = var_match.group(1)
                        # Check if there's a defer for closing the file
                        defer_found = False
                        for j in range(i+1, min(i+10, len(lines))):
                            if f'defer {var_name}.Close()' in lines[j]:
                                defer_found = True
                                break
                        if not defer_found:
                            results.append({
                                'line': line_num,
                                'column': line.find('os.'),
                                'message': f"File '{var_name}' opened but not deferred for closing",
                                'type': 'missing_defer',
                                'severity': 'medium'
                            })
                
                # Check for nil pointer dereference
                if '*' in line and '=' in line:
                    var_match = re.search(r'\*(\w+)\s*=', line)
                    if var_match:
                        var_name = var_match.group(1)
                        # Check if there's a nil check before dereferencing
                        nil_check_found = False
                        for j in range(max(0, i-5), i):
                            if f'if {var_name} == nil' in lines[j] or f'if {var_name} != nil' in lines[j]:
                                nil_check_found = True
                                break
                        if not nil_check_found:
                            results.append({
                                'line': line_num,
                                'column': line.find('*'),
                                'message': f"Possible nil pointer dereference of '{var_name}'",
                                'type': 'nil_deref',
                                'severity': 'high'
                            })
            
            return results
                
        except Exception as e:
            print(f"Error in manual analysis: {e}")
            return []

