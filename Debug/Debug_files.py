import os


def collect_py_files_text(folder_path, output_file):
    # Open the output file in write mode
    with open(output_file, 'w') as outfile:
        # Walk through all files in the given directory
        for root, dirs, files in os.walk(folder_path):
            # Filter for .py files only
            py_files = [file for file in files if file.endswith('.py')]

            for py_file in py_files:
                # Construct the full file path
                file_path = os.path.join(root, py_file)

                # Write the file name as a header
                outfile.write(f"--- {py_file} ---\n")

                # Read the content of the .py file
                with open(file_path, 'r') as infile:
                    outfile.write(infile.read())

                # Add a blank line after each file's content
                outfile.write("\n\n")


# Example usage:
folder_path = 'H:/Pycharm_project/Inline_Data_Analytics_use/gui'  # Replace with the path to your folder
output_file = 'collected_py_files)1.txt'
collect_py_files_text(folder_path, output_file)

print(f"All .py files have been collected into {output_file}")