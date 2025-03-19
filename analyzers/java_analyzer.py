import subprocess
import os
import tempfile
from analyzers.base_analyzer import BaseAnalyzer

class JavaAnalyzer(BaseAnalyzer):
    def analyze(self, file_path):
        """
        Analyze Java code using PMD and SpotBugs
        """
        results = []
        
        # Run PMD
        try:
            pmd_output = subprocess.check_output(
                ['pmd', 'check', '-R', 'pmd.xml', '-f', 'text', file_path],
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            # Parse PMD output
            for line in pmd_output.splitlines():
                if file_path in line:
                    try:
                        # Extract line number and message
                        parts = line.split(file_path)[1].strip()
                        if ':' in parts:
                            line_num, message = parts.split(':', 1)
                            results.append({
                                'line': int(line_num),
                                'column': 1,
                                'message': message.strip(),
                                'type': 'error',
                                'symbol': 'pmd'
                            })
                    except (ValueError, IndexError):
                        continue
        except subprocess.CalledProcessError as e:
            if e.output:
                for line in e.output.splitlines():
                    if file_path in line:
                        try:
                            # Extract line number and message
                            parts = line.split(file_path)[1].strip()
                            if ':' in parts:
                                line_num, message = parts.split(':', 1)
                                results.append({
                                    'line': int(line_num),
                                    'column': 1,
                                    'message': message.strip(),
                                    'type': 'error',
                                    'symbol': 'pmd'
                                })
                        except (ValueError, IndexError):
                            continue
        except FileNotFoundError:
            results.append({
                'line': 1,
                'column': 1,
                'message': "PMD not found. Please install it with 'brew install pmd'",
                'type': 'error'
            })
        
        # Run javac to check for compilation errors
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                subprocess.check_output(
                    ['javac', '-d', temp_dir, file_path],
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )
        except subprocess.CalledProcessError as e:
            if e.output:
                for line in e.output.splitlines():
                    if ':' in line and 'error:' in line:
                        try:
                            # Extract line number and error message
                            parts = line.split(':')
                            if len(parts) >= 4:
                                line_num = int(parts[1])
                                message = ':'.join(parts[3:]).strip()
                                results.append({
                                    'line': line_num,
                                    'column': 1,
                                    'message': message,
                                    'type': 'error',
                                    'symbol': 'javac'
                                })
                        except (ValueError, IndexError):
                            continue
        except FileNotFoundError:
            results.append({
                'line': 1,
                'column': 1,
                'message': "Java compiler not found. Please install JDK",
                'type': 'error'
            })
        
        # Run SpotBugs if compilation succeeded
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                class_file = os.path.join(temp_dir, os.path.splitext(os.path.basename(file_path))[0] + '.class')
                
                # Compile Java file
                subprocess.check_output(
                    ['javac', '-d', temp_dir, file_path],
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )
                
                # Run SpotBugs
                spotbugs_output = subprocess.check_output(
                    ['spotbugs', '-textui', '-low', class_file],
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )
                
                # Parse SpotBugs output
                for line in spotbugs_output.splitlines():
                    if '[' in line and ']' in line and 'line' in line.lower():
                        try:
                            # Extract line number from the message
                            start = line.find('line') + 4
                            end = line.find(']', start)
                            if start > 4 and end > start:
                                line_num = int(line[start:end].strip())
                                message = line[end + 1:].strip()
                                results.append({
                                    'line': line_num,
                                    'column': 1,
                                    'message': message,
                                    'type': 'warning',
                                    'symbol': 'spotbugs'
                                })
                        except (ValueError, IndexError):
                            continue
        except (subprocess.CalledProcessError, FileNotFoundError):
            # SpotBugs errors are not critical
            pass
        
        return results