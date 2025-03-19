# models/bug_classifier.py
import json
import os
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

class BugClassifier:
    def __init__(self, model_path='models/bug_classifier.pkl'):
        self.model_path = model_path
        self.model = None
        self.load_model()
        
        # Fallback rules for when the model is not available
        self.severity_keywords = {
            'critical': [
                'segmentation fault', 'memory leak', 'buffer overflow', 'null pointer',
                'race condition', 'deadlock', 'security', 'vulnerability', 'crash',
                'exception', 'infinite loop', 'resource leak', 'data loss'
            ],
            'high': [
                'performance', 'memory usage', 'thread safety', 'concurrency',
                'resource', 'timeout', 'error handling', 'undefined behavior',
                'uninitialized', 'memory corruption'
            ],
            'medium': [
                'code style', 'maintainability', 'readability', 'naming convention',
                'documentation', 'deprecated', 'warning', 'unused', 'complexity'
            ],
            'low': [
                'whitespace', 'formatting', 'comment', 'typo', 'style guide',
                'minor', 'cosmetic', 'trivial'
            ]
        }
        
        # Language-specific severity mappings
        self.language_severity = {
            'python': {
                'error': 'high',
                'warning': 'medium',
                'convention': 'low',
                'refactor': 'low',
                'F': 'high',  # Fatal errors that prevent further processing
                'E': 'high',  # Error for important programming issues
                'W': 'medium',  # Warning for stylistic or minor programming issues
                'C': 'low',  # Convention for coding standard violations
                'R': 'low',  # Refactor for bad code smell
            },
            'javascript': {
                'error': 'high',
                'warning': 'medium',
                'suggestion': 'low',
            },
            'java': {
                'error': 'high',
                'warning': 'medium',
                'info': 'low',
            },
            'cpp': {
                'error': 'high',
                'warning': 'medium',
                'style': 'low',
                'performance': 'medium',
                'portability': 'medium',
                'information': 'low',
            },
            'go': {
                'error': 'high',
                'warning': 'medium',
                'info': 'low',
            }
        }
    
    def load_model(self):
        """
        Load the trained model from disk or create a new one if it doesn't exist
        """
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
            except:
                self.model = None
        else:
            # Create a simple model with some training data
            self.train_model()
    
    def train_model(self):
        """
        Train a simple model for bug classification
        """
        # Sample training data
        X = [
            # Critical bugs
            "Segmentation fault when accessing null pointer",
            "Memory leak in allocation routine",
            "Buffer overflow vulnerability in string handling",
            "Race condition in concurrent access",
            "Deadlock in thread synchronization",
            "Security vulnerability in input validation",
            "Application crashes when processing malformed input",
            "Unhandled exception in critical path",
            "Infinite loop in main processing routine",
            "Resource leak in file handling",
            
            # High severity bugs
            "Performance degradation in sorting algorithm",
            "Excessive memory usage in data processing",
            "Thread safety issue in shared resource access",
            "Timeout in network communication",
            "Missing error handling in file operations",
            "Undefined behavior when using uninitialized variable",
            "Memory corruption in array manipulation",
            "Resource exhaustion under heavy load",
            "Incorrect error propagation",
            "Improper exception handling",
            
            # Medium severity bugs
            "Code style violation in class naming",
            "Poor maintainability due to complex method",
            "Readability issues in nested conditionals",
            "Using deprecated API",
            "Warning about potential side effects",
            "Unused variable in function",
            "High cyclomatic complexity in method",
            "Missing documentation for public API",
            "Inconsistent return values",
            "Redundant code that could be simplified",
            
            # Low severity bugs
            "Inconsistent whitespace in indentation",
            "Formatting issues in code alignment",
            "Missing or outdated comments",
            "Typo in variable name",
            "Style guide violation in brace placement",
            "Minor optimization opportunity",
            "Cosmetic issue in UI component",
            "Trivial code duplication",
            "Unnecessary import or include",
            "Inconsistent line endings"
        ]
        
        y = (
            ["critical"] * 10 + 
            ["high"] * 10 + 
            ["medium"] * 10 + 
            ["low"] * 10
        )
        
        # Create and train the model
        self.model = Pipeline([
            ('vectorizer', TfidfVectorizer(max_features=1000)),
            ('classifier', MultinomialNB())
        ])
        
        self.model.fit(X, y)
        
        # Save the model
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.model, f)
    
    def classify(self, language, bug_type, message):
        """
        Classify a bug based on its type and message
        
        Returns one of: 'critical', 'high', 'medium', 'low'
        """
        # First, check if we have a language-specific mapping for this bug type
        language = language.lower() if language else 'unknown'
        if language in self.language_severity and bug_type in self.language_severity[language]:
            return self.language_severity[language][bug_type]
        
        # If we have a trained model, use it
        if self.model:
            try:
                severity = self.model.predict([message])[0]
                return severity
            except:
                pass
        
        # Fallback to keyword-based classification
        message_lower = message.lower()
        
        # Check for critical keywords first
        for severity, keywords in self.severity_keywords.items():
            for keyword in keywords:
                if keyword in message_lower:
                    return severity
        
        # Default to medium if no keywords match
        return "medium"