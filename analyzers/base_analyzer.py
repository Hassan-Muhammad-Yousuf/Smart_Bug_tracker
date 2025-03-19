from abc import ABC, abstractmethod

class BaseAnalyzer(ABC):
    @abstractmethod
    def analyze(self, file_path):
        """
        Analyze the given file and return a list of issues found
        
        Each issue should be a dictionary with the following keys:
        - line: line number where the issue was found
        - column: column number where the issue was found
        - message: description of the issue
        - type: type of the issue (e.g., error, warning, style)
        """
        pass

