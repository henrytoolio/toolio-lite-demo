import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Toolio Lite Demo App (Metrics in Rows, Weeks in Columns, Hierarchical Expand/Collapse)

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

# -----------------------------
# Constants
# -----------------------------
METRICS = ["Gross Sales Units", "Receipts Units", "BOP Units", "On Order Units"]

# -----------------------------
# Data Generation
# -----------------------------
def generate_sample_data(locations):
    np.random.seed(42)
    start_date = datetime.now().replace(day=1)
    weeks = [(start_date + timedelta(weeks=i)).strftime("%Y-%m-%d") for i in range(3)]
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
                                "Location": loc.get("name", ""),
                                "Channel": loc.get("channel", ""),
                                "Channel Group": loc.get("channel_group", ""),
                                "Selling Channel": loc.get("selling_channel", ""),
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

def sum_week_columns(df, week_cols):
    return {c: df[c].sum() for c in week_cols}

def build_expandable_rows(df, row_attrs, level, parent_key, rows, week_cols):
    if level >= len(row_attrs):
        return

    attr = row_attrs[level]
    groups = df.groupby(attr, dropna=False)

    for value, gdf in groups:
        key_tuple = parent_key + (value,)
        key_str = key_tuple_to_str(key_tuple)
        expanded = key_str in st.session_state.expanded_groups

        # Header row (group roll-up)
        header = {a: "" for a in row_attrs}
        header[attr] = ("  " * level) + (str(value) if value else "(blank)")
        header["_expand_indicator"] = "▼" if expanded else "▶"

        # Roll-up totals for all metrics
        totals = gdf.groupby("Metric").sum(numeric_only=True)
        for w in week_cols:
            header[w] = totals[w].sum() if w in totals.columns else 0
        rows.append(header)

        # Drill down
        if expanded:
            if level + 1 < len(row_attrs):
                build_expandable_rows(gdf, row_attrs, level + 1, key_tuple, rows, week_cols)
            else:
                # At lowest group level, list metrics in rows
                for metric, mdf in gdf.groupby("Metric"):
                    m_row = {a: "" for a in row_attrs}
                    m_row[row_attrs[-1]] = ("  " * (level + 1)) + metric
                    m_row["_expand_indicator"] = ""
                    for w in week_cols:
                        m_row[w] = mdf[w].sum() if w in mdf.columns else 0
                    rows.append(m_row)

# -----------------------------
# Main App
# -----------------------------
def main():
    st.title("📊 Toolio Lite - Merchandise Plan Demo")
    st.markdown("Metrics in rows • Weeks in columns • Hierarchical expand/collapse")

    config_tab, view_tab = st.tabs(["⚙️ Configuration", "📊 Data View"])

    # ---------------- Configuration ----------------
    with config_tab:
        st.header("Location Configuration")
        if not st.session_state.locations:
            st.session_state.locations = [{} for _ in range(3)]

        c_add, c_remove = st.columns(2)
        with c_add:
            if st.button("➕ Add Location", disabled=len(st.session_state.locations) >= 10):
                st.session_state.locations.append({})
                st.rerun()
        with c_remove:
            if st.button("➖ Remove Last Location", disabled=len(st.session_state.locations) <= 1):
                st.session_state.locations.pop()
                st.rerun()

        for i, loc in enumerate(st.session_state.locations):
            with st.expander(f"📍 Location {i+1}", expanded=i < 2):
                c1, c2, c3 = st.columns(3)
                loc["name"] = c1.text_input("Location Name", loc.get("name", ""), key=f"name_{i}")
                loc["channel"] = c2.text_input("Channel", loc.get("channel", ""), key=f"channel_{i}")
                loc["channel_group"] = c3.text_input("Channel Group", loc.get("channel_group", ""), key=f"cg_{i}")
                loc["selling_channel"] = st.text_input("Selling Channel", loc.get("selling_channel", ""), key=f"sc_{i}")

        if st.button("🔄 Generate Data", type="primary"):
            valids = [l for l in st.session_state.locations if l.get("name")]
            if not valids:
                st.error("⚠️ Please add at least one location name.")
            else:
                st.session_state.data = generate_sample_data(valids)
                st.session_state.filtered_data = st.session_state.data.copy()
                st.success("✓ Data generated successfully!")
                st.rerun()

        if st.session_state.data is not None:
            st.subheader("📊 Data Preview")
            st.dataframe(st.session_state.data.head(10), use_container_width=True)

    # ---------------- Data View ----------------
    with view_tab:
        if st.session_state.data is None:
            st.warning("⚠️ Generate data first.")
            return

        df = st.session_state.data
        all_attrs = [c for c in df.columns if c not in METRICS]

        with st.sidebar:
            st.header("⚙️ Controls")
            row_attrs = st.multiselect(
                "Group by Rows",
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

            c1, c2 = st.columns(2)
            with c1:
                if st.button("Expand All"):
                    df_m = melt_and_pivot(apply_filters(df, filters))
                    groups = df_m.groupby(row_attrs)
                    st.session_state.expanded_groups = {key_tuple_to_str(k if isinstance(k, tuple) else (k,)) for k, _ in groups}
                    st.rerun()
            with c2:
                if st.button("Collapse All"):
                    st.session_state.expanded_groups.clear()
                    st.rerun()

        df_filtered = apply_filters(df, st.session_state.filters)
        df_m = melt_and_pivot(df_filtered)
        week_cols = [c for c in df_m.columns if c not in all_attrs + ["Metric"]]

        rows = []
        if row_attrs:
            build_expandable_rows(df_m, row_attrs, 0, tuple(), rows, week_cols)
        else:
            for metric, gdf in df_m.groupby("Metric"):
                row = {"_expand_indicator": "", row_attrs[-1] if row_attrs else "Metric": metric}
                for w in week_cols:
                    row[w] = gdf[w].sum()
                rows.append(row)

        display_df = pd.DataFrame(rows)
        ordered_cols = ["_expand_indicator"] + row_attrs + week_cols
        for col in ordered_cols:
            if col not in display_df.columns:
                display_df[col] = ""
        display_df = display_df[ordered_cols]

        st.subheader("📈 Data Table (Metrics in Rows, Weeks in Columns)")
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        st.caption("Metrics always appear in rows within each expanded group. Weeks span columns like Toolio.")

        with st.expander("ℹ️ How to Use This Demo"):
            st.markdown(
                """### Configuration Tab:\n1. Configure Locations (up to 10) with Channel, Channel Group, etc.\n2. Generate Data.\n\n### Data View Tab:\n1. Group by Rows → choose attributes to show (e.g., Channel, Channel Group).\n2. Weeks are across columns automatically.\n3. Metrics appear as sub-rows under each group and are always visible.\n4. Expand/Collapse controls reveal or hide lower levels in the hierarchy.\n\n### Example:\nGroup by: Channel → Channel Group.\n- Collapse Channel to see totals.\n- Expand Channel to see Channel Groups.\n- Each expanded level shows metrics as rows across week columns."""
            )

if __name__ == "__main__":
    main()

