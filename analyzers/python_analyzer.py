import subprocess
import json
import os
from analyzers.base_analyzer import BaseAnalyzer

class PythonAnalyzer(BaseAnalyzer):
    def analyze(self, file_path):
        """
        Analyze Python code using pylint and flake8
        """
        results = []
        
        # Run pylint
        try:
            # Use pylint with JSON reporter
            pylint_output = subprocess.check_output(
                ['pylint', '--output-format=json', file_path],
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            # Parse pylint output
            pylint_issues = json.loads(pylint_output)
            for issue in pylint_issues:
                results.append({
                    'line': issue.get('line', 0),
                    'column': issue.get('column', 0),
                    'message': issue.get('message', ''),
                    'type': issue.get('type', ''),
                    'symbol': issue.get('symbol', '')
                })
        except subprocess.CalledProcessError as e:
            # Pylint returns non-zero exit code when it finds issues
            if e.output:
                try:
                    pylint_issues = json.loads(e.output)
                    for issue in pylint_issues:
                        results.append({
                            'line': issue.get('line', 0),
                            'column': issue.get('column', 0),
                            'message': issue.get('message', ''),
                            'type': issue.get('type', ''),
                            'symbol': issue.get('symbol', '')
                        })
                except json.JSONDecodeError:
                    # If output is not valid JSON, add a generic error
                    results.append({
                        'line': 1,
                        'column': 1,
                        'message': f"Error running pylint: {e.output}",
                        'type': 'error'
                    })
        except FileNotFoundError:
            # If pylint is not installed
            results.append({
                'line': 1,
                'column': 1,
                'message': "Pylint not found. Please install it with 'pip install pylint'",
                'type': 'error'
            })
        
        # Run flake8
        try:
            flake8_output = subprocess.check_output(
                ['flake8', '--format=default', file_path],
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            # Parse flake8 output (format: file:line:column: error_code message)
            for line in flake8_output.splitlines():
                parts = line.split(':', 3)
                if len(parts) >= 4:
                    file, line_num, col, error = parts
                    error_code, error_msg = error.strip().split(' ', 1)
                    results.append({
                        'line': int(line_num),
                        'column': int(col),
                        'message': error_msg.strip(),
                        'type': 'style' if error_code.startswith('E') else 'warning',
                        'symbol': error_code
                    })
        except subprocess.CalledProcessError as e:
            # Flake8 might return non-zero exit code
            if e.output:
                for line in e.output.splitlines():
                    parts = line.split(':', 3)
                    if len(parts) >= 4:
                        file, line_num, col, error = parts
                        error_code, error_msg = error.strip().split(' ', 1)
                        results.append({
                            'line': int(line_num),
                            'column': int(col),
                            'message': error_msg.strip(),
                            'type': 'style' if error_code.startswith('E') else 'warning',
                            'symbol': error_code
                        })
        except FileNotFoundError:
            # If flake8 is not installed
            results.append({
                'line': 1,
                'column': 1,
                'message': "Flake8 not found. Please install it with 'pip install flake8'",
                'type': 'error'
            })
        
        return results

