import subprocess
import xml.etree.ElementTree as ET
import tempfile
from analyzers.base_analyzer import BaseAnalyzer

class CppAnalyzer(BaseAnalyzer):
    def analyze(self, file_path):
        """
        Analyze C++ code using Cppcheck
        """
        results = []
        
        # Create a temporary file for Cppcheck output
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as temp:
            temp_output_path = temp.name
        
        try:
            # Run Cppcheck with XML output
            subprocess.check_output(
                [
                    'cppcheck', 
                    '--enable=all', 
                    '--xml', 
                    f'--output-file={temp_output_path}',
                    file_path
                ],
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            # Parse Cppcheck output
            tree = ET.parse(temp_output_path)
            root = tree.getroot()
            
            for error in root.findall('.//error'):
                location = error.find('location')
                if location is not None:
                    results.append({
                        'line': int(location.get('line', 0)),
                        'column': 0,  # Cppcheck doesn't provide column info
                        'message': error.get('msg', ''),
                        'type': error.get('severity', 'warning'),
                        'symbol': error.get('id', '')
                    })
        except subprocess.CalledProcessError as e:
            # Cppcheck might return non-zero exit code
            # Try to parse the output anyway
            try:
                tree = ET.parse(temp_output_path)
                root = tree.getroot()
                
                for error in root.findall('.//error'):
                    location = error.find('location')
                    if location is not None:
                        results.append({
                            'line': int(location.get('line', 0)),
                            'column': 0,
                            'message': error.get('msg', ''),
                            'type': error.get('severity', 'warning'),
                            'symbol': error.get('id', '')
                        })
            except:
                # If parsing fails, add a generic error
                results.append({
                    'line': 1,
                    'column': 1,
                    'message': f"Error running Cppcheck: {e.output}",
                    'type': 'error'
                })
        except FileNotFoundError:
            # If Cppcheck is not installed
            results.append({
                'line': 1,
                'column': 1,
                'message': "Cppcheck not found. Please install it from http://cppcheck.sourceforge.net/",
                'type': 'error'
            })
        
        return results

