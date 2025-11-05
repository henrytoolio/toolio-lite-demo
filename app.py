import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Toolio Lite Demo App (Full Restored UI + Expandable Metrics)

st.set_page_config(page_title="Toolio Lite - Merchandise Plan Demo", page_icon="📊", layout="wide")

# Initialize session state
for key, default in [
    ("data", None),
    ("filtered_data", None),
    ("selected_attributes", []),
    ("group_by_rows", []),
    ("group_by_columns", []),
    ("filters", {}),
    ("locations", []),
    ("data_regenerated", False),
    ("expanded_groups", set()),
    ("sort_columns_alphabetically", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# Generate sample data
def generate_sample_data(locations):
    np.random.seed(42)
    start_date = datetime.now().replace(day=1)
    weeks = [(start_date + timedelta(weeks=i)).strftime('%Y-%m-%d') for i in range(3)]
    divisions = ['Mens', 'Womens']
    departments = ['Bottoms', 'Tops']
    classes = {
        'Tops': ['Long Sleeve', 'Short Sleeve'],
        'Bottoms': ['Short Leg', 'Long Leg']
    }
    data = []
    for week in weeks:
        for loc in locations:
            name = loc['name']
            for div in divisions:
                for dept in departments:
                    for cls in classes[dept]:
                        data.append({
                            'Week': week,
                            'Location': name,
                            'Channel': loc.get('channel', ''),
                            'Channel Group': loc.get('channel_group', ''),
                            'Selling Channel': loc.get('selling_channel', ''),
                            'Division': div,
                            'Department': dept,
                            'Class': cls,
                            'Gross Sales Units': np.random.randint(50, 500),
                            'Receipts Units': np.random.randint(30, 400),
                            'BOP Units': np.random.randint(100, 1000),
                            'On Order Units': np.random.randint(0, 300)
                        })
    return pd.DataFrame(data)

# Utility functions
def apply_filters(df, filters):
    filtered = df.copy()
    for attr, vals in filters.items():
        if vals:
            filtered = filtered[filtered[attr].isin(vals)]
    return filtered

def get_group_key(group_values):
    if isinstance(group_values, tuple):
        return '|'.join(map(str, group_values))
    return str(group_values)

def render_expandable_table(df, row_attrs, expanded_groups, metrics):
    if not row_attrs or df.empty:
        return df
    has_metrics = 'Metric' in row_attrs or 'Metrics' in row_attrs
    grouped = df.groupby(row_attrs)
    rows = []
    for group_key, group_df in grouped:
        gid = get_group_key(group_key)
        is_metric_group = has_metrics and ('Metric' in str(group_key) or 'Metrics' in str(group_key))
        is_expanded = True if is_metric_group else gid in expanded_groups
        header = {}
        if isinstance(group_key, tuple):
            for i, attr in enumerate(row_attrs):
                header[attr] = group_key[i]
        else:
            header[row_attrs[0]] = group_key
        header['_expand_indicator'] = '' if is_metric_group else ('▼' if is_expanded else '▶')
        for metric in metrics:
            header[metric] = group_df[metric].sum()
        rows.append(pd.DataFrame([header]))
        if is_expanded or is_metric_group:
            detail = group_df.copy()
            if row_attrs:
                first_attr = row_attrs[0]
                if first_attr in detail.columns:
                    detail[first_attr] = '  ' + detail[first_attr].astype(str)
            detail['_expand_indicator'] = ''
            rows.append(detail)
    return pd.concat(rows, ignore_index=True)

# Main function
def main():
    st.title('📊 Toolio Lite - Merchandise Plan Demo')
    st.markdown('**Interactive demo showing grouping, filtering, and expandable pivot-style tables (Metrics always expanded)**')
    config_tab, view_tab = st.tabs(['⚙️ Configuration', '📊 Data View'])

    with config_tab:
        st.header('Location Configuration')
        st.markdown('**Configure up to 10 locations with their properties**')
        if not st.session_state.locations:
            st.session_state.locations = [{} for _ in range(3)]
        for i, loc in enumerate(st.session_state.locations):
            with st.expander(f'📍 Location {i+1}', expanded=i<2):
                c1, c2, c3 = st.columns(3)
                loc['name'] = c1.text_input('Location Name', loc.get('name',''), key=f'name_{i}')
                loc['channel'] = c2.text_input('Channel', loc.get('channel',''), key=f'ch_{i}')
                loc['channel_group'] = c3.text_input('Channel Group', loc.get('channel_group',''), key=f'cg_{i}')
                loc['selling_channel'] = st.text_input('Selling Channel', loc.get('selling_channel',''), key=f'sellch_{i}')
        st.divider()
        st.header('Product Attributes')
        st.info('''**Fixed Attribute Hierarchy:**\n- **Division**: Mens, Womens\n- **Department**: Bottoms, Tops\n- **Class**:\n  - For Tops: Long Sleeve, Short Sleeve\n  - For Bottoms: Short Leg, Long Leg''')
        st.divider()
        if st.button('🔄 Generate Data', type='primary'):
            valids = [l for l in st.session_state.locations if l.get('name')]
            if not valids:
                st.error('Add at least one named location.')
            else:
                st.session_state.data = generate_sample_data(valids)
                st.session_state.filtered_data = st.session_state.data.copy()
                st.success('Data generated successfully!')
                st.rerun()
        if st.session_state.data is not None:
            st.subheader('📊 Data Preview')
            st.info(f'Total rows: {len(st.session_state.data):,} | Columns: {", ".join(st.session_state.data.columns)}')
            st.dataframe(st.session_state.data.head(10), use_container_width=True)

    with view_tab:
        if st.session_state.data is None:
            st.warning('Generate data first!')
            return
        data = st.session_state.data
        metrics = ['Gross Sales Units','Receipts Units','BOP Units','On Order Units']
        attributes = [c for c in data.columns if c not in metrics]

        with st.sidebar:
            st.header('⚙️ Controls')
            group_by_rows = st.multiselect('Group by Rows', attributes, default=['Channel','Division'])
            st.session_state.group_by_rows = group_by_rows
            filters = {}
            for attr in attributes:
                vals = st.multiselect(f'Filter {attr}', sorted(data[attr].unique()), default=[])
                if vals:
                    filters[attr] = vals
            st.session_state.filters = filters
            st.divider()
            if st.button('Reset Filters'):
                st.session_state.filters = {}
                st.rerun()

        filtered = apply_filters(data, st.session_state.filters)
        st.session_state.filtered_data = filtered
        total_sales = filtered['Gross Sales Units'].sum()
        total_receipts = filtered['Receipts Units'].sum()
        total_bop = filtered['BOP Units'].sum()
        total_order = filtered['On Order Units'].sum()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric('Gross Sales Units', f'{total_sales:,.0f}')
        c2.metric('Receipts Units', f'{total_receipts:,.0f}')
        c3.metric('BOP Units', f'{total_bop:,.0f}')
        c4.metric('On Order Units', f'{total_order:,.0f}')

        st.subheader('🔽 Expand/Collapse Groups')
        if group_by_rows:
            grouped = filtered.groupby(group_by_rows)
            cols = st.columns(min(4,len(grouped)))
            i = 0
            for key, _ in grouped:
                gid = get_group_key(key)
                exp = gid in st.session_state.expanded_groups
                label = ' | '.join(map(str,key)) if isinstance(key,tuple) else str(key)
                with cols[i%len(cols)]:
                    if st.button(f"{'▼' if exp else '▶'} {label[:25]}", key=f'exp_{gid}'):
                        if exp: st.session_state.expanded_groups.discard(gid)
                        else: st.session_state.expanded_groups.add(gid)
                        st.rerun()
                i+=1

        st.divider()
        st.subheader('📈 Expandable Grouped Table')
        display = render_expandable_table(filtered, group_by_rows, st.session_state.expanded_groups, metrics)
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.caption('💡 Metrics are always expanded, even when parent groups are collapsed.')

        st.divider()
        with st.expander('ℹ️ How to Use This Demo'):
            st.markdown('''### Configuration Tab:\n1. **Locations**: Add up to 10 locations with:\n   - Location Name, Channel, Channel Group\n   - Location Type (Source, Inventory, or Selling)\n   - Each type determines which metrics are available\n2. **Attributes**: Fixed hierarchy:\n   - Division (Mens, Womens)\n   - Department (Bottoms, Tops)\n   - Class (Long/Short Sleeve for Tops, Long/Short Leg for Bottoms)\n3. **Generate Data**: Click to create sample data\n\n### Data View Tab:\n1. **Group By Rows**: Select attributes to group vertically\n2. **Filters**: Narrow down data by selecting specific attribute values\n3. **Metrics**: The four key metrics:\n   - **Gross Sales Units**: Units sold\n   - **Receipts Units**: Units received\n   - **BOP Units**: Beginning of period inventory\n   - **On Order Units**: Units currently on order\n\n### Example Workflow:\n1. Configure 3–5 locations with different types\n2. Generate data\n3. Group by Rows: Division, Department, Class\n4. Filter by Location to see specific stores''')

if __name__ == '__main__':
    main()
