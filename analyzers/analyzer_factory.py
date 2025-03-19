from analyzers.javascript_analyzer import JavaScriptAnalyzer
from analyzers.python_analyzer import PythonAnalyzer
from analyzers.go_analyzer import GoAnalyzer
from analyzers.java_analyzer import JavaAnalyzer
from analyzers.cpp_analyzer import CppAnalyzer

class AnalyzerFactory:
    def __init__(self):
        self.analyzers = {
            'javascript': JavaScriptAnalyzer(),
            'python': PythonAnalyzer(),
            'go': GoAnalyzer(),
            'java': JavaAnalyzer(),
            'cpp': CppAnalyzer()
        }
    
    def get_analyzer(self, language):
        """
        Get the appropriate analyzer for the given language.
        
        Args:
            language (str): The programming language to analyze
            
        Returns:
            object: The analyzer for the specified language, or None if not supported
        """
        return self.analyzers.get(language.lower())

