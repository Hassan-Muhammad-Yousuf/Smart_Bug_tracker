import os

def detect_language(file_path):
    """
    Detect the programming language of a file based on its extension.
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        str: The detected language, or None if not recognized
    """
    ext = get_file_extension(file_path)
    
    # Map file extensions to languages
    if ext in ['.py']:
        return 'python'
    elif ext in ['.js', '.jsx', '.ts', '.tsx']:
        return 'javascript'
    elif ext in ['.java']:
        return 'java'
    elif ext in ['.cpp', '.cc', '.cxx', '.c', '.h', '.hpp', '.hxx']:
        return 'cpp'
    elif ext in ['.go']:
        return 'go'
    
    return None

def get_file_extension(file_path):
    """
    Get the file extension from a file path.
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        str: The file extension (including the dot)
    """
    _, ext = os.path.splitext(file_path)
    return ext.lower()

