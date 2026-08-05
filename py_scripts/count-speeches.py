from pathlib import Path

def count_txt_files(folder_path):
    path = Path(folder_path)
    
    # Safety check: ensure the folder actually exists
    if not path.exists() or not path.is_dir():
        print(f"Error: The folder '{folder_path}' does not exist.")
        return

    # .rglob() stands for "recursive glob". It searches the root and ALL subfolders.
    # We turn the results into a list and simply count the length of that list.
    total_files = len(list(path.rglob('*.txt')))
    
    print(f"Total .txt files found: {total_files}")

# ==========================================
# CONFIGURATION & USAGE
# ==========================================

# Replace with the path to the folder you want to scan
target_folder = r"G:\Mon Drive\00 - Université\00 - Doctorat\00 - Recherches These\00 - Corpus\corpus v4\Bush"

count_txt_files(target_folder)