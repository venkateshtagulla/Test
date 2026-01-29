import re

# Read the file
with open(r'e:\KHM_Engineers\Software Projects\ARKA\Code\Web\frontend-development\src\app\inspection\create\page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Define the inspection name field HTML
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

# Find the position right after the grid opening and before "Select Vessel"
pattern = r'(<div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-8 max-w-5xl">\r?\n\s*{/\* Select Vessel \*/})'
replacement = r'<div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-8 max-w-5xl">\n' + inspection_name_field + r'                            {/* Select Vessel */}'

# Replace
new_content = re.sub(pattern, replacement, content)

# Write back
with open(r'e:\KHM_Engineers\Software Projects\ARKA\Code\Web\frontend-development\src\app\inspection\create\page.tsx', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Successfully added Inspection Name field!")
