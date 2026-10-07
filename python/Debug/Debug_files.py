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
folder_path_2 = 'H:/Pycharm_project/Inline_Data_Analytics_use/gui'
folder_path_1 = 'H:/Pycharm_project/Inline_Data_Analytics_use/gui/components'
output_file_1 = 'Collected_components.txt'
output_file_2 = 'Collected_gui.txt'
collect_py_files_text(folder_path_1, output_file_1)

collect_py_files_text(folder_path_2, output_file_2)

print(f"All .py files have been collected into {output_file_1}")