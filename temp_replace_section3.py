#!/usr/bin/env python3
"""Script to replace section 3 in lorax_CORRECTED.md"""

file_path = r"c:\Users\lukasz.krysik\Desktop\FXcrypto\FX_code_AI_v2\docs\database\lorax_CORRECTED.md"

# Read the file
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find section 3 start (line 597, 0-indexed = 596)
# Find section 4 start (line 1591, 0-indexed = 1590)
section3_start = None
section4_start = None

for i, line in enumerate(lines):
    if line.strip() == "## 3. SQL Query Guide with User Prompts":
        section3_start = i
    elif line.strip() == "## 4. Table Joining Guidelines":
        section4_start = i
        break

print(f"Section 3 starts at line {section3_start + 1}")
print(f"Section 4 starts at line {section4_start + 1}")

# New section 3 content
new_section3 = """## 3. SQL Query Examples

For ready-to-use SQL queries with examples, see **[LORAX_EXAMPLE_QUERIES.md](LORAX_EXAMPLE_QUERIES.md)**

This separate document contains 20 validated queries covering:
- Packaging waste queries
- Shipment & sales queries
- BOM (Bill of Materials) queries
- Exception queries
- EPR reporting queries
- Sustainability & reporting queries

---

"""

# Build new file content
new_content = []

# Keep everything before section 3
new_content.extend(lines[:section3_start])

# Add new section 3
new_content.append(new_section3)

# Add everything from section 4 onwards
new_content.extend(lines[section4_start:])

# Now renumber sections 4-9 to 3-8
final_content = []
for line in new_content:
    # Replace section headers
    if line.strip() == "## 4. Table Joining Guidelines":
        final_content.append("## 3. Table Joining Guidelines\n")
    elif line.strip() == "## 5. Filters and Parameterization":
        final_content.append("## 4. Filters and Parameterization\n")
    elif line.strip() == "## 6. Advanced Business Queries":
        # Skip this section header - we'll remove it entirely
        continue
    elif line.strip() == "## 7. AI Agent Guide":
        final_content.append("## 5. AI Agent Guide\n")
    elif line.strip() == "## 8. Terminology Glossary":
        final_content.append("## 6. Terminology Glossary\n")
    elif line.strip() == "## 9. Common Errors and Solutions":
        final_content.append("## 7. Common Errors and Solutions\n")
    elif line.strip() == "## 10. Appendix: Complete Schema Reference":
        final_content.append("## 8. Appendix: Complete Schema Reference\n")
    else:
        final_content.append(line)

# Write the modified content
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(final_content)

print(f"\nFile updated successfully!")
print(f"Lines removed: {section4_start - section3_start}")
print(f"New section 3 length: {len(new_section3)} characters")
