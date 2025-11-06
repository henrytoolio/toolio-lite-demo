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

def apply_filters(df, filters):
    out = df.copy()
    for col, vals in filters.items():
        if vals:
            out = out[out[col].isin(vals)]
    return out

def key_tuple_to_str(parts):
    return "|".join(map(str, parts)) if isinstance(parts, (list, tuple)) else str(parts)

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

# ===================================================
# CSS
# ===================================================
GRID_CSS = """
<style>
.toolio-table {
  border-collapse: collapse;
  width: 100%;
  table-layout: fixed;
  border: 1px solid #e0e0e0;
  font-size: 0.95rem;
}
.toolio-table th, .toolio-table td {
  border: 1px solid #e0e0e0;
  padding: 6px 10px;
  text-align: left;
  vertical-align: middle;
}
.toolio-table th {
  background-color: #fafafa;
  font-weight: 700;
}
.toolio-num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.toolio-metric {
  background: #f9f9f9;
  font-weight: 700;
}
.toolio-indent { display: inline-block; }
</style>
"""
st.markdown(GRID_CSS, unsafe_allow_html=True)

# ===================================================
# Grid Renderer (with inline Streamlit toggles)
# ===================================================
def render_table(df_wide, group_attrs, week_cols):
    st.markdown("<table class='toolio-table'><thead><tr>" +
                "".join([f"<th>{h}</th>" for h in ["Metric"] + group_attrs + [f"Week {w}" for w in week_cols]]) +
                "</tr></thead><tbody>", unsafe_allow_html=True)

    for metric, gdf in df_wide.groupby("Metric"):
        # Metric header
        totals = [int(gdf[w].sum()) for w in week_cols]
        metric_row = "<tr><td class='toolio-metric'>{}</td>{}<td class='toolio-metric toolio-num'>{}</td></tr>".format(
            metric,
            "".join(["<td class='toolio-metric'></td>" for _ in group_attrs]),
            "</td><td class='toolio-metric toolio-num'>".join([f"{v:,}" for v in totals])
        )
        st.markdown(metric_row, unsafe_allow_html=True)

        def recurse(df, level, path):
            if level >= len(group_attrs): return
            attr = group_attrs[level]
            for val, gsub in df.groupby(attr, dropna=False, sort=False):
                node_key = key_tuple_to_str(path + [val])
                is_expanded = node_key in st.session_state.expanded_groups
                label = "(blank)" if val in [None, ""] else str(val)
                totals = [int(gsub[w].sum()) for w in week_cols]
                indent = "&nbsp;" * (level * 4)
                cols = st.columns([0.05, 0.95])
                with cols[0]:
                    if st.button(("▼" if is_expanded else "▶") + " ", key=node_key):
                        if is_expanded:
                            st.session_state.expanded_groups.discard(node_key)
                        else:
                            st.session_state.expanded_groups.add(node_key)
                        st.rerun()
                with cols[1]:
                    st.markdown(f"{indent}**{label}**", unsafe_allow_html=True)
                row_html = "".join([f"<td class='toolio-num'>{v:,}</td>" for v in totals])
                st.markdown("<table class='toolio-table'><tr><td></td>" +
                            "".join(["<td></td>" for _ in group_attrs]) +
                            row_html + "</tr></table>", unsafe_allow_html=True)
                if is_expanded:
                    recurse(gsub, level + 1, path + [val])
        recurse(gdf, 0, [metric])

    st.markdown("</tbody></table>", unsafe_allow_html=True)

# ===================================================
# Main App
# ===================================================
def main():
    st.title("📊 Toolio Lite - Merchandise Plan Demo")
    st.markdown("Metrics fixed • Expand groups inline • Weeks in columns (Toolio-style)")

    config_tab, view_tab = st.tabs(["⚙️ Configuration", "📊 Data View"])
    with config_tab:
        st.header("Location Configuration")
        with st.expander("📍 Configure Locations", expanded=False):
            if not st.session_state.locations:
                st.session_state.locations = [{} for _ in range(3)]

            col1, col2 = st.columns(2)
            with col1:
                if st.button("➕ Add Location", disabled=len(st.session_state.locations) >= 10):
                    st.session_state.locations.append({})
                    st.rerun()
            with col2:
                if st.button("➖ Remove Last Location", disabled=len(st.session_state.locations) <= 1):
                    st.session_state.locations.pop()
                    st.rerun()

            for i, loc in enumerate(st.session_state.locations):
                with st.expander(f"📍 Location {i+1}", expanded=False):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        loc["name"] = st.text_input("Location Name:", value=loc.get("name", ""), key=f"loc_name_{i}")
                    with c2:
                        loc["channel"] = st.text_input("Channel:", value=loc.get("channel", ""), key=f"loc_channel_{i}")
                    with c3:
                        loc["channel_group"] = st.text_input("Channel Group:", value=loc.get("channel_group", ""), key=f"loc_channel_group_{i}")
                    loc["selling_channel"] = st.text_input("Selling Channel:", value=loc.get("selling_channel", ""), key=f"loc_selling_channel_{i}")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        loc["source_location"] = st.checkbox("Source", value=loc.get("source_location", False), key=f"loc_source_{i}")
                    with c2:
                        loc["inventory_location"] = st.checkbox("Inventory", value=loc.get("inventory_location", False), key=f"loc_inventory_{i}")
                    with c3:
                        loc["selling_location"] = st.checkbox("Selling", value=loc.get("selling_location", False), key=f"loc_selling_{i}")

        st.divider()
        if st.button("🔄 Generate Data", type="primary", use_container_width=True):
            valid = [l for l in st.session_state.locations if l.get("name", "").strip()]
            if not valid:
                st.error("⚠️ Please add at least one location.")
            else:
                with st.spinner("Generating data..."):
                    st.session_state.data = generate_sample_data(valid)
                    st.session_state.filtered_data = st.session_state.data.copy()
                    st.success(f"✓ Data generated for {len(valid)} location(s)!")
                    st.rerun()

    with view_tab:
        if st.session_state.data is None:
            st.warning("⚠️ Generate data first.")
            return
        df = st.session_state.data
        all_attrs = [c for c in df.columns if c not in METRICS]
        with st.sidebar:
            st.header("⚙️ Controls")
            row_attrs = st.multiselect("Group by Rows", options=[c for c in all_attrs if c != "Week"],
                                       default=["Channel", "Channel Group", "Selling Channel"])
            st.session_state.group_by_rows = row_attrs
            filters = {}
            for a in [c for c in all_attrs if c != "Week"]:
                vals = sorted(df[a].dropna().unique().tolist())
                sel = st.multiselect(f"Filter {a}", options=vals, key=f"flt_{a}")
                if sel:
                    filters[a] = sel
            st.session_state.filters = filters
            st.divider()
            if st.button("Collapse All"):
                st.session_state.expanded_groups.clear()
                st.rerun()
        df_filtered = apply_filters(df, st.session_state.filters)
        df_wide = melt_and_pivot(df_filtered)
        week_cols = [c for c in df_wide.columns if c not in [*all_attrs, "Metric"]]
        st.subheader("📈 Toolio-style Grid (click ▶ to expand)")
        render_table(df_wide, st.session_state.group_by_rows, week_cols)

if __name__ == "__main__":
    main()

