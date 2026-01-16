import os

def rename_images_to_map():
    """
    Automate renaming of image files in numbered folders within latambarcem directory.
    Changes any image file to 'map' while preserving the original extension.
    """
    
    # Base directory containing numbered folders
    base_dir = "../latambarcem"
    
    if not os.path.exists(base_dir):
        print(f"Error: Directory '{base_dir}' not found!")
        return
    
    # Get all subdirectories (numbered folders)
    subdirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    
    # Common image file extensions
    image_extensions = ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp', '.gif', '.webp']
    
    renamed_count = 0
    skipped_count = 0
    
    print(f"Starting automation for {len(subdirs)} folders...")
    print("-" * 60)
    
    for folder_name in sorted(subdirs):
        folder_path = os.path.join(base_dir, folder_name)
        print(f"Processing folder: {folder_name}")
        
        # Find all files in the folder
        try:
            all_files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
        except PermissionError:
            print(f"  ❌ Permission denied for folder {folder_name}")
            skipped_count += 1
            continue
        
        # Find image files
        image_files = []
        for file in all_files:
            file_ext = os.path.splitext(file)[1].lower()
            if file_ext in image_extensions:
                image_files.append(file)
        
        if not image_files:
            print(f"  ⚠️  No image files found")
            skipped_count += 1
            continue
        
        # Rename the first (or only) image file
        original_file = image_files[0]
        file_ext = os.path.splitext(original_file)[1]
        new_filename = f"map{file_ext}"
        
        old_path = os.path.join(folder_path, original_file)
        new_path = os.path.join(folder_path, new_filename)
        
        try:
            # Check if target file already exists
            if os.path.exists(new_path):
                if original_file == new_filename:
                    print(f"  ✅ Already correctly named: {new_filename}")
                else:
                    print(f"  ⚠️  Target file already exists: {new_filename}")
                skipped_count += 1
                continue
            
            # Rename the file
            os.rename(old_path, new_path)
            print(f"  ✅ Renamed: '{original_file}' → '{new_filename}'")
            renamed_count += 1
            
        except Exception as e:
            print(f"  ❌ Error renaming '{original_file}': {str(e)}")
            skipped_count += 1
    
    print("-" * 60)
    print(f"✨ Automation completed successfully!")
    print(f"📁 Files renamed: {renamed_count}")
    print(f"⏭️  Files skipped: {skipped_count}")
    print(f"📂 Total folders processed: {len(subdirs)}")

if __name__ == "__main__":
    print("🔄 Image File Renaming Automation")
    print("=" * 60)
    rename_images_to_map() 