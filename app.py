import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

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
if 'group_by_attributes' not in st.session_state:
    st.session_state.group_by_attributes = []
if 'filters' not in st.session_state:
    st.session_state.filters = {}

def generate_sample_data():
    """Generate sample merchandise plan data for 3 weeks with attributes"""
    # Generate 3 weeks of dates
    start_date = datetime.now().replace(day=1)  # Start of current month
    weeks = []
    for i in range(3):
        week_start = start_date + timedelta(weeks=i)
        weeks.append(week_start.strftime('%Y-%m-%d'))
    
    # Sample attributes
    categories = ['Tops', 'Bottoms', 'Dresses', 'Accessories']
    brands = ['Brand A', 'Brand B', 'Brand C', 'Brand D']
    colors = ['Red', 'Blue', 'Black', 'White', 'Green']
    sizes = ['XS', 'S', 'M', 'L', 'XL']
    stores = ['Store 1', 'Store 2', 'Store 3', 'Store 4']
    
    # Generate sample data
    data = []
    np.random.seed(42)  # For reproducibility
    
    for week in weeks:
        for category in categories:
            for brand in brands:
                for color in colors[:3]:  # Limit for demo
                    for size in sizes[:3]:  # Limit for demo
                        for store in stores[:2]:  # Limit for demo
                            data.append({
                                'Week': week,
                                'Category': category,
                                'Brand': brand,
                                'Color': color,
                                'Size': size,
                                'Store': store,
                                'Gross Sales Units': np.random.randint(50, 500),
                                'Receipts Units': np.random.randint(30, 400),
                                'BOP Units': np.random.randint(100, 1000),
                                'On Order Units': np.random.randint(0, 300)
                            })
    
    return pd.DataFrame(data)

def apply_filters(df, filters):
    """Apply filters to dataframe"""
    filtered_df = df.copy()
    
    for attr, value in filters.items():
        if value and len(value) > 0:
            filtered_df = filtered_df[filtered_df[attr].isin(value)]
    
    return filtered_df

def apply_group_by(df, group_by_attrs, metrics):
    """Apply group by and aggregate metrics"""
    if not group_by_attrs:
        return df
    
    # Group by selected attributes
    grouped = df.groupby(group_by_attrs)[metrics].sum().reset_index()
    
    return grouped

def main():
    st.title("📊 Toolio Lite - Merchandise Plan Demo")
    st.markdown("**Interactive demo showing how attributes, grouping, and filtering work in merchandise planning**")
    
    # Generate or load data
    if st.session_state.data is None:
        with st.spinner("Generating sample data..."):
            st.session_state.data = generate_sample_data()
            st.session_state.filtered_data = st.session_state.data.copy()
    
    data = st.session_state.data
    
    # Sidebar for controls
    with st.sidebar:
        st.header("⚙️ Controls")
        
        # Available attributes
        available_attributes = ['Category', 'Brand', 'Color', 'Size', 'Store', 'Week']
        
        st.subheader("📋 Select Attributes to Display")
        selected_attributes = st.multiselect(
            "Choose attributes to show in the table:",
            options=available_attributes,
            default=st.session_state.selected_attributes,
            help="Select which attribute columns to display in the data table"
        )
        st.session_state.selected_attributes = selected_attributes
        
        st.divider()
        
        # Group By
        st.subheader("🔀 Group By")
        group_by_options = [attr for attr in available_attributes if attr != 'Week']
        group_by_attributes = st.multiselect(
            "Group data by:",
            options=group_by_options,
            default=st.session_state.group_by_attributes,
            help="Group and aggregate data by selected attributes (similar to SQL GROUP BY)"
        )
        st.session_state.group_by_attributes = group_by_attributes
        
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
        if st.button("🔄 Reset All", type="secondary"):
            st.session_state.selected_attributes = []
            st.session_state.group_by_attributes = []
            st.session_state.filters = {}
            st.session_state.filtered_data = st.session_state.data.copy()
            st.rerun()
    
    # Main content area
    # Metrics selection
    metrics = ['Gross Sales Units', 'Receipts Units', 'BOP Units', 'On Order Units']
    
    # Apply filters
    filtered_data = apply_filters(data, filters)
    
    # Apply group by
    if group_by_attributes:
        # Include Week in group by if not already there and if Week is in filters
        group_by_cols = group_by_attributes.copy()
        if 'Week' in filters and 'Week' not in group_by_cols:
            group_by_cols.append('Week')
        
        filtered_data = apply_group_by(filtered_data, group_by_cols, metrics)
    else:
        # If no group by, still filter by week if specified
        if 'Week' in filters:
            filtered_data = filtered_data[filtered_data['Week'].isin(filters['Week'])]
    
    st.session_state.filtered_data = filtered_data
    
    # Display summary statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Gross Sales Units", f"{filtered_data['Gross Sales Units'].sum():,.0f}")
    with col2:
        st.metric("Receipts Units", f"{filtered_data['Receipts Units'].sum():,.0f}")
    with col3:
        st.metric("BOP Units", f"{filtered_data['BOP Units'].sum():,.0f}")
    with col4:
        st.metric("On Order Units", f"{filtered_data['On Order Units'].sum():,.0f}")
    
    st.divider()
    
    # Display data table
    st.subheader("📈 Data Table")
    
    # Prepare columns to display
    display_columns = []
    
    # Add group by attributes first (if any)
    if group_by_attributes:
        display_columns.extend(group_by_attributes)
        # Add Week if it's in the data but not in group by
        if 'Week' in filtered_data.columns and 'Week' not in group_by_attributes:
            if not filters.get('Week') or len(filters.get('Week', [])) > 1:
                display_columns.append('Week')
    
    # Add selected attributes (if not already in display columns)
    for attr in selected_attributes:
        if attr in filtered_data.columns and attr not in display_columns:
            display_columns.append(attr)
    
    # If no specific attributes selected, show group by or all attributes
    if not display_columns:
        if group_by_attributes:
            display_columns = group_by_attributes.copy()
            if 'Week' in filtered_data.columns:
                display_columns.append('Week')
        else:
            # Show all attribute columns except metrics
            display_columns = [col for col in filtered_data.columns if col not in metrics]
    
    # Always add metrics
    display_columns.extend(metrics)
    
    # Filter to only show columns that exist in the dataframe
    display_columns = [col for col in display_columns if col in filtered_data.columns]
    
    # Display the table
    if len(filtered_data) > 0:
        st.dataframe(
            filtered_data[display_columns],
            use_container_width=True,
            hide_index=True,
            height=400
        )
        
        st.caption(f"Showing {len(filtered_data):,} rows")
    else:
        st.warning("No data matches the current filters. Please adjust your filters.")
    
    # Instructions section
    with st.expander("ℹ️ How to Use This Demo"):
        st.markdown("""
        ### This demo shows how Toolio Lite handles merchandise planning:
        
        1. **Attributes**: Select which attribute columns to display in the table
           - Attributes are dimensions like Category, Brand, Color, Size, Store, Week
           - They help you organize and view your merchandise data
        
        2. **Group By**: Aggregate data by selected attributes
           - Similar to SQL GROUP BY functionality
           - Metrics (units) will be summed for each group
           - Useful for high-level analysis
        
        3. **Filters**: Narrow down the data view
           - Select specific values for any attribute
           - Multiple selections create OR conditions (e.g., Category = "Tops" OR "Bottoms")
           - Filters work together with AND logic
        
        4. **Metrics**: The four key metrics displayed are:
           - **Gross Sales Units**: Units sold
           - **Receipts Units**: Units received
           - **BOP Units**: Beginning of period inventory
           - **On Order Units**: Units currently on order
        
        ### Try this workflow:
        1. Select "Category" and "Brand" in Group By
        2. Filter by Week to show only one week
        3. Add "Color" as a filter to see specific colors
        4. Notice how the metrics aggregate at the group level
        """)

if __name__ == "__main__":
    main()

