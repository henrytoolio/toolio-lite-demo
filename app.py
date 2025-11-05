import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Toolio Lite Demo App

# Page configuration
st.set_page_config(
    page_title="Toolio Lite - Merchandise Plan Demo",
    page_icon="📊",
    layout="wide",
)

# -----------------------------
# Session State Initialization
# -----------------------------
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


# -----------------------------
# Data Generation
# -----------------------------

def generate_sample_data(locations):
    """Generate sample merchandise plan data for 3 weeks with location and attribute hierarchy"""
    # Generate 3 weeks of dates
    start_date = datetime.now().replace(day=1)  # Start of current month
    weeks = [(start_date + timedelta(weeks=i)).strftime("%Y-%m-%d") for i in range(3)]

    # Attribute hierarchy
    divisions = ["Mens", "Womens"]
    departments = ["Bottoms", "Tops"]
    classes = {
        "Tops": ["Long Sleeve", "Short Sleeve"],
        "Bottoms": ["Short Leg", "Long Leg"],
    }

    # Generate sample data
    data = []
    np.random.seed(42)  # For reproducibility

    for week in weeks:
        for location in locations:
            loc_name = location["name"]
            is_source = location.get("source_location", False)
            is_inventory = location.get("inventory_location", False)
            is_selling = location.get("selling_location", False)

            for division in divisions:
                for department in departments:
                    class_list = classes.get(department, [])
                    for class_item in class_list:
                        row = {
                            "Week": week,
                            "Location": loc_name,
                            "Channel": location.get("channel", ""),
                            "Channel Group": location.get("channel_group", ""),
                            "Selling Channel": location.get("selling_channel", ""),
                            "Division": division,
                            "Department": department,
                            "Class": class_item,
                        }

                        # Determine metrics based on location type
                        if is_source:
                            # Source location: Has BOP, Receipts, On Order, NO Sales
                            row["BOP Units"] = np.random.randint(100, 1000)
                            row["Receipts Units"] = np.random.randint(30, 400)
                            row["On Order Units"] = np.random.randint(0, 300)
                            row["Gross Sales Units"] = 0
                        elif is_inventory:
                            # Inventory location: Has BOP and Sales, NO Receipts or On Order
                            row["BOP Units"] = np.random.randint(100, 1000)
                            row["Gross Sales Units"] = np.random.randint(50, 500)
                            row["Receipts Units"] = 0
                            row["On Order Units"] = 0
                        elif is_selling:
                            # Selling location (only selling is true): Just Sales
                            row["Gross Sales Units"] = np.random.randint(50, 500)
                            row["BOP Units"] = 0
                            row["Receipts Units"] = 0
                            row["On Order Units"] = 0
                        else:
                            # Default: All metrics
                            row["Gross Sales Units"] = np.random.randint(50, 500)
                            row["Receipts Units"] = np.random.randint(30, 400)
                            row["BOP Units"] = np.random.randint(100, 1000)
                            row["On Order Units"] = np.random.randint(0, 300)

                        data.append(row)

    return pd.DataFrame(data)


# -----------------------------
# Helpers
# -----------------------------

def apply_filters(df, filters):
    """Apply filters to dataframe"""
    filtered_df = df.copy()
    for attr, value in filters.items():
        if value:
            filtered_df = filtered_df[filtered_df[attr].isin(value)]
    return filtered_df


def get_group_key(group_values, row_attrs):
    """Create a unique key for a group"""
    return str(group_values)


def render_expandable_table(df, row_attrs, expanded_groups, metrics):
    """Render a table with expand/collapse functionality for grouped rows (metrics always expanded)"""
    if not row_attrs or len(df) == 0:
        return df

    # Check if 'Metric' or 'Metrics' is in row_attrs (metrics are always expanded)
    has_metrics = "Metric" in row_attrs or "Metrics" in row_attrs

    grouped = df.groupby(row_attrs)
    display_rows = []

    for group_key, group_df in grouped:
        group_id = get_group_key(group_key, row_attrs)
        is_metric_group = has_metrics and ("Metric" in str(group_key) or "Metrics" in str(group_key))
        is_expanded = True if is_metric_group else group_id in expanded_groups

        # Header row
        header_row = {}
        if isinstance(group_key, tuple):
            for i, attr in enumerate(row_attrs):
                header_row[attr] = group_key[i] if i < len(group_key) else ""
        else:
            header_row[row_attrs[0]] = group_key

        header_row["_expand_indicator"] = "" if is_metric_group else ("▼" if is_expanded else "▶")

        for metric in metrics:
            if metric in group_df.columns:
                header_row[metric] = group_df[metric].sum()
            elif "Value" in group_df.columns:
                header_row["Value"] = group_df["Value"].sum()

        display_rows.append(pd.DataFrame([header_row]))

        # Detail rows if expanded
        if is_expanded:
            detail_rows = group_df.copy()
            if row_attrs:
                first_attr = row_attrs[0]
                if first_attr in detail_rows.columns:
                    detail_rows[first_attr] = "  " + detail_rows[first_attr].astype(str)
            detail_rows["_expand_indicator"] = ""
            display_rows.append(detail_rows)

    if display_rows:
        return pd.concat(display_rows, ignore_index=True)
    return df


def apply_pivot_table(df, row_attrs, col_attrs, all_metrics):
    """Create a pivot table with row and column grouping (like Toolio)"""
    if not row_attrs and not col_attrs:
        return df

    has_metrics_in_rows = "Metrics" in row_attrs
    has_metrics_in_cols = "Metrics" in col_attrs

    row_attributes = [a for a in row_attrs if a != "Metrics"]
    col_attributes = [a for a in col_attrs if a != "Metrics"]

    available_metrics = [m for m in all_metrics if m in df.columns]
    if not available_metrics:
        return df

    final_row_attrs = row_attributes.copy()
    final_col_attrs = col_attributes.copy()

    # Melt when metrics dimension is used
    if has_metrics_in_rows or has_metrics_in_cols:
        id_vars = [c for c in df.columns if c not in available_metrics]
        melted_df = pd.melt(df, id_vars=id_vars, value_vars=available_metrics, var_name="Metric", value_name="Value")
        if has_metrics_in_rows and "Metric" not in final_row_attrs:
            final_row_attrs.append("Metric")
        if has_metrics_in_cols and "Metric" not in final_col_attrs:
            final_col_attrs.append("Metric")
        working_df = melted_df
        value_col = "Value"
    else:
        working_df = df
        value_col = available_metrics[0] if len(available_metrics) == 1 else available_metrics

    # Only rows
    if (row_attributes or has_metrics_in_rows) and not (col_attributes or has_metrics_in_cols):
        if has_metrics_in_rows:
            return working_df.groupby(final_row_attrs)[value_col].sum().reset_index()
        return working_df.groupby(row_attributes)[available_metrics].sum().reset_index()

    # Only columns
    if (col_attributes or has_metrics_in_cols) and not (row_attributes or has_metrics_in_rows):
        if has_metrics_in_cols:
            return working_df.groupby(final_col_attrs)[value_col].sum().reset_index()
        return working_df.groupby(col_attributes)[available_metrics].sum().reset_index()

    # Both rows and columns -> pivot
    if has_metrics_in_rows or has_metrics_in_cols:
        try:
            pivot = pd.pivot_table(
                working_df,
                values=value_col,
                index=final_row_attrs if final_row_attrs else ["Metric"],
                columns=final_col_attrs if final_col_attrs else ["Metric"],
                aggfunc="sum",
                fill_value=0,
            )
            if isinstance(pivot.columns, pd.MultiIndex):
                pivot.columns = ["_".join(map(str, col)) for col in pivot.columns.values]
            return pivot
        except Exception as e:
            st.error(f"Error creating pivot table: {e}")
            return df
    else:
        # Standard pivot per metric
        pivot_tables = []
        for metric in available_metrics:
            try:
                pv = pd.pivot_table(
                    working_df,
                    values=metric,
                    index=row_attributes,
                    columns=col_attributes,
                    aggfunc="sum",
                    fill_value=0,
                )
                if isinstance(pv.columns, pd.MultiIndex):
                    pv.columns = ["_".join(map(str, col)) for col in pv.columns.values]
                elif len(available_metrics) > 1:
                    pv.columns = [f"{c}_{metric}" for c in pv.columns]
                pivot_tables.append(pv)
            except Exception as e:
                st.error(f"Error creating pivot table for {metric}: {e}")
        if not pivot_tables:
            return df
        if len(pivot_tables) == 1:
            return pivot_tables[0]
        result = pivot_tables[0]
        for pt in pivot_tables[1:]:
            result = pd.concat([result, pt], axis=1)
        return result


# -----------------------------
# App Main
# -----------------------------

def main():
    st.title("📊 Toolio Lite - Merchandise Plan Demo")
    st.markdown("**Interactive demo showing how attributes, grouping, and filtering work in merchandise planning**")

    # Tabs
    config_tab, view_tab = st.tabs(["⚙️ Configuration", "📊 Data View"])

    # ---------------- Configuration Tab ----------------
    with config_tab:
        st.header("Location Configuration")
        st.markdown("**Configure up to 10 locations with their properties**")

        if not st.session_state.locations:
            st.session_state.locations = [{} for _ in range(5)]

        col_add, col_remove = st.columns(2)
        with col_add:
            if st.button("➕ Add Location", disabled=len(st.session_state.locations) >= 10):
                pass
        # Use a separate button to actually add (Streamlit buttons rerun, so we need a unique key)
        if st.button("➕ Add Location (confirm)", key="add_loc", disabled=len(st.session_state.locations) >= 10):
            st.session_state.locations.append({})
            st.rerun()

        with col_remove:
            if st.button("➖ Remove Last Location", disabled=len(st.session_state.locations) <= 1):
                pass
        if st.button("➖ Remove Last Location (confirm)", key="rem_loc", disabled=len(st.session_state.locations) <= 1):
            st.session_state.locations.pop()
            st.rerun()

        st.divider()

        for i, location in enumerate(st.session_state.locations):
            with st.expander(f"📍 Location {i+1}", expanded=i < 3):
                c1, c2, c3 = st.columns(3)
                with c1:
                    location_name = st.text_input(
                        "Location Name:",
                        value=location.get("name", ""),
                        key=f"loc_name_{i}",
                        placeholder="e.g., Store 1, Warehouse A",
                    )
                    location["name"] = location_name
                with c2:
                    channel = st.text_input(
                        "Channel:",
                        value=location.get("channel", ""),
                        key=f"loc_channel_{i}",
                        placeholder="e.g., Retail, Online",
                    )
                    location["channel"] = channel
                with c3:
                    channel_group = st.text_input(
                        "Channel Group:",
                        value=location.get("channel_group", ""),
                        key=f"loc_channel_group_{i}",
                        placeholder="e.g., E-commerce, Brick & Mortar",
                    )
                    location["channel_group"] = channel_group

                selling_channel = st.text_input(
                    "Selling Channel:",
                    value=location.get("selling_channel", ""),
                    key=f"loc_selling_channel_{i}",
                    placeholder="e.g., Online, Store, Wholesale",
                )
                location["selling_channel"] = selling_channel

                st.markdown("**Location Type:**")
                t1, t2, t3 = st.columns(3)
                with t1:
                    source_location = st.checkbox(
                        "Source Location",
                        value=location.get("source_location", False),
                        key=f"loc_source_{i}",
                        help="Holds inventory - receives, has on order and BOP, NO sales",
                    )
                    location["source_location"] = source_location
                with t2:
                    inventory_location = st.checkbox(
                        "Inventory Location",
                        value=location.get("inventory_location", False),
                        key=f"loc_inventory_{i}",
                        help="Holds inventory and sells - has sales and BOP, nothing else",
                    )
                    location["inventory_location"] = inventory_location
                with t3:
                    selling_location = st.checkbox(
                        "Selling Location",
                        value=location.get("selling_location", False),
                        key=f"loc_selling_{i}",
                        help="If only this is true, location just has sales",
                    )
                    location["selling_location"] = selling_location

                if not (source_location or inventory_location or selling_location):
                    st.info("⚠️ No location type selected - will default to all metrics")

        st.divider()

        st.header("Product Attributes")
        st.info(
            """
            **Fixed Attribute Hierarchy:**
            - **Division**: Mens, Womens
            - **Department**: Bottoms, Tops
            - **Class**:
              - For Tops: Long Sleeve, Short Sleeve
              - For Bottoms: Short Leg, Long Leg
            """
        )

        st.divider()

        if st.button("🔄 Generate Data", type="primary", use_container_width=True):
            valid_locations = [loc for loc in st.session_state.locations if loc.get("name", "").strip()]
            if not valid_locations:
                st.error("⚠️ Please add at least one location with a name before generating data.")
            else:
                with st.spinner("Generating data..."):
                    st.session_state.locations = valid_locations
                    st.session_state.data = generate_sample_data(valid_locations)
                    st.session_state.filtered_data = st.session_state.data.copy()
                    st.session_state.data_regenerated = True
                    st.success(f"✓ Data generated successfully for {len(valid_locations)} location(s)!")
                    st.rerun()

        if st.session_state.data is not None:
            st.subheader("📊 Data Preview")
            st.info(
                f"Total rows: {len(st.session_state.data):,} | Columns: {', '.join(st.session_state.data.columns.tolist())}"
            )
            st.dataframe(st.session_state.data.head(10), use_container_width=True, hide_index=True)

    # ---------------- Data View Tab ----------------
    with view_tab:
        if st.session_state.data is None:
            st.warning("⚠️ Please configure locations in the Configuration tab and generate data first.")
            st.info("💡 Click on the '⚙️ Configuration' tab above to set up your locations.")
            return

        data = st.session_state.data

        # Sidebar Controls
        with st.sidebar:
            st.header("⚙️ Controls")
            metrics = ["Gross Sales Units", "Receipts Units", "BOP Units", "On Order Units"]
            available_attributes = [c for c in data.columns if c not in metrics]
            all_grouping_options = available_attributes + ["Metrics"]

            st.subheader("📋 Select Attributes to Display")
            selected_attributes = st.multiselect(
                "Choose attributes to show in the table:",
                options=available_attributes,
                default=st.session_state.selected_attributes,
                help="Select which attribute columns to display in the data table",
            )
            st.session_state.selected_attributes = selected_attributes

            st.divider()

            st.subheader("🔀 Group By (Rows & Columns)")
            st.markdown("**Group by Rows** (vertical grouping)")
            group_by_rows = st.multiselect(
                "Rows:",
                options=all_grouping_options,
                default=st.session_state.group_by_rows,
                help="Attributes or metrics to group by rows (vertical grouping)",
            )
            st.session_state.group_by_rows = group_by_rows

            st.markdown("**Group by Columns** (horizontal grouping)")
            st.info("💡 Tip: Put 'Week' in columns to see time across the top (like Toolio)")
            group_by_columns = st.multiselect(
                "Columns:",
                options=all_grouping_options,
                default=st.session_state.group_by_columns,
                help="Attributes or metrics to group by columns (horizontal grouping - creates pivot table)",
            )
            st.session_state.group_by_columns = group_by_columns

            st.divider()

            st.subheader("🔍 Filters")
            st.info("Apply filters to narrow down the data view")
            filters = {}
            for attr in available_attributes:
                if attr != "Week":
                    unique_values = sorted(data[attr].unique().tolist())
                    selected_values = st.multiselect(
                        f"Filter by {attr}:",
                        options=unique_values,
                        default=st.session_state.filters.get(attr, []),
                        help=f"Filter data by {attr}",
                    )
                    if selected_values:
                        filters[attr] = selected_values
            if "Week" in filters:
                del filters["Week"]
            st.session_state.filters = filters

            st.divider()

            st.subheader("📊 Display Options")
            sort_columns_alphabetically = st.checkbox(
                "Sort Columns Alphabetically",
                value=st.session_state.get("sort_columns_alphabetically", False),
                help="Sort table columns in alphabetical order",
            )
            st.session_state.sort_columns_alphabetically = sort_columns_alphabetically

            st.divider()

            if st.button("🔄 Reset Filters", type="secondary"):
                st.session_state.selected_attributes = []
                st.session_state.group_by_rows = []
                st.session_state.group_by_columns = []
                st.session_state.filters = {}
                st.session_state.filtered_data = st.session_state.data.copy()
                st.rerun()

        # Main content area
        filtered_data = apply_filters(data, st.session_state.filters)

        # Apply grouping/pivot
        if st.session_state.group_by_rows or st.session_state.group_by_columns:
            filtered_data = apply_pivot_table(
                filtered_data,
                st.session_state.group_by_rows,
                st.session_state.group_by_columns,
                ["Gross Sales Units", "Receipts Units", "BOP Units", "On Order Units"],
            )
        st.session_state.filtered_data = filtered_data

        # Totals (before pivot)
        filtered_for_totals = apply_filters(data, st.session_state.filters)
        total_gross_sales = filtered_for_totals["Gross Sales Units"].sum()
        total_receipts = filtered_for_totals["Receipts Units"].sum()
        total_bop = filtered_for_totals["BOP Units"].sum()
        total_on_order = filtered_for_totals["On Order Units"].sum()

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Gross Sales Units", f"{total_gross_sales:,.0f}")
        with m2:
            st.metric("Receipts Units", f"{total_receipts:,.0f}")
        with m3:
            st.metric("BOP Units", f"{total_bop:,.0f}")
        with m4:
            st.metric("On Order Units", f"{total_on_order:,.0f}")

        st.divider()

        with st.expander("⚙️ Grouping & Filtering Controls", expanded=True):
            metrics_local = ["Gross Sales Units", "Receipts Units", "BOP Units", "On Order Units"]
            available_attributes_local = [c for c in data.columns if c not in metrics_local]
            all_grouping_options_local = available_attributes_local + ["Metrics"]

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**🔀 Group by Rows**")
                group_by_rows_main = st.multiselect(
                    "Select attributes for row grouping:",
                    options=all_grouping_options_local,
                    default=st.session_state.group_by_rows,
                    help="Attributes or metrics to group by rows (vertical grouping)",
                    key="group_by_rows_main",
                )
                st.session_state.group_by_rows = group_by_rows_main
            with c2:
                st.markdown("**🔀 Group by Columns**")
                st.info("💡 Tip: Put 'Week' in columns to see time across the top")
                group_by_columns_main = st.multiselect(
                    "Select attributes for column grouping:",
                    options=all_grouping_options_local,
                    default=st.session_state.group_by_columns,
                    help="Attributes or metrics to group by columns (horizontal grouping - creates pivot table)",
                    key="group_by_columns_main",
                )
                st.session_state.group_by_columns = group_by_columns_main

        st.divider()

        # Display table
        st.subheader("📈 Data Table")

        if isinstance(filtered_data, pd.DataFrame) and len(filtered_data) > 0:
            if st.session_state.group_by_rows and not st.session_state.group_by_columns:
                # Expand/Collapse controls
                st.markdown("**🔽 Expand/Collapse Groups:**")
                st.info("💡 Click the buttons below to expand/collapse groups. Metrics are always expanded.")

                grouped = filtered_data.groupby(st.session_state.group_by_rows)
                groups_list = list(grouped)
                non_metric_groups = [g for g in groups_list if "Metric" not in str(g[0]) and "Metrics" not in st.session_state.group_by_rows]
                cols_per_row = min(4, max(1, len(non_metric_groups)))
                button_cols = st.columns(cols_per_row)
                idx = 0
                for group_key, _ in non_metric_groups:
                    group_id = get_group_key(group_key, st.session_state.group_by_rows)
                    is_expanded = group_id in st.session_state.expanded_groups
                    label = " | ".join(map(str, group_key)) if isinstance(group_key, tuple) else str(group_key)
                    with button_cols[idx % cols_per_row]:
                        if st.button(f"{'▼' if is_expanded else '▶'} {label[:25]}", key=f"expand_{group_id}", use_container_width=True):
                            if is_expanded:
                                st.session_state.expanded_groups.discard(group_id)
                            else:
                                st.session_state.expanded_groups.add(group_id)
                            st.rerun()
                    idx += 1

                st.divider()
                display_df = render_expandable_table(
                    filtered_data,
                    st.session_state.group_by_rows,
                    st.session_state.expanded_groups,
                    ["Gross Sales Units", "Receipts Units", "BOP Units", "On Order Units"],
                )
            else:
                # No rows-only grouping -> raw/pivot output
                if not (st.session_state.group_by_rows or st.session_state.group_by_columns):
                    # Select columns
                    metrics_cols = ["Gross Sales Units", "Receipts Units", "BOP Units", "On Order Units"]
                    display_columns = []
                    if st.session_state.selected_attributes:
                        for attr in st.session_state.selected_attributes:
                            if attr in filtered_data.columns:
                                display_columns.append(attr)
                    else:
                        display_columns = [c for c in filtered_data.columns if c not in metrics_cols]
                    for m in metrics_cols:
                        if m in filtered_data.columns:
                            display_columns.append(m)
                    display_columns = [c for c in display_columns if c in filtered_data.columns]
                    display_df = filtered_data[display_columns] if display_columns else filtered_data
                else:
                    display_df = filtered_data

            if st.session_state.get("sort_columns_alphabetically", False):
                display_df = display_df[sorted(display_df.columns.tolist())]

            st.dataframe(display_df, use_container_width=True, hide_index=False, height=500)
            st.caption(f"Showing {len(display_df):,} rows" if isinstance(display_df, pd.DataFrame) else "Pivot table view")
        else:
            st.warning("No data matches the current filters. Please adjust your filters.")

        # Instructions
        with st.expander("ℹ️ How to Use This Demo"):
            st.markdown(
                """
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
                   - Tip: Put 'Week' in columns to see time across
                3. **Filters**: Narrow down data by selecting specific attribute values
                4. **Metrics**: The four key metrics:
                   - **Gross Sales Units**: Units sold
                   - **Receipts Units**: Units received
                   - **BOP Units**: Beginning of period inventory
                   - **On Order Units**: Units currently on order

                ### Example Workflow:
                1. Configure 3–5 locations with different types
                2. Generate data
                3. Group by Rows: Division, Department, Class
                4. Group by Columns: Week (to see time across)
                5. Filter by Location to see specific stores
                """
            )


if __name__ == "__main__":
    main()
