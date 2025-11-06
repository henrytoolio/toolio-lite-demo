import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ===================================================
# Page Config
# ===================================================
st.set_page_config(page_title="Toolio Lite - Merchandise Plan Demo", page_icon="📊", layout="wide")

# ===================================================
# Initialize Session State
# ===================================================
for key, default in [
    ("data", None),
    ("filtered_data", None),
    ("group_by_rows", []),
    ("filters", {}),
    ("locations", []),
    ("expanded_groups", set()),
]:
    if key not in st.session_state:
        st.session_state[key] = default

METRICS = ["Gross Sales Units", "Receipts Units", "BOP Units", "On Order Units"]

# ===================================================
# Data Generation
# ===================================================
def generate_sample_data(locations):
    """Generate sample data based on configured locations"""
    np.random.seed(42)
    start_date = datetime.now().replace(day=1)
    weeks = [(start_date + timedelta(weeks=i)).strftime("%Y-%m-%d") for i in range(4)]
    divisions = ["Mens", "Womens"]
    departments = ["Bottoms", "Tops"]
    classes = {"Tops": ["Long Sleeve", "Short Sleeve"], "Bottoms": ["Short Leg", "Long Leg"]}
    data = []
    for week in weeks:
        for loc in locations:
            for div in divisions:
                for dept in departments:
                    for cls in classes[dept]:
                        row = {
                            "Week": week,
                            "Location": loc.get("name", ""),
                            "Channel": loc.get("channel", ""),
                            "Channel Group": loc.get("channel_group", ""),
                            "Selling Channel": loc.get("selling_channel", ""),
                            "Division": div,
                            "Department": dept,
                            "Class": cls,
                        }
                        # Metrics behavior
                        if loc.get("source_location"):
                            row["BOP Units"] = np.random.randint(100, 1000)
                            row["Receipts Units"] = np.random.randint(30, 400)
                            row["On Order Units"] = np.random.randint(0, 300)
                            row["Gross Sales Units"] = 0
                        elif loc.get("inventory_location"):
                            row["BOP Units"] = np.random.randint(100, 1000)
                            row["Gross Sales Units"] = np.random.randint(50, 500)
                            row["Receipts Units"] = 0
                            row["On Order Units"] = 0
                        elif loc.get("selling_location"):
                            row["Gross Sales Units"] = np.random.randint(50, 500)
                            row["BOP Units"] = 0
                            row["Receipts Units"] = 0
                            row["On Order Units"] = 0
                        else:
                            row["Gross Sales Units"] = np.random.randint(50, 500)
                            row["Receipts Units"] = np.random.randint(30, 400)
                            row["BOP Units"] = np.random.randint(100, 1000)
                            row["On Order Units"] = np.random.randint(0, 300)
                        data.append(row)
    return pd.DataFrame(data)

# ===================================================
# Helper Functions
# ===================================================
def apply_filters(df, filters):
    out = df.copy()
    for col, vals in filters.items():
        if vals:
            out = out[out[col].isin(vals)]
    return out

def key_tuple_to_str(parts):
    if isinstance(parts, tuple):
        return "|".join(map(str, parts))
    return str(parts)

def melt_and_pivot(df):
    melted = df.melt(
        id_vars=[c for c in df.columns if c not in METRICS],
        value_vars=METRICS,
        var_name="Metric",
        value_name="Value",
    )
    pivoted = pd.pivot_table(
        melted,
        values="Value",
        index=[c for c in melted.columns if c not in ["Week", "Value"]],
        columns="Week",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()
    return pivoted

# ---------------- Grid Rendering ----------------
GRID_CSS = """
<style>
.toolio-header, .toolio-row {display: grid; grid-template-columns: var(--grid-cols); align-items: center;}
.toolio-header {background:#fafafa; font-weight:600; border-bottom:1px solid #e0e0e0;}
.toolio-row {border-bottom:1px solid #e0e0e0;}
.toolio-cell {padding:6px 8px; border-right:1px solid #e0e0e0;}
.toolio-cell:last-child {border-right:none;}
.toolio-metric {font-weight:700; background:#f9f9f9;}
.toolio-hover:hover {background:#f6faff;}
.toolio-mono {font-variant-numeric: tabular-nums; text-align:right;}
.toolio-arrow {padding:0 4px; cursor:pointer; font-size:14px;}
</style>
"""
st.markdown(GRID_CSS, unsafe_allow_html=True)

def render_hierarchy(df, attrs, level, parent_key, week_cols):
    if not attrs or level >= len(attrs):
        return
    attr = attrs[level]
    groups = df.groupby(attr, dropna=False)
    for val, gdf in groups:
        key_tuple = parent_key + (val,)
        key_str = key_tuple_to_str(key_tuple)
        expanded = key_str in st.session_state.expanded_groups
        arrow = "▼" if expanded else "▶"
        indent = "&nbsp;" * (level * 4)
        week_vals = [int(gdf[w].sum()) if w in gdf.columns else 0 for w in week_cols]

        cols = st.columns([0.45] + [0.11] * len(week_cols))
        with cols[0]:
            if st.button(arrow, key=f"btn_{key_str}"):
                if expanded:
                    st.session_state.expanded_groups.discard(key_str)
                else:
                    st.session_state.expanded_groups.add(key_str)
                st.rerun()
            st.markdown(f"{indent}{val}", unsafe_allow_html=True)
        for i, w in enumerate(week_cols):
            with cols[i + 1]:
                st.markdown(f"<div class='toolio-cell toolio-mono'>{week_vals[i]:,}</div>", unsafe_allow_html=True)

        if expanded and level + 1 < len(attrs):
            render_hierarchy(gdf, attrs, level + 1, key_tuple, week_cols)

# ===================================================
# Main App
# ===================================================
def main():
    st.title("📊 Toolio Lite - Merchandise Plan Demo")
    st.markdown("Interactive hierarchy and location-based data configuration.")

    config_tab, view_tab = st.tabs(["⚙️ Configuration", "📊 Data View"])

    # ---------------- CONFIGURATION TAB ----------------
    with config_tab:
        st.header("Location Configuration")

        with st.expander("📍 Configure Locations", expanded=False):
            st.markdown("**Configure up to 10 locations with their properties**")

            if 'locations' not in st.session_state or len(st.session_state.locations) == 0:
                st.session_state.locations = [{} for _ in range(min(10, 3))]

            if st.button("📕 Collapse All Locations"):
                st.session_state.collapse_all_locations = True
                st.rerun()
            else:
                st.session_state.collapse_all_locations = False

            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("➕ Add Location", disabled=len(st.session_state.locations) >= 10):
                    st.session_state.locations.append({})
                    st.rerun()
            with col2:
                if st.button("➖ Remove Last Location", disabled=len(st.session_state.locations) <= 1):
                    st.session_state.locations.pop()
                    st.rerun()

            st.divider()

            for i, location in enumerate(st.session_state.locations):
                expanded = not st.session_state.get('collapse_all_locations', False) and i < 3
                with st.expander(f"📍 Location {i+1}", expanded=expanded):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        location['name'] = st.text_input("Location Name:", value=location.get('name', ''), key=f"loc_name_{i}", placeholder="e.g., Store 1, Warehouse A")
                    with col2:
                        location['channel'] = st.text_input("Channel:", value=location.get('channel', ''), key=f"loc_channel_{i}", placeholder="e.g., Retail, Online")
                    with col3:
                        location['channel_group'] = st.text_input("Channel Group:", value=location.get('channel_group', ''), key=f"loc_channel_group_{i}", placeholder="e.g., E-commerce, Brick & Mortar")

                    location['selling_channel'] = st.text_input("Selling Channel:", value=location.get('selling_channel', ''), key=f"loc_selling_channel_{i}", placeholder="e.g., Online, Store, Wholesale")

                    st.markdown("**Location Type:**")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        location['source_location'] = st.checkbox("Source Location", value=location.get('source_location', False), key=f"loc_source_{i}")
                    with col2:
                        location['inventory_location'] = st.checkbox("Inventory Location", value=location.get('inventory_location', False), key=f"loc_inventory_{i}")
                    with col3:
                        location['selling_location'] = st.checkbox("Selling Location", value=location.get('selling_location', False), key=f"loc_selling_{i}")

                    if not any([location['source_location'], location['inventory_location'], location['selling_location']]):
                        st.info("⚠️ No location type selected - will default to all metrics")

            st.session_state.locations = st.session_state.locations

        st.divider()
        if st.button("🔄 Generate Data", type="primary", use_container_width=True):
            valid_locations = [loc for loc in st.session_state.locations if loc.get('name', '').strip()]
            if len(valid_locations) == 0:
                st.error("⚠️ Please add at least one location with a name before generating data.")
            else:
                with st.spinner("Generating data..."):
                    st.session_state.locations = valid_locations
                    st.session_state.data = generate_sample_data(valid_locations)
                    st.session_state.filtered_data = st.session_state.data.copy()
                    st.success(f"✓ Data generated successfully for {len(valid_locations)} location(s)!")
                    st.rerun()

        if st.session_state.data is not None:
            st.subheader("📊 Data Preview")
            st.dataframe(st.session_state.data.head(10), use_container_width=True, hide_index=True)

    # ---------------- DATA VIEW TAB ----------------
    with view_tab:
        if st.session_state.data is None:
            st.warning("⚠️ Generate data first.")
            return

        df = st.session_state.data
        all_attrs = [c for c in df.columns if c not in METRICS]

        with st.sidebar:
            st.header("⚙️ Controls")
            row_attrs = st.multiselect("Group by Attributes", options=[c for c in all_attrs if c != "Week"], default=["Channel", "Channel Group"])
            filters = {}
            for a in [c for c in all_attrs if c != "Week"]:
                vals = sorted(df[a].dropna().unique().tolist())
                sel = st.multiselect(f"Filter {a}", options=vals, key=f"flt_{a}")
                if sel:
                    filters[a] = sel
            st.session_state.group_by_rows = row_attrs
            st.session_state.filters = filters
            if st.button("Collapse All"):
                st.session_state.expanded_groups.clear()
                st.rerun()

        df_filtered = apply_filters(df, st.session_state.filters)
        df_m = melt_and_pivot(df_filtered)
        week_cols = [c for c in df_m.columns if c not in all_attrs + ["Metric"]]

        st.subheader("📈 Interactive Grid (Toolio Layout)")
        for metric, gdf in df_m.groupby("Metric"):
            st.markdown(f"### **{metric}**")
            render_hierarchy(gdf, st.session_state.group_by_rows, 0, (metric,), week_cols)

# ===================================================
if __name__ == "__main__":
    main()

