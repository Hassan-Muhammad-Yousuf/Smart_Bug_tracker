import os
import re
from openai import OpenAI
from dotenv import load_dotenv

class AICodeFixer:
    """
    A class that uses OpenAI's GPT models to generate code fix suggestions
    for bugs identified in the Smart Bug Tracker.
    """
    
    def __init__(self):
        """
        Initialize the AICodeFixer with the OpenAI API key from environment variables.
        """
        # Load environment variables from .env file
        load_dotenv()
        
        # Get API key from environment variable
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            print("Warning: OPENAI_API_KEY environment variable not set. AI code fixing will not work.")
            self.client = None
        else:
            # Initialize the OpenAI client
            self.client = OpenAI(api_key=api_key)
        
        # Default model to use
        self.model = "gpt-4o"
        
        # Context window size for extracting code around the bug
        self.context_lines = 10
    
    def extract_code_context(self, file_path, line_number, context_lines=None):
        """
        Extract code context around the specified line number from a file.
        
        Args:
            file_path (str): Path to the file
            line_number (int): Line number where the bug was detected
            context_lines (int, optional): Number of lines to include before and after the bug line
            
        Returns:
            str: Code snippet with context around the bug
        """
        if context_lines is None:
            context_lines = self.context_lines
            
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                
            # Calculate start and end lines for context
            start_line = max(0, line_number - context_lines - 1)
            end_line = min(len(lines), line_number + context_lines)
            
            # Extract the relevant lines
            context = ''.join(lines[start_line:end_line])
            
            return context
        except Exception as e:
            print(f"Error extracting code context: {e}")
            return ""
    
    def generate_fix(self, code_snippet, error_message, language, line_number):
        """
        Generate a fix suggestion for the given code snippet and error message.
        
        Args:
            code_snippet (str): The code snippet containing the bug
            error_message (str): The error message or bug description
            language (str): The programming language of the code
            line_number (int): The line number where the bug was detected
            
        Returns:
            dict: A dictionary containing the suggestion and code example
        """
        if not hasattr(self, 'client') or self.client is None:
            return {
                "suggestion": "AI code fixing is not available. Please set the OPENAI_API_KEY environment variable.",
                "code_example": ""
            }
        
        try:
            # Create a prompt for the AI using string concatenation instead of f-string
            prompt = (
                "You are an expert software engineer. Analyze this code snippet and provide a minimal, focused fix for the specific bug.\n\n"
                "Your response should be concise and include:\n"
                "1. A brief explanation of the issue (1-2 sentences)\n"
                "2. The corrected code (only the relevant lines that need to be changed)\n\n"
                f"Language: {language}\n"
                f"Error/Bug: {error_message}\n"
                f"Line Number: {line_number}\n\n"
                "Code:\n"
                f"```{language}\n"
                f"{code_snippet}\n"
                "```\n\n"
                "Provide only the necessary fix without additional explanations or best practices."
            )
            
            # Call the OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert software engineer specializing in debugging and fixing code issues."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,  # Lower temperature for more focused responses
                max_tokens=500    # Limit token count for concise responses
            )
            
            # Extract the response
            ai_response = response.choices[0].message.content
            
            # Parse the response to extract suggestion and code example
            suggestion, code_example = self._parse_ai_response(ai_response, language)
            
            return {
                "suggestion": suggestion,
                "code_example": code_example
            }
            
        except Exception as e:
            print(f"Error generating AI fix: {e}")
            return {
                "suggestion": f"Failed to generate AI fix: {str(e)}",
                "code_example": ""
            }
    
    def _parse_ai_response(self, response, language):
        """
        Parse the AI response to extract the suggestion and code example.
        
        Args:
            response (str): The raw response from the AI
            language (str): The programming language
            
        Returns:
            tuple: (suggestion, code_example)
        """
        # Extract code blocks using regex
        code_pattern = r"```(?:\w+)?\n([\s\S]*?)\n```"
        code_blocks = re.findall(code_pattern, response)
        
        # Extract the code example (use the first code block if available)
        code_example = code_blocks[0] if code_blocks else ""
        
        # Remove code blocks from the response to get the suggestion
        suggestion = re.sub(code_pattern, "", response).strip()
        
        return suggestion, code_example

