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

def apply_pivot_table(df, row_attrs, col_attrs, all_metrics):
    """Create a pivot table with row and column grouping (like Toolio)"""
    if not row_attrs and not col_attrs:
        return df
    
    # Separate metrics from attributes in grouping
    metric_list = ['Gross Sales Units', 'Receipts Units', 'BOP Units', 'On Order Units']
    row_metrics = [m for m in row_attrs if m in metric_list]
    col_metrics = [m for m in col_attrs if m in metric_list]
    row_attributes = [a for a in row_attrs if a not in metric_list]
    col_attributes = [a for a in col_attrs if a not in metric_list]
    
    # Ensure metrics exist in dataframe
    available_metrics = [m for m in all_metrics if m in df.columns]
    if not available_metrics:
        return df
    
    # If metrics are selected for grouping, we need to unpivot/melt the data
    if row_metrics or col_metrics:
        # Unpivot metrics to make them a dimension
        id_vars = [col for col in df.columns if col not in available_metrics]
        melted_df = pd.melt(
            df,
            id_vars=id_vars,
            value_vars=available_metrics,
            var_name='Metric',
            value_name='Value'
        )
        
        # Update grouping attributes to include Metric dimension
        final_row_attrs = row_attributes.copy()
        final_col_attrs = col_attributes.copy()
        
        if row_metrics:
            # Add Metric to row attributes if metrics are grouped by rows
            if 'Metric' not in final_row_attrs:
                final_row_attrs.append('Metric')
        elif col_metrics:
            # Add Metric to column attributes if metrics are grouped by columns
            if 'Metric' not in final_col_attrs:
                final_col_attrs.append('Metric')
        else:
            # If metrics specified but not in row/col, add to rows by default
            if 'Metric' not in final_row_attrs:
                final_row_attrs.append('Metric')
        
        # Use melted dataframe and Value as the metric
        working_df = melted_df
        value_col = 'Value'
    else:
        # No metrics in grouping, use original dataframe
        working_df = df
        value_col = available_metrics[0] if len(available_metrics) == 1 else available_metrics
    
    # If only row grouping (no column grouping)
    if (row_attributes or row_metrics) and not (col_attributes or col_metrics):
        if row_metrics:
            # Group by rows including Metric
            grouped = working_df.groupby(final_row_attrs)[value_col].sum().reset_index()
        else:
            # Group by rows and sum all metrics
            grouped = working_df.groupby(row_attributes)[available_metrics].sum().reset_index()
        return grouped
    
    # If only column grouping (no row grouping)
    if (col_attributes or col_metrics) and not (row_attributes or row_metrics):
        if col_metrics:
            # Group by columns including Metric
            grouped = working_df.groupby(final_col_attrs)[value_col].sum().reset_index()
        else:
            # Group by columns and sum all metrics
            grouped = working_df.groupby(col_attributes)[available_metrics].sum().reset_index()
        return grouped
    
    # Both row and column grouping - create pivot table
    if row_metrics or col_metrics:
        # Pivot with Metric as a dimension
        try:
            pivot = pd.pivot_table(
                working_df,
                values=value_col,
                index=final_row_attrs if final_row_attrs else ['Metric'],
                columns=final_col_attrs if final_col_attrs else ['Metric'],
                aggfunc='sum',
                fill_value=0
            )
            # Flatten column names if multi-level
            if isinstance(pivot.columns, pd.MultiIndex):
                pivot.columns = [f"{'_'.join(map(str, col))}" for col in pivot.columns.values]
            return pivot
        except Exception as e:
            st.error(f"Error creating pivot table: {e}")
            return df
    else:
        # Standard pivot table with attributes only
        # For each metric, create a pivot table
        pivot_tables = []
        for metric in available_metrics:
            try:
                pivot = pd.pivot_table(
                    working_df,
                    values=metric,
                    index=row_attributes,
                    columns=col_attributes,
                    aggfunc='sum',
                    fill_value=0
                )
                # Flatten column names if multi-level
                if isinstance(pivot.columns, pd.MultiIndex):
                    pivot.columns = [f"{'_'.join(map(str, col))}" for col in pivot.columns.values]
                else:
                    # If single column, add metric name
                    if len(available_metrics) > 1:
                        pivot.columns = [f"{col}_{metric}" for col in pivot.columns]
                
                pivot_tables.append(pivot)
            except Exception as e:
                st.error(f"Error creating pivot table for {metric}: {e}")
                continue
        
        # Combine pivot tables (if multiple metrics)
        if len(pivot_tables) == 0:
            return df
        elif len(pivot_tables) == 1:
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
                
                # All options for grouping (attributes + metrics)
                all_grouping_options = available_attributes + metrics
                
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
                    options=all_grouping_options,
                    default=st.session_state.group_by_rows,
                    help="Attributes or metrics to group by rows (vertical grouping)"
                )
                st.session_state.group_by_rows = group_by_rows
                
                st.markdown("**Group by Columns** (horizontal grouping)")
                st.info("💡 Tip: Put 'Week' in columns to see time across the top (like Toolio)")
                group_by_columns = st.multiselect(
                    "Columns:",
                    options=all_grouping_options,
                    default=st.session_state.group_by_columns,
                    help="Attributes or metrics to group by columns (horizontal grouping - creates pivot table)"
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
            
            # Calculate totals from original filtered data (before pivot)
            filtered_for_totals = apply_filters(data, filters)
            
            # Display summary statistics
            col1, col2, col3, col4 = st.columns(4)
            
            # Calculate totals from original data (before grouping)
            total_gross_sales = filtered_for_totals['Gross Sales Units'].sum()
            total_receipts = filtered_for_totals['Receipts Units'].sum()
            total_bop = filtered_for_totals['BOP Units'].sum()
            total_on_order = filtered_for_totals['On Order Units'].sum()
            
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
            
            # Prepare columns to display based on selected_attributes
            if len(filtered_data) > 0:
                # If grouping is applied, show all columns
                if group_by_rows or group_by_columns:
                    display_df = filtered_data
                else:
                    # If no grouping, show selected attributes + metrics
                    display_columns = []
                    
                    # Add selected attributes
                    if selected_attributes:
                        for attr in selected_attributes:
                            if attr in filtered_data.columns:
                                display_columns.append(attr)
                    else:
                        # If no attributes selected, show all attribute columns
                        display_columns = [col for col in filtered_data.columns if col not in metrics]
                    
                    # Always add metrics
                    for metric in metrics:
                        if metric in filtered_data.columns:
                            display_columns.append(metric)
                    
                    # Filter to only existing columns
                    display_columns = [col for col in display_columns if col in filtered_data.columns]
                    
                    if display_columns:
                        display_df = filtered_data[display_columns]
                    else:
                        display_df = filtered_data
                
                st.dataframe(
                    display_df,
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
