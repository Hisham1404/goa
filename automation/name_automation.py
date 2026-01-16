import os
import re
from pathlib import Path

def clean_filename(filename):
    """
    Remove 'enhanced', 'enhance', 'contour', and 'countour' from filename while preserving numbers and other parts
    """
    # Get filename without extension
    name, ext = os.path.splitext(filename)
    
    # Remove 'enhanced' with optional underscores before/after (case insensitive)
    name = re.sub(r'_?enhanced_?', '', name, flags=re.IGNORECASE)
    
    # Remove 'enhance' with optional underscores before/after (case insensitive)
    name = re.sub(r'_?enhance_?', '', name, flags=re.IGNORECASE)
    
    # Remove 'contour' with optional underscores before/after (case insensitive)
    name = re.sub(r'_?contour_?', '', name, flags=re.IGNORECASE)
    
    # Remove 'countour' with optional underscores before/after (case insensitive)
    name = re.sub(r'_?countour_?', '', name, flags=re.IGNORECASE)

    name = re.sub(r'_?enchanced_?', '', name, flags=re.IGNORECASE)

    name = re.sub(r'_?enchance_?', '', name, flags=re.IGNORECASE)

    
    # Clean up multiple consecutive underscores
    name = re.sub(r'_{2,}', '_', name)
    
    # Remove any leading/trailing underscores or spaces
    name = name.strip('_').strip()
    
    # If name is empty after cleaning, use 'image'
    if not name:
        name = 'image'
    
    return name + ext

def rename_images_in_folder(folder_path):
    """
    Rename all image files in the specified folder
    """
    if not os.path.exists(folder_path):
        print(f"Folder not found: {folder_path}")
        return
    
    # Common image extensions
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif'}
    
    renamed_count = 0
    
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        
        # Skip if it's a directory
        if os.path.isdir(file_path):
            continue
        
        # Check if it's an image file
        _, ext = os.path.splitext(filename.lower())
        if ext not in image_extensions:
            continue
        
        # Check if filename contains any of the target words
        if any(word in filename.lower() for word in ['enhanced', 'enhance', 'contour', 'countour', 'enchanced', 'enchance']):
            new_filename = clean_filename(filename)
            new_file_path = os.path.join(folder_path, new_filename)
            
            # Avoid overwriting existing files
            counter = 1
            original_new_filename = new_filename
            while os.path.exists(new_file_path):
                name, ext = os.path.splitext(original_new_filename)
                new_filename = f"{name}_{counter}{ext}"
                new_file_path = os.path.join(folder_path, new_filename)
                counter += 1
            
            try:
                os.rename(file_path, new_file_path)
                print(f"Renamed: {filename} -> {new_filename}")
                renamed_count += 1
            except OSError as e:
                print(f"Error renaming {filename}: {e}")
    
    print(f"Total files renamed in {folder_path}: {renamed_count}")

def main():
    """
    Main function to process multiple folders
    """
    # Define your folder paths here
    folders_to_process = [
        r"../maps\ambeli\plots\1/enhanced",
        # Add more folder paths as needed
    ]
    
    print("Starting image renaming process...")
    
    for folder_path in folders_to_process:
        print(f"\nProcessing folder: {folder_path}")
        rename_images_in_folder(folder_path)
    
    print("\nRenaming process completed!")

def process_single_folder():
    """
    Interactive function to process a single folder
    """
    folder_path = input("Enter the folder path: ").strip()
    rename_images_in_folder(folder_path)

if __name__ == "__main__":
    # You can either run main() for predefined folders or process_single_folder() for interactive mode
    
    choice = input("Enter '1' for predefined folders or '2' for single folder input: ").strip()
    
    if choice == '1':
        main()
    elif choice == '2':
        process_single_folder()
    else:
        print("Invalid choice. Running predefined folders...")
        main()
