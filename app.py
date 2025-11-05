import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from itertools import product

# Page configuration
st.set_page_config(
    page_title="Toolio Lite - Merchandise Plan Demo",
    page_icon="📊",
    layout="wide"
)

# Initialize session state
if 'data' not in st.session_state:
    st.session_state.data = None
if 'filtered_data' not in st.session_state:
    st.session_state.filtered_data = None
if 'selected_attributes' not in st.session_state:
    st.session_state.selected_attributes = []
if 'group_by_rows' not in st.session_state:
    st.session_state.group_by_rows = []
if 'group_by_columns' not in st.session_state:
    st.session_state.group_by_columns = []
if 'filters' not in st.session_state:
    st.session_state.filters = {}
if 'locations' not in st.session_state:
    st.session_state.locations = []
if 'data_regenerated' not in st.session_state:
    st.session_state.data_regenerated = False

def generate_sample_data(locations):
    """Generate sample merchandise plan data for 3 weeks with location and attribute hierarchy"""
    # Generate 3 weeks of dates
    start_date = datetime.now().replace(day=1)  # Start of current month
    weeks = []
    for i in range(3):
        week_start = start_date + timedelta(weeks=i)
        weeks.append(week_start.strftime('%Y-%m-%d'))
    
    # Attribute hierarchy
    divisions = ['Mens', 'Womens']
    departments = ['Bottoms', 'Tops']
    classes = {
        'Tops': ['Long Sleeve', 'Short Sleeve'],
        'Bottoms': ['Short Leg', 'Long Leg']
    }
    
    # Generate sample data
    data = []
    np.random.seed(42)  # For reproducibility
    
    for week in weeks:
        for location in locations:
            loc_name = location['name']
            is_source = location.get('source_location', False)
            is_inventory = location.get('inventory_location', False)
            is_selling = location.get('selling_location', False)
            
            for division in divisions:
                for department in departments:
                    # Get appropriate classes for this department
                    class_list = classes.get(department, [])
                    
                    for class_item in class_list:
                        row = {
                            'Week': week,
                            'Location': loc_name,
                            'Channel': location.get('channel', ''),
                            'Channel Group': location.get('channel_group', ''),
                            'Division': division,
                            'Department': department,
                            'Class': class_item
                        }
                        
                        # Determine metrics based on location type
                        if is_source:
                            # Source location: Has BOP, Receipts, On Order, NO Sales
                            row['BOP Units'] = np.random.randint(100, 1000)
                            row['Receipts Units'] = np.random.randint(30, 400)
                            row['On Order Units'] = np.random.randint(0, 300)
                            row['Gross Sales Units'] = 0
                        elif is_inventory:
                            # Inventory location: Has BOP and Sales, NO Receipts or On Order
                            row['BOP Units'] = np.random.randint(100, 1000)
                            row['Gross Sales Units'] = np.random.randint(50, 500)
                            row['Receipts Units'] = 0
                            row['On Order Units'] = 0
                        elif is_selling:
                            # Selling location (only selling is true): Just Sales
                            row['Gross Sales Units'] = np.random.randint(50, 500)
                            row['BOP Units'] = 0
                            row['Receipts Units'] = 0
                            row['On Order Units'] = 0
                        else:
                            # Default: All metrics
                            row['Gross Sales Units'] = np.random.randint(50, 500)
                            row['Receipts Units'] = np.random.randint(30, 400)
                            row['BOP Units'] = np.random.randint(100, 1000)
                            row['On Order Units'] = np.random.randint(0, 300)
                        
                        data.append(row)
    
    return pd.DataFrame(data)

def apply_filters(df, filters):
    """Apply filters to dataframe"""
    filtered_df = df.copy()
    
    for attr, value in filters.items():
        if value and len(value) > 0:
            filtered_df = filtered_df[filtered_df[attr].isin(value)]
    
    return filtered_df

def apply_pivot_table(df, row_attrs, col_attrs, metrics):
    """Create a pivot table with row and column grouping (like Toolio)"""
    if not row_attrs and not col_attrs:
        return df
    
    # If only row grouping (no column grouping)
    if row_attrs and not col_attrs:
        grouped = df.groupby(row_attrs)[metrics].sum().reset_index()
        return grouped
    
    # If only column grouping (no row grouping)
    if col_attrs and not row_attrs:
        # Group by columns
        grouped = df.groupby(col_attrs)[metrics].sum().reset_index()
        return grouped
    
    # Both row and column grouping - create pivot table
    # For each metric, create a pivot table
    pivot_tables = []
    for metric in metrics:
        pivot = pd.pivot_table(
            df,
            values=metric,
            index=row_attrs,
            columns=col_attrs,
            aggfunc='sum',
            fill_value=0
        )
        # Flatten column names if multi-level
        if isinstance(pivot.columns, pd.MultiIndex):
            pivot.columns = ['_'.join(map(str, col)).strip() for col in pivot.columns.values]
        else:
            pivot.columns = [f"{col}_{metric}" if col != metric else metric for col in pivot.columns]
        
        # Add metric name as suffix if multiple metrics
        if len(metrics) > 1:
            pivot.columns = [f"{col}_{metric}" if not str(col).endswith(metric) else str(col) for col in pivot.columns]
        
        pivot_tables.append(pivot)
    
    # Combine pivot tables (if multiple metrics)
    if len(pivot_tables) == 1:
        return pivot_tables[0]
    else:
        # For multiple metrics, concatenate side by side
        result = pivot_tables[0]
        for pt in pivot_tables[1:]:
            # Align by index
            result = pd.concat([result, pt], axis=1)
        return result

def main():
    st.title("📊 Toolio Lite - Merchandise Plan Demo")
    st.markdown("**Interactive demo showing how attributes, grouping, and filtering work in merchandise planning**")
    
    # Configuration tab
    config_tab, view_tab = st.tabs(["⚙️ Configuration", "📊 Data View"])
    
    with config_tab:
        st.header("Location Configuration")
        st.markdown("**Configure up to 10 locations with their properties**")
        
        # Location management
        if 'locations' not in st.session_state or len(st.session_state.locations) == 0:
            st.session_state.locations = [{} for _ in range(min(10, 5))]  # Start with 5
        
        # Add/Remove location buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ Add Location", disabled=len(st.session_state.locations) >= 10):
                if len(st.session_state.locations) < 10:
                    st.session_state.locations.append({})
                    st.rerun()
        with col2:
            if st.button("➖ Remove Last Location", disabled=len(st.session_state.locations) <= 1):
                if len(st.session_state.locations) > 1:
                    st.session_state.locations.pop()
                    st.rerun()
        
        st.divider()
        
        # Location inputs
        for i, location in enumerate(st.session_state.locations):
            with st.expander(f"📍 Location {i+1}", expanded=i < 3):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    location_name = st.text_input(
                        "Location Name:",
                        value=location.get('name', ''),
                        key=f"loc_name_{i}",
                        placeholder="e.g., Store 1, Warehouse A"
                    )
                    location['name'] = location_name
                
                with col2:
                    channel = st.text_input(
                        "Channel:",
                        value=location.get('channel', ''),
                        key=f"loc_channel_{i}",
                        placeholder="e.g., Retail, Online"
                    )
                    location['channel'] = channel
                
                with col3:
                    channel_group = st.text_input(
                        "Channel Group:",
                        value=location.get('channel_group', ''),
                        key=f"loc_channel_group_{i}",
                        placeholder="e.g., E-commerce, Brick & Mortar"
                    )
                    location['channel_group'] = channel_group
                
                st.markdown("**Location Type:**")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    source_location = st.checkbox(
                        "Source Location",
                        value=location.get('source_location', False),
                        key=f"loc_source_{i}",
                        help="Holds inventory - receives, has on order and BOP, NO sales"
                    )
                    location['source_location'] = source_location
                
                with col2:
                    inventory_location = st.checkbox(
                        "Inventory Location",
                        value=location.get('inventory_location', False),
                        key=f"loc_inventory_{i}",
                        help="Holds inventory and sells - has sales and BOP, nothing else"
                    )
                    location['inventory_location'] = inventory_location
                
                with col3:
                    selling_location = st.checkbox(
                        "Selling Location",
                        value=location.get('selling_location', False),
                        key=f"loc_selling_{i}",
                        help="If only this is true, location just has sales"
                    )
                    location['selling_location'] = selling_location
                
                if not source_location and not inventory_location and not selling_location:
                    st.info("⚠️ No location type selected - will default to all metrics")
        
        st.divider()
        
        # Attributes section (fixed hierarchy)
        st.header("Product Attributes")
        st.info("""
        **Fixed Attribute Hierarchy:**
        - **Division**: Mens, Womens
        - **Department**: Bottoms, Tops
        - **Class**: 
          - For Tops: Long Sleeve, Short Sleeve
          - For Bottoms: Short Leg, Long Leg
        """)
        
        st.divider()
        
        # Generate data button
        if st.button("🔄 Generate Data", type="primary", use_container_width=True):
            # Validate locations
            valid_locations = [loc for loc in st.session_state.locations if loc.get('name', '').strip()]
            if len(valid_locations) == 0:
                st.error("⚠️ Please add at least one location with a name before generating data.")
            else:
                with st.spinner("Generating data..."):
                    st.session_state.locations = valid_locations
                    st.session_state.data = generate_sample_data(valid_locations)
                    st.session_state.filtered_data = st.session_state.data.copy()
                    st.session_state.data_regenerated = True
                    st.success(f"✓ Data generated successfully for {len(valid_locations)} location(s)!")
                    st.rerun()
        
        # Show data preview
        if st.session_state.data is not None:
            st.subheader("📊 Data Preview")
            st.info(f"Total rows: {len(st.session_state.data):,} | Columns: {', '.join(st.session_state.data.columns.tolist())}")
            st.dataframe(st.session_state.data.head(10), use_container_width=True, hide_index=True)
    
    with view_tab:
        # Generate or load data
        if st.session_state.data is None:
            st.warning("⚠️ Please configure locations in the Configuration tab and generate data first.")
            st.info("💡 Click on the '⚙️ Configuration' tab above to set up your locations.")
        else:
            data = st.session_state.data
            
            # Sidebar for controls
            with st.sidebar:
                st.header("⚙️ Controls")
                
                # Get available attributes from data
                metrics = ['Gross Sales Units', 'Receipts Units', 'BOP Units', 'On Order Units']
                available_attributes = [col for col in data.columns if col not in metrics]
                
                st.subheader("📋 Select Attributes to Display")
                selected_attributes = st.multiselect(
                    "Choose attributes to show in the table:",
                    options=available_attributes,
                    default=st.session_state.selected_attributes,
                    help="Select which attribute columns to display in the data table"
                )
                st.session_state.selected_attributes = selected_attributes
                
                st.divider()
                
                # Group By - Rows and Columns (like Toolio)
                st.subheader("🔀 Group By (Rows & Columns)")
                st.markdown("**Group by Rows** (vertical grouping)")
                group_by_rows = st.multiselect(
                    "Rows:",
                    options=available_attributes,
                    default=st.session_state.group_by_rows,
                    help="Attributes to group by rows (vertical grouping)"
                )
                st.session_state.group_by_rows = group_by_rows
                
                st.markdown("**Group by Columns** (horizontal grouping)")
                st.info("💡 Tip: Put 'Week' in columns to see time across the top (like Toolio)")
                group_by_columns = st.multiselect(
                    "Columns:",
                    options=available_attributes,
                    default=st.session_state.group_by_columns,
                    help="Attributes to group by columns (horizontal grouping - creates pivot table)"
                )
                st.session_state.group_by_columns = group_by_columns
                
                st.divider()
                
                # Filters
                st.subheader("🔍 Filters")
                st.info("Apply filters to narrow down the data view")
                
                filters = {}
                for attr in available_attributes:
                    if attr != 'Week':  # Week filter handled separately
                        unique_values = sorted(data[attr].unique().tolist())
                        selected_values = st.multiselect(
                            f"Filter by {attr}:",
                            options=unique_values,
                            default=st.session_state.filters.get(attr, []),
                            help=f"Filter data by {attr}"
                        )
                        if selected_values:
                            filters[attr] = selected_values
                
                # Week filter (special handling)
                unique_weeks = sorted(data['Week'].unique().tolist())
                selected_weeks = st.multiselect(
                    "Filter by Week:",
                    options=unique_weeks,
                    default=st.session_state.filters.get('Week', unique_weeks),
                    help="Select which weeks to display"
                )
                if selected_weeks:
                    filters['Week'] = selected_weeks
                
                st.session_state.filters = filters
                
                st.divider()
                
                # Reset button
                if st.button("🔄 Reset Filters", type="secondary"):
                    st.session_state.selected_attributes = []
                    st.session_state.group_by_rows = []
                    st.session_state.group_by_columns = []
                    st.session_state.filters = {}
                    st.session_state.filtered_data = st.session_state.data.copy()
                    st.rerun()
            
            # Main content area
            # Apply filters
            filtered_data = apply_filters(data, filters)
            
            # Apply row and column grouping (pivot table)
            if group_by_rows or group_by_columns:
                filtered_data = apply_pivot_table(filtered_data, group_by_rows, group_by_columns, metrics)
            else:
                # If no group by, still filter by week if specified
                if 'Week' in filters:
                    filtered_data = filtered_data[filtered_data['Week'].isin(filters['Week'])]
            
            st.session_state.filtered_data = filtered_data
            
            # Display summary statistics
            col1, col2, col3, col4 = st.columns(4)
            
            # Calculate totals (handle pivot table format)
            if isinstance(filtered_data.index, pd.MultiIndex) or (isinstance(filtered_data.columns, pd.Index) and any('_' in str(col) for col in filtered_data.columns)):
                # Pivot table - sum all numeric values
                numeric_data = filtered_data.select_dtypes(include=[np.number])
                total_gross_sales = numeric_data.sum().sum() if len(numeric_data.columns) > 0 else 0
                total_receipts = total_gross_sales
                total_bop = total_gross_sales
                total_on_order = total_gross_sales
            else:
                # Regular dataframe
                if 'Gross Sales Units' in filtered_data.columns:
                    total_gross_sales = filtered_data['Gross Sales Units'].sum()
                    total_receipts = filtered_data['Receipts Units'].sum()
                    total_bop = filtered_data['BOP Units'].sum()
                    total_on_order = filtered_data['On Order Units'].sum()
                else:
                    # Pivot table format - try to sum numeric columns
                    numeric_cols = filtered_data.select_dtypes(include=[np.number])
                    total_gross_sales = numeric_cols.sum().sum() if len(numeric_cols.columns) > 0 else 0
                    total_receipts = total_gross_sales
                    total_bop = total_gross_sales
                    total_on_order = total_gross_sales
            
            with col1:
                st.metric("Gross Sales Units", f"{total_gross_sales:,.0f}")
            with col2:
                st.metric("Receipts Units", f"{total_receipts:,.0f}")
            with col3:
                st.metric("BOP Units", f"{total_bop:,.0f}")
            with col4:
                st.metric("On Order Units", f"{total_on_order:,.0f}")
            
            st.divider()
            
            # Display data table
            st.subheader("📈 Data Table")
            
            # Display the table
            if len(filtered_data) > 0:
                st.dataframe(
                    filtered_data,
                    use_container_width=True,
                    hide_index=False,
                    height=500
                )
                
                if isinstance(filtered_data, pd.DataFrame):
                    st.caption(f"Showing {len(filtered_data):,} rows")
                else:
                    st.caption("Pivot table view")
            else:
                st.warning("No data matches the current filters. Please adjust your filters.")
            
            # Instructions section
            with st.expander("ℹ️ How to Use This Demo"):
                st.markdown("""
                ### Configuration Tab:
                1. **Locations**: Add up to 10 locations with:
                   - Location Name, Channel, Channel Group
                   - Location Type (Source, Inventory, or Selling)
                   - Each type determines which metrics are available
                2. **Attributes**: Fixed hierarchy:
                   - Division (Mens, Womens)
                   - Department (Bottoms, Tops)
                   - Class (Long/Short Sleeve for Tops, Long/Short Leg for Bottoms)
                3. **Generate Data**: Click to create sample data
                
                ### Data View Tab:
                1. **Group By Rows**: Select attributes to group vertically
                2. **Group By Columns**: Select attributes to group horizontally (creates pivot table)
                   - Tip: Put 'Week' in columns to see time across the top (like Toolio)
                3. **Filters**: Narrow down data by selecting specific attribute values
                4. **Metrics**: The four key metrics:
                   - **Gross Sales Units**: Units sold
                   - **Receipts Units**: Units received
                   - **BOP Units**: Beginning of period inventory
                   - **On Order Units**: Units currently on order
                
                ### Example Workflow:
                1. Configure 3-5 locations with different types
                2. Generate data
                3. Group by Rows: Division, Department, Class
                4. Group by Columns: Week (to see time across)
                5. Filter by Location to see specific stores
                """)

if __name__ == "__main__":
    main()
