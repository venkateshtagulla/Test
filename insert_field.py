#!/usr/bin/env python3
"""Insert Inspection Name field into the inspection creation form."""

file_path = r'e:\KHM_Engineers\Software Projects\ARKA\Code\Web\frontend-development\src\app\inspection\create\page.tsx'

# Read the file
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# The inspection name field to insert
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

# Insert after line 162 (the grid div) and before line 163 (Select Vessel comment)
# Line 162 is index 161 (0-indexed)
insert_position = 162  # Insert before line 163

# Split into lines
field_lines = inspection_name_field.split('\n')

# Insert the new lines
for i, line in enumerate(field_lines):
    lines.insert(insert_position + i, line + '\n' if line else '\n')

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"✅ Successfully inserted Inspection Name field at line {insert_position}")
print(f"📝 Total lines in file: {len(lines)}")
