import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Toolio Lite Demo App - Interactive Hierarchical Grid
# Metric as top-level, attributes nested, weeks as columns, per-node clickable toggles

st.set_page_config(page_title="Toolio Lite - Merchandise Plan Demo", page_icon="📊", layout="wide")

# -----------------------------
# Session State
# -----------------------------
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

# -----------------------------
# Data Generation
# -----------------------------
def generate_sample_data(locations):
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
                        data.append(
                            {
                                "Week": week,
                                "Channel": loc.get("channel", ""),
                                "Channel Group": loc.get("channel_group", ""),
                                "Division": div,
                                "Department": dept,
                                "Class": cls,
                                "Gross Sales Units": np.random.randint(50, 500),
                                "Receipts Units": np.random.randint(30, 400),
                                "BOP Units": np.random.randint(100, 1000),
                                "On Order Units": np.random.randint(0, 300),
                            }
                        )
    return pd.DataFrame(data)

# -----------------------------
# Helper Functions
# -----------------------------
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

        cols = st.columns([0.1 + 0.1 * level, 0.9 - 0.1 * level] + [0.2] * len(week_cols))

        with cols[0]:
            if st.button(arrow, key=f"toggle_{key_str}"):
                if expanded:
                    st.session_state.expanded_groups.discard(key_str)
                else:
                    st.session_state.expanded_groups.add(key_str)
                st.rerun()
        with cols[1]:
            st.write(("" if level == 0 else "".ljust(level * 4)) + str(val))
        for i, w in enumerate(week_cols):
            with cols[i + 2]:
                st.write(int(gdf[w].sum()))

        if expanded and level + 1 < len(attrs):
            render_hierarchy(gdf, attrs, level + 1, key_tuple, week_cols)

# -----------------------------
# Main App
# -----------------------------
def main():
    st.title("📊 Toolio Lite - Merchandise Plan Demo")
    st.markdown("Interactive hierarchy: per-node expand/collapse inside grid (Toolio-style)")

    config_tab, view_tab = st.tabs(["⚙️ Configuration", "📊 Data View"])

    with config_tab:
        st.header("Location Configuration")
        if not st.session_state.locations:
            st.session_state.locations = [{"channel": "Ecom", "channel_group": "Store"}, {"channel": "Wholesale", "channel_group": "Web"}]

        if st.button("🔄 Generate Data", type="primary"):
            st.session_state.data = generate_sample_data(st.session_state.locations)
            st.session_state.filtered_data = st.session_state.data.copy()
            st.success("✓ Data generated successfully!")
            st.rerun()

        if st.session_state.data is not None:
            st.dataframe(st.session_state.data.head(10), use_container_width=True)

    with view_tab:
        if st.session_state.data is None:
            st.warning("⚠️ Generate data first.")
            return

        df = st.session_state.data
        all_attrs = [c for c in df.columns if c not in METRICS]

        with st.sidebar:
            st.header("⚙️ Controls")
            row_attrs = st.multiselect(
                "Group by Attributes",
                options=[c for c in all_attrs if c != "Week"],
                default=["Channel", "Channel Group"],
            )

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
            render_hierarchy(gdf, row_attrs, 0, (metric,), week_cols)

if __name__ == "__main__":
    main()

