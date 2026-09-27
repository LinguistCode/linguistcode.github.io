### ---------------------
# Quick sanity check: how many speeches (.txt files) are in a corpus folder?
# Handy after each cleaning pass to make sure no file got lost along the way.
### ---------------------

from pathlib import Path

def count_txt_files(folder_path):
    path = Path(folder_path)
    
    # Bail out early if the path is wrong (typo in the drive letter, moved folder...).
    if not path.exists() or not path.is_dir():
        print(f"Error: The folder '{folder_path}' does not exist.")
        return

    # rglob = recursive glob -> also digs into the year subfolders.
    # No need to open anything: just list the matches and take the length.
    total_files = len(list(path.rglob('*.txt')))
    
    print(f"Total .txt files found: {total_files}")

### ---------------------
# CONFIG
### ---------------------

# Point this at the president folder to count (one run per president).
target_folder = r"A:\path\to\folder"

count_txt_files(target_folder)