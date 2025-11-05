#!/usr/bin/env python3
# Fix all indentation issues in app.py

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix line 444 (0-indexed: 443) - should be inside spinner block
lines[443] = '                    st.session_state.filtered_data = st.session_state.data.copy()\n'

# Fix line 445 (0-indexed: 444) - should be inside spinner block
lines[444] = '                    st.session_state.data_regenerated = True\n'

# Fix line 446 (0-indexed: 445) - should be inside spinner block
lines[445] = '                    st.success(f"✓ Data generated successfully for {len(valid_locations)} location(s)!")\n'

# Fix line 447 (0-indexed: 446) - should be inside spinner block
lines[446] = '                    st.rerun()\n'

# Fix line 567 (0-indexed: 566) - should be inside else block
lines[566] = '            else:\n'

# Fix lines 568-570 (0-indexed: 567-569) - should be inside else block
lines[567] = '                # If no group by, still filter by week if specified\n'
lines[568] = '                if \'Week\' in filters:\n'
lines[569] = '                    filtered_data = filtered_data[filtered_data[\'Week\'].isin(filters[\'Week\'])]\n'

# Fix line 702 (0-indexed: 701) - closing parenthesis should be indented
if lines[701].strip() == ')':
    lines[701] = '                )\n'

# Fix lines 704-707 (0-indexed: 703-706) - should be inside if block
lines[703] = '                if isinstance(filtered_data, pd.DataFrame):\n'
lines[704] = '                    st.caption(f"Showing {len(filtered_data):,} rows")\n'
lines[705] = '                else:\n'
lines[706] = '                    st.caption("Pivot table view")\n'

# Fix line 708 (0-indexed: 707) - should be inside else block
lines[707] = '            else:\n'

# Fix line 709 (0-indexed: 708) - should be inside else block
lines[708] = '                st.warning("No data matches the current filters. Please adjust your filters.")\n'

# Fix lines 711-712 (0-indexed: 710-711) - should be inside else block
if lines[710].strip().startswith('# Instructions'):
    lines[710] = '            # Instructions section\n'
if lines[711].strip().startswith('with st.expander'):
    lines[711] = '            with st.expander("ℹ️ How to Use This Demo"):\n'

with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Fixed all indentation issues!")

