#!/usr/bin/env python3
# Fix all indentation issues in app.py

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix line 461 (0-indexed: 460) - should be indented inside else block
lines[460] = '            data = st.session_state.data\n'

# Fix lines 463-558 (0-indexed: 462-557) - should all be indented inside else block
# These lines need to be indented by 4 more spaces (12 spaces total instead of 8)
for i in range(462, 558):
    if i < len(lines):
        line = lines[i]
        # Only fix if line has content (not empty)
        if line.strip():
            # If line starts with 4 spaces (outside else), add 4 more
            if line.startswith('    ') and not line.startswith('            '):
                lines[i] = '    ' + line

with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Fixed indentation!")

