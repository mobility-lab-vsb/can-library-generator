import os
import shutil

output_dir = os.path.join(os.path.dirname(__file__), '..', 'temp')

def delete_temp_files():
    for filename in os.listdir(output_dir):
        file_path = os.path.join(output_dir, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
            print(f"Removing {file_path}...")
        except Exception as e:
            print(f"Error removing {file_path}: {e}")

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
        print(f"Removing {output_dir}...")

if __name__ == "__main__":
    delete_temp_files()