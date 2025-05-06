#!/usr/bin/env python
"""
Script to automatically update imports to use the new src structure.
"""
import os
import re

def update_file_imports(file_path, pattern, replacement):
    """
    Update imports in a file based on pattern and replacement.
    
    Args:
        file_path: Path to the file to update
        pattern: Regex pattern to search for
        replacement: Replacement string
    """
    try:
        with open(file_path, 'r') as file:
            content = file.read()
        
        updated_content = re.sub(pattern, replacement, content)
        
        if content != updated_content:
            with open(file_path, 'w') as file:
                file.write(updated_content)
            print(f"Updated: {file_path}")
        else:
            print(f"No changes needed: {file_path}")
            
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")

def process_directory(directory, excluded_paths=None):
    """
    Process all Python files in a directory and its subdirectories.
    
    Args:
        directory: Directory to process
        excluded_paths: List of paths to exclude
    """
    excluded_paths = excluded_paths or []
    
    # Define patterns and replacements
    patterns_and_replacements = [
        (r'from app import', 'from app import'),
        (r'from app\.', 'from app.'),
        (r'import src.app', 'import src.app'),
    ]
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                
                # Skip excluded paths
                if any(excluded_path in file_path for excluded_path in excluded_paths):
                    continue
                
                # Update imports in the file
                for pattern, replacement in patterns_and_replacements:
                    update_file_imports(file_path, pattern, replacement)

def main():
    """Main function to update imports."""
    # Process src directory
    process_directory('src')
    
    # Process scripts directory
    process_directory('scripts')
    
    # Process tests directory
    process_directory('tests')
    
    print("Import updates completed!")

if __name__ == "__main__":
    main() 