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
    ("expanded_groups", set()),  # stores keys of expanded nodes
    ("collapse_all_locations", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# Metrics for the demo
METRICS = ["Gross Sales Units", "Receipts Units", "BOP Units", "On Order Units"]

# ===================================================
# Data Generation
# ===================================================
def generate_sample_data(locations):
    """Generate sample data based on configured locations"""
    np.random.seed(42)
    start_date = datetime.now().replace(day=1)
    # 4 weekly buckets
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
                        # Metrics behavior by location type
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
# Helpers
# ===================================================
def apply_filters(df, filters):
    out = df.copy()
    for col, vals in filters.items():
        if vals:
            out = out[out[col].isin(vals)]
    return out

def key_tuple_to_str(parts):
    """Unique key for session-state expansion tracking"""
    if isinstance(parts, tuple):
        return "|".join(map(str, parts))
    return str(parts)

def melt_and_pivot(df):
    """
    Melt metrics into 'Metric','Value' and pivot weeks into columns.
    Returns a wide DF with: [all attributes..., 'Metric', <week columns>...]
    """
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
# CSS for Toolio-like Grid
# ===================================================
GRID_CSS = """
<style>
/* Table wrapper for horizontal scroll if needed */
.toolio-wrap {
  width: 100%;
  overflow-x: auto;
}

/* True table look */
.toolio-table {
  border-collapse: collapse;
  width: 100%;
  table-layout: fixed;
  border: 1px solid #e0e0e0;
  font-size: 0.95rem;
}

/* Header styling */
.toolio-table thead th {
  position: sticky;
  top: 0;
  background: #fafafa;
  font-weight: 700;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
  border-right: 1px solid #e0e0e0;
  padding: 8px 10px;
  white-space: nowrap;
}

/* Body cells */
.toolio-table tbody td {
  border-bottom: 1px solid #e0e0e0;
  border-right: 1px solid #e0e0e0;
  padding: 6px 10px;
  vertical-align: middle;
}

/* Last cell border-right cleanup */
.toolio-table tr td:last-child, .toolio-table thead th:last-child {
  border-right: none;
}

/* Numeric alignment */
.toolio-num {
  font-variant-numeric: tabular-nums;
  text-align: right;
  white-space: nowrap;
}

/* Metric rows */
.toolio-metric {
  background: #f9f9f9;
  font-weight: 700;
}

/* Hover effect for readability */
.toolio-table tbody tr:hover {
  background: #f6faff;
}

/* Arrow button */
.toolio-arrow {
  display: inline-block;
  padding: 0 6px;
  margin-right: 6px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  cursor: pointer;
  user-select: none;
  text-decoration: none;
  color: inherit;
}

/* Indentation container */
.toolio-indent {
  display: inline-block;
}

/* Prevent button underline */
a.toolio-arrow { text-decoration: none; }
</style>
"""
st.markdown(GRID_CSS, unsafe_allow_html=True)

# ===================================================
# Grid Rendering
# ===================================================
def render_table_header(group_attrs, week_cols):
    # Build header HTML
    headers = ["Metric"] + group_attrs + [f"Week {w}" for w in week_cols]
    ths = "".join([f"<th>{h}</th>" for h in headers])
    return f"<thead><tr>{ths}</tr></thead>"

def sum_week_values(df, week_cols):
    return [int(df[w].sum()) if w in df.columns else 0 for w in week_cols]

def html_escape(s):
    return ("" if s is None else str(s)).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def render_metric_row(metric_name, df_metric, group_attrs, week_cols):
    """Metric header row (bold, shaded). Group columns blank; weeks show rollup for the metric."""
    num_vals = sum_week_values(df_metric, week_cols)
    tds = []
    # Metric cell
    tds.append(f"<td class='toolio-metric'>{html_escape(metric_name)}</td>")
    # Group columns (blank on metric header)
    for _ in group_attrs:
        tds.append("<td class='toolio-metric'></td>")
    # Week numeric columns
    for v in num_vals:
        tds.append(f"<td class='toolio-metric toolio-num'>{v:,}</td>")
    return f"<tr class='toolio-metric'>{''.join(tds)}</tr>"

def render_group_row(level, group_attrs, level_idx, labels, current_label, is_expanded, key_str, df_group, week_cols):
    """
    Render a single group row:
    - level: current depth (0..)
    - group_attrs: full list of group-by columns
    - level_idx: which column this label belongs to
    - labels: path labels above this node (for indentation)
    - current_label: display value for this node
    - is_expanded: whether this node is expanded
    - key_str: session-state key
    - df_group: dataframe subset for this node
    - week_cols: week columns for numeric values
    """
    num_vals = sum_week_values(df_group, week_cols)
    tds = []

    # Metric column is empty on group rows
    tds.append("<td></td>")

    # For each group column, place label only at the current level; others blank
    for idx, colname in enumerate(group_attrs):
        if idx == level_idx:
            # Arrow + indent inside this cell
            indent_px = 14 * level  # visual indentation
            arrow = "▼" if is_expanded else "▶"
            # Render arrow as a button (Streamlit will handle clicks outside HTML)
            # We'll place a unique placeholder and then swap with a button via st.button nearby.
            # But easier: use a unique link and capture via query params? In Streamlit, simplest is to inject a button via st.button and keep this cell showing label only.
            # Instead: we render a small form button in a separate st.columns row (works, but we want single HTML table).
            # Pragmatic approach: render the arrow as a link with a unique href and catch it with st.experimental_set_query_params doesn't persist well. So we do buttons via st.form + st.columns outside.
            # To stay purely HTML and still clickable in Streamlit, we use st.form/button approach per row after composing HTML row-by-row (below).
            label_html = f"""
              <div style="display:flex;align-items:center;">
                <div class="toolio-indent" style="width:{indent_px}px;"></div>
                <span id="label_{key_str}">{html_escape(current_label)}</span>
              </div>
            """
            # Temporarily put an arrow slot we replace with a real Streamlit button beside the table row
            tds.append(f"<td>{label_html}</td>")
        else:
            tds.append("<td></td>")

    # Week numeric columns
    for v in num_vals:
        tds.append(f"<td class='toolio-num'>{v:,}</td>")

    return f"<tr>{''.join(tds)}</tr>"

def render_hierarchy_html(df_metric, group_attrs, week_cols, path_values, level, rows_html, button_rows):
    """
    Recursively append rows to rows_html and collect Streamlit buttons to control expansion.
    We render HTML rows, but clickable arrows are Streamlit buttons placed immediately under the table,
    aligned logically by sequence. Each button toggles the node and triggers rerun.
    """
    if not group_attrs or level >= len(group_attrs):
        return

    attr = group_attrs[level]
    # Stable ordering for groups
    for val, gdf in df_metric.groupby(attr, dropna=False, sort=False):
        # Unique key for this node: (metric, path_values + current val)
        node_values = tuple(path_values + [val])
        key_str = key_tuple_to_str(node_values)
        is_expanded = key_str in st.session_state.expanded_groups

        # HTML row (arrow is rendered as text; real click button comes later)
        rows_html.append(
            render_group_row(
                level=level,
                group_attrs=group_attrs,
                level_idx=level,
                labels=path_values,
                current_label=("(blank)" if val in [None, ""] else str(val)),
                is_expanded=is_expanded,
                key_str=key_str,
                df_group=gdf,
                week_cols=week_cols,
            )
        )

        # Collect a toggle button to place below the table, with a readable label and same order
        button_rows.append((key_str, is_expanded, "(blank)" if val in [None, ""] else str(val)))

        # Recurse only if expanded
        if is_expanded and level + 1 < len(group_attrs):
            render_hierarchy_html(gdf, group_attrs, week_cols, path_values + [val], level + 1, rows_html, button_rows)

def render_metric_section_html(metric, df_metric, group_attrs, week_cols):
    """
    Build complete HTML for one metric section (metric header row + its hierarchy),
    and return (html_string, button_specs) where button_specs are the nodes with toggle buttons.
    """
    rows_html = []
    button_rows = []

    # Metric header row
    rows_html.append(render_metric_row(metric, df_metric, group_attrs, week_cols))

    # Hierarchy under this metric
    if group_attrs:
        render_hierarchy_html(
            df_metric=df_metric,
            group_attrs=group_attrs,
            week_cols=week_cols,
            path_values=[metric],   # first element is metric
            level=0,
            rows_html=rows_html,
            button_rows=button_rows,
        )

    return "\n".join(rows_html), button_rows

def render_grid(df_wide, group_attrs, week_cols):
    """
    Render full Toolio-style table:
    - Metric in first column
    - Grouping columns next (dynamic depth)
    - Weeks columns at the end
    - Subtle gridlines and right-aligned numerics
    - Expand/collapse per node (buttons drawn under table)
    """
    # Build HTML table
    html_parts = []
    html_parts.append("<div class='toolio-wrap'>")
    html_parts.append("<table class='toolio-table'>")
    html_parts.append(render_table_header(group_attrs, week_cols))
    html_parts.append("<tbody>")

    # Collect buttons we need to draw after the table (to actually toggle state)
    all_buttons = []

    for metric, gdf in df_wide.groupby("Metric"):
        section_html, btns = render_metric_section_html(metric, gdf, group_attrs, week_cols)
        html_parts.append(section_html)
        all_buttons.extend(btns)

    html_parts.append("</tbody></table></div>")

    # Show the table
    st.markdown("".join(html_parts), unsafe_allow_html=True)

    # Draw the buttons in the same order as rows. Each toggles its node only.
    # We use a layout with multiple columns for compactness.
    if all_buttons:
        st.markdown("###### Expand / Collapse")
        cols = st.columns(min(6, max(1, len(all_buttons))))
        for i, (key_str, is_expanded, label) in enumerate(all_buttons):
            with cols[i % len(cols)]:
                if st.button(("▼ " if is_expanded else "▶ ") + label, key=f"btn_{key_str}"):
                    if is_expanded:
                        st.session_state.expanded_groups.discard(key_str)
                    else:
                        st.session_state.expanded_groups.add(key_str)
                    st.rerun()

# ===================================================
# Main App
# ===================================================
def main():
    st.title("📊 Toolio Lite - Merchandise Plan Demo")
    st.markdown("Metrics in the first column • Click to drill down groups • Weeks in columns (Toolio-style)")

    # Tabs
    config_tab, view_tab = st.tabs(["⚙️ Configuration", "📊 Data View"])

    # ---------------- CONFIG TAB ----------------
    with config_tab:
        st.header("Location Configuration")

        # Collapsible config panel (always starts collapsed)
        with st.expander("📍 Configure Locations", expanded=False):
            st.markdown("**Configure up to 10 locations with their properties**")

            if not st.session_state.locations:
                st.session_state.locations = [{} for _ in range(3)]

            # Collapse all nested location forms quickly
            if st.button("📕 Collapse All Locations"):
                st.session_state.collapse_all_locations = True
                st.rerun()
            else:
                st.session_state.collapse_all_locations = False

            # Add / Remove
            c1, c2 = st.columns(2)
            with c1:
                if st.button("➕ Add Location", disabled=len(st.session_state.locations) >= 10):
                    st.session_state.locations.append({})
                    st.rerun()
            with c2:
                if st.button("➖ Remove Last Location", disabled=len(st.session_state.locations) <= 1):
                    st.session_state.locations.pop()
                    st.rerun()

            st.divider()

            # Each location is in its own expander
            for i, loc in enumerate(st.session_state.locations):
                expanded = not st.session_state.get("collapse_all_locations", False) and i < 3
                with st.expander(f"📍 Location {i+1}", expanded=expanded):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        loc["name"] = st.text_input("Location Name:", value=loc.get("name", ""), key=f"loc_name_{i}", placeholder="e.g., Store 1, Warehouse A")
                    with c2:
                        loc["channel"] = st.text_input("Channel:", value=loc.get("channel", ""), key=f"loc_channel_{i}", placeholder="e.g., Ecom, Wholesale")
                    with c3:
                        loc["channel_group"] = st.text_input("Channel Group:", value=loc.get("channel_group", ""), key=f"loc_channel_group_{i}", placeholder="e.g., Store, Web")
                    loc["selling_channel"] = st.text_input("Selling Channel:", value=loc.get("selling_channel", ""), key=f"loc_selling_channel_{i}", placeholder="e.g., Online, Store, Wholesale")

                    st.markdown("**Location Type:**")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        loc["source_location"] = st.checkbox("Source Location", value=loc.get("source_location", False), key=f"loc_source_{i}")
                    with c2:
                        loc["inventory_location"] = st.checkbox("Inventory Location", value=loc.get("inventory_location", False), key=f"loc_inventory_{i}")
                    with c3:
                        loc["selling_location"] = st.checkbox("Selling Location", value=loc.get("selling_location", False), key=f"loc_selling_{i}")

                    if not any([loc.get("source_location"), loc.get("inventory_location"), loc.get("selling_location")]):
                        st.info("⚠️ No location type selected — will default to all metrics")

            # persist
            st.session_state.locations = st.session_state.locations

        st.divider()
        if st.button("🔄 Generate Data", type="primary", use_container_width=True):
            valid = [l for l in st.session_state.locations if l.get("name", "").strip()]
            if not valid:
                st.error("⚠️ Please add at least one location with a name before generating data.")
            else:
                with st.spinner("Generating data..."):
                    st.session_state.data = generate_sample_data(valid)
                    st.session_state.filtered_data = st.session_state.data.copy()
                    st.success(f"✓ Data generated successfully for {len(valid)} location(s)!")
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
            # Dynamic group-by (any depth, user-selected)
            row_attrs = st.multiselect(
                "Group by Rows (Hierarchy)",
                options=[c for c in all_attrs if c != "Week"],
                default=["Channel", "Channel Group", "Selling Channel"],
                help="Choose the attribute hierarchy to drill down through."
            )
            st.session_state.group_by_rows = row_attrs

            # Filters
            st.subheader("🔍 Filters")
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

        # Apply filters and pivot weeks
        df_filtered = apply_filters(df, st.session_state.filters)
        df_wide = melt_and_pivot(df_filtered)
        week_cols = [c for c in df_wide.columns if c not in [*all_attrs, "Metric"]]

        st.subheader("📈 Toolio-style Grid (click ▶ to expand)")
        render_grid(df_wide, st.session_state.group_by_rows, week_cols)

# ===================================================
if __name__ == "__main__":
    main()

