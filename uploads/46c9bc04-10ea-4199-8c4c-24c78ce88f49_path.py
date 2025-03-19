import os

def print_directory_structure(path, level=0):
    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        if os.path.isdir(item_path):
            print("    " * level + f"[DIR] {item}")
            print_directory_structure(item_path, level + 1)
        else:
            print("    " * level + f"[FILE] {item}")

project_path = "/Users/king/Desktop/Study Material /Software and AI"  
print_directory_structure(project_path)
