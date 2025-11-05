import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Toolio Lite Demo App - Toolio-style layout
# Metric as top-level, attributes nested, weeks as columns

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

def build_hierarchy_for_metric(df, attrs, level, parent_key, rows, week_cols, metric_name):
    if level >= len(attrs):
        return
    attr = attrs[level]
    groups = df.groupby(attr, dropna=False)
    for val, gdf in groups:
        key_tuple = parent_key + (val,)
        key_str = key_tuple_to_str(key_tuple)
        expanded = key_str in st.session_state.expanded_groups

        header = {"Metric": ""}  # Empty metric column for attribute rows
        for a in attrs:
            header[a] = ""
        header[attr] = ("  " * level) + (str(val) if val else "(blank)")
        header["_expand_indicator"] = "▼" if expanded else "▶"
        for w in week_cols:
            header[w] = gdf[w].sum() if w in gdf.columns else 0
        rows.append(header)

        if expanded:
            if level + 1 < len(attrs):
                build_hierarchy_for_metric(gdf, attrs, level + 1, key_tuple, rows, week_cols, metric_name)
            else:
                # Leaf level - show detail rows if needed
                pass

# -----------------------------
# Main App
# -----------------------------
def main():
    st.title("📊 Toolio Lite - Merchandise Plan Demo")
    st.markdown("Toolio-style layout: Metric as top-level, attributes nested, weeks as columns")

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

        rows = []
        for metric, gdf in df_m.groupby("Metric"):
            # Metric header row (always expanded, no expand indicator)
            metric_row = {"_expand_indicator": "", "Metric": f"**{metric}**"}
            for a in row_attrs:
                metric_row[a] = ""
            for w in week_cols:
                metric_row[w] = gdf[w].sum()
            rows.append(metric_row)

            # Build attribute hierarchy under this metric (always expanded for metrics)
            if row_attrs:
                build_hierarchy_for_metric(gdf, row_attrs, 0, (metric,), rows, week_cols, metric)

        display_df = pd.DataFrame(rows)
        ordered_cols = ["_expand_indicator", "Metric"] + row_attrs + week_cols
        for col in ordered_cols:
            if col not in display_df.columns:
                display_df[col] = ""
        display_df = display_df[ordered_cols]

        # Expand/Collapse buttons for attribute groups (metrics are always expanded)
        if row_attrs and len(rows) > 0:
            st.subheader("🔽 Expand / Collapse")
            # Get unique top-level attribute groups
            top_attr = row_attrs[0]
            unique_groups = set()
            for metric_name, gdf in df_m.groupby("Metric"):
                for val in gdf[top_attr].dropna().unique():
                    unique_groups.add((metric_name, val))
            
            if unique_groups:
                cols = st.columns(min(4, max(1, len(unique_groups))))
                for i, (metric_name, val) in enumerate(sorted(unique_groups)):
                    key_str = key_tuple_to_str((metric_name, val))
                    expanded = key_str in st.session_state.expanded_groups
                    label = f"{metric_name[:15]}... → {str(val)[:15]}"
                    with cols[i % len(cols)]:
                        if st.button(f"{'▼' if expanded else '▶'} {label}", key=f"expand_{key_str}"):
                            if expanded:
                                st.session_state.expanded_groups.discard(key_str)
                            else:
                                st.session_state.expanded_groups.add(key_str)
                            st.rerun()

        st.subheader("📈 Data Table (Toolio Layout)")
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        st.caption("Metric is top-level; attributes nest beneath. Weeks are columns. Expand/collapse applies only to attributes.")

if __name__ == "__main__":
    main()

