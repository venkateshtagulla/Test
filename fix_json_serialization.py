"""
Script to replace json.dumps with json_dumps_safe in all Lambda handlers.
This fixes the Decimal serialization issue.
"""
import os
import re

# Directory containing Lambda handlers
lambda_dir = r"e:\KHM_Engineers\Software Projects\ARKA\Code\Web\backend-development\routers\lambda"

# Files to process
files_to_fix = [
    "inspection_form.py",
    "auth.py",
    "admin_auth.py",
    "vessel.py",
    "crew.py",
    "inspection_assignment.py",
    "defect.py",
    "upload.py",
    "dashboard.py",
    "admin_inspector.py"
]

for filename in files_to_fix:
    filepath = os.path.join(lambda_dir, filename)
    
    if not os.path.exists(filepath):
        print(f"Skipping {filename} - file not found")
        continue
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if json_dumps_safe import already exists
    has_import = 'from utility.json_encoder import json_dumps_safe' in content
    
    # Add import if not present
    if not has_import and 'json.dumps(' in content:
        # Find the last utility import
        import_pattern = r'(from utility\.\w+ import [^\n]+\n)'
        matches = list(re.finditer(import_pattern, content))
        if matches:
            last_import = matches[-1]
            insert_pos = last_import.end()
            content = content[:insert_pos] + 'from utility.json_encoder import json_dumps_safe\n' + content[insert_pos:]
            print(f"Added import to {filename}")
    
    # Replace json.dumps with json_dumps_safe
    original_content = content
    content = re.sub(r'\bjson\.dumps\(', 'json_dumps_safe(', content)
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed {filename}")
    else:
        print(f"No changes needed for {filename}")

print("\nDone! All Lambda handlers have been updated.")
