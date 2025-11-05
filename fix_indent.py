#!/usr/bin/env python3
# Fix indentation in app.py

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix lines 444-447 (0-indexed: 443-446)
lines[443] = '                    st.session_state.filtered_data = st.session_state.data.copy()\n'
lines[444] = '                    st.session_state.data_regenerated = True\n'
lines[445] = '                    st.success(f"✓ Data generated successfully for {len(valid_locations)} location(s)!")\n'
lines[446] = '                    st.rerun()\n'

with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Fixed indentation!")

