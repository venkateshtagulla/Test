#!/usr/bin/env python3
"""Add Inspection Name field to the inspection creation form."""

import os

file_path = r'e:\KHM_Engineers\Software Projects\ARKA\Code\Web\frontend-development\src\app\inspection\create\page.tsx'

# Backup the file first
backup_path = file_path + '.backup'
if not os.path.exists(backup_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Created backup at {backup_path}")

# Read the file
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# The field to insert
inspection_name_field = '''                            {/* Inspection Name */}
                            <div className="space-y-2 md:col-span-2">
                                <label className="block text-sm font-medium text-gray-700">
                                    Inspection Name <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="text"
                                    className="w-full bg-[#F5F9FA] border-none rounded-lg px-4 py-3 text-sm text-gray-900 focus:ring-2 focus:ring-[#1B6486] focus:outline-none"
                                    placeholder="e.g., Monthly Safety Inspection - January 2026"
                                    value={formData.inspection_name}
                                    onChange={(e) => setFormData({ ...formData, inspection_name: e.target.value })}
                                    required
                                />
                            </div>

'''

# Find and replace - insert after the grid div and before Select Vessel comment
search_text = '''                        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-8 max-w-5xl">
                            {/* Select Vessel */}'''

replace_text = '''                        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-8 max-w-5xl">
''' + inspection_name_field + '''                            {/* Select Vessel */}'''

if search_text in content:
    new_content = content.replace(search_text, replace_text, 1)  # Replace only first occurrence
    
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ Successfully added Inspection Name field!")
    print("📝 The field has been inserted as the first field in the form")
    print("🔍 Location: After the grid div, before 'Select Vessel'")
else:
    print("❌ Could not find the insertion point")
    print("🔍 Searching for alternative pattern...")
    
    # Try alternative pattern
    alt_search = '<div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-8 max-w-5xl">'
    if alt_search in content:
        print(f"✅ Found grid div")
        # Find the position
        pos = content.find(alt_search)
        # Find the next line
        next_newline = content.find('\n', pos)
        # Insert after the newline
        new_content = content[:next_newline+1] + inspection_name_field + content[next_newline+1:]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("✅ Successfully added Inspection Name field using alternative method!")
    else:
        print("❌ Could not find grid div either")
