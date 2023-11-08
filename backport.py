def backport_patch(file_path, anchor, new_lines):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Find the index of the anchor line
    anchor_index = None
    for i, line in enumerate(lines):
        if anchor in line:
            anchor_index = i
            break

    if anchor_index is not None:
        # Insert new lines after the anchor
        for i, new_line in enumerate(new_lines):
            lines.insert(anchor_index + 1 + i, new_line)
            
        with open(file_path, 'w') as file:
            file.writelines(lines)
    else:
        print("Anchor line not found.")

# Usage
file_path = 'path_to_your_file.js'
anchor = 'function setProp(dst, path, value) {'
new_lines = [
    '    if (part === "__proto__") {\n',
    '        return dst;\n',
    '    }\n'
]

backport_patch(file_path, anchor, new_lines)
