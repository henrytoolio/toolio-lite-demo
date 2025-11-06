import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ---------------- Page config ----------------
st.set_page_config(page_title="Toolio Lite - Merchandise Plan Demo", page_icon="📊", layout="wide")

# ---------------- Session state ----------------
for k, v in [
    ("data", None),
    ("filtered_data", None),
    ("group_by_rows", []),
    ("filters", {}),
    ("locations", []),
    ("expanded_groups", set()),
]:
    if k not in st.session_state:
        st.session_state[k] = v

METRICS = ["Gross Sales Units", "Receipts Units", "BOP Units", "On Order Units"]

# ---------------- Data generation ----------------
def generate_sample_data(locations):
    np.random.seed(42)
    start = datetime.now().replace(day=1)
    weeks = [(start + timedelta(weeks=i)).strftime("%Y-%m-%d") for i in range(4)]

    divisions = ["Mens", "Womens"]
    departments = ["Bottoms", "Tops"]
    classes = {"Tops": ["Long Sleeve", "Short Sleeve"], "Bottoms": ["Short Leg", "Long Leg"]}

    rows = []
    for w in weeks:
        for loc in locations:
            for div in divisions:
                for dep in departments:
                    for cls in classes[dep]:
                        r = {
                            "Week": w,
                            "Location": loc.get("name", ""),
                            "Channel": loc.get("channel", ""),
                            "Channel Group": loc.get("channel_group", ""),
                            "Selling Channel": loc.get("selling_channel", ""),
                            "Division": div,
                            "Department": dep,
                            "Class": cls,
                        }
                        if loc.get("source_location"):
                            r["BOP Units"] = np.random.randint(100, 1000)
                            r["Receipts Units"] = np.random.randint(30, 400)
                            r["On Order Units"] = np.random.randint(0, 300)
                            r["Gross Sales Units"] = 0
                        elif loc.get("inventory_location"):
                            r["BOP Units"] = np.random.randint(100, 1000)
                            r["Gross Sales Units"] = np.random.randint(50, 500)
                            r["Receipts Units"] = 0
                            r["On Order Units"] = 0
                        elif loc.get("selling_location"):
                            r["Gross Sales Units"] = np.random.randint(50, 500)
                            r["BOP Units"] = 0
                            r["Receipts Units"] = 0
                            r["On Order Units"] = 0
                        else:
                            r["Gross Sales Units"] = np.random.randint(50, 500)
                            r["Receipts Units"] = np.random.randint(30, 400)
                            r["BOP Units"] = np.random.randint(100, 1000)
                            r["On Order Units"] = np.random.randint(0, 300)
                        rows.append(r)
    return pd.DataFrame(rows)

# ---------------- Helpers ----------------
def apply_filters(df, filters):
    out = df.copy()
    for c, vals in filters.items():
        if vals:
            out = out[out[c].isin(vals)]
    return out

def key_str(parts):
    return "|".join(map(str, parts)) if isinstance(parts, (list, tuple)) else str(parts)

def melt_pivot_weeks(df):
    m = df.melt(
        id_vars=[c for c in df.columns if c not in METRICS],
        value_vars=METRICS,
        var_name="Metric",
        value_name="Value",
    )
    w = pd.pivot_table(
        m,
        values="Value",
        index=[c for c in m.columns if c not in ["Week", "Value"]],
        columns="Week",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()
    return w

def html_escape(s):
    return ("" if s is None else str(s)).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# ---------------- CSS ----------------
st.markdown("""
<style>
.toolio-wrap { width:100%; overflow-x:auto; }
.toolio-table { border-collapse:collapse; width:100%; table-layout:fixed; border:1px solid #e0e0e0; font-size:0.95rem; }
.toolio-table th, .toolio-table td { border:1px solid #e0e0e0; padding:6px 10px; vertical-align:middle; }
.toolio-table th { background:#fafafa; font-weight:700; text-align:left; white-space:nowrap; }
.toolio-num { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
.toolio-metric { background:#f9f9f9; font-weight:700; }
.toolio-arrow { cursor:pointer; padding:0 6px; margin-right:6px; border:1px solid #ccc; border-radius:4px; background:#fff; }
.toolio-arrow:hover { background:#f0f6ff; }
</style>
""", unsafe_allow_html=True)

# ---------------- Table rendering ----------------
def render_header(group_cols, week_cols):
    cols = ["Metric"] + group_cols + [f"Week {w}" for w in week_cols]
    return "<thead><tr>" + "".join(f"<th>{html_escape(c)}</th>" for c in cols) + "</tr></thead>"

def week_sums(df, week_cols):
    return [int(df[w].sum()) if w in df.columns else 0 for w in week_cols]

def tr_metric(metric, df_metric, group_cols, week_cols):
    nums = week_sums(df_metric, week_cols)
    tds = [f"<td class='toolio-metric'>{html_escape(metric)}</td>"]
    tds += ["<td class='toolio-metric'></td>" for _ in group_cols]
    tds += [f"<td class='toolio-metric toolio-num'>{v:,}</td>" for v in nums]
    return "<tr>" + "".join(tds) + "</tr>"

def render_grid(df_wide, group_cols, week_cols):
    st.markdown("<div class='toolio-wrap'><table class='toolio-table'>", unsafe_allow_html=True)
    st.markdown(render_header(group_cols, week_cols), unsafe_allow_html=True)
    st.markdown("<tbody>", unsafe_allow_html=True)

    for metric, df_m in df_wide.groupby("Metric"):
        st.markdown(tr_metric(metric, df_m, group_cols, week_cols), unsafe_allow_html=True)
        if group_cols:
            render_children(df_m, group_cols, week_cols, [metric], 0)

    st.markdown("</tbody></table></div>", unsafe_allow_html=True)

def render_children(df_metric, group_cols, week_cols, path, level):
    if level >= len(group_cols):
        return
    col = group_cols[level]
    for val, g in df_metric.groupby(col, dropna=False, sort=False):
        lbl = "(blank)" if val in [None, ""] else str(val)
        node_k = key_str(path + [val])
        expanded = node_k in st.session_state.expanded_groups
        arrow = "▼" if expanded else "▶"

        nums = week_sums(g, week_cols)
        tds = ["<td></td>"]  # blank metric cell
        for i, _ in enumerate(group_cols):
            if i == level:
                indent = "&nbsp;" * (level * 4)
                btn_key = f"btn_{node_k}"
                clicked = st.button(arrow, key=btn_key)
                if clicked:
                    if expanded:
                        st.session_state.expanded_groups.remove(node_k)
                    else:
                        st.session_state.expanded_groups.add(node_k)
                    st.rerun()
                cell_html = f"{indent}{lbl}"
                tds.append(f"<td>{cell_html}</td>")
            else:
                tds.append("<td></td>")
        tds += [f"<td class='toolio-num'>{v:,}</td>" for v in nums]
        st.markdown("<tr>" + "".join(tds) + "</tr>", unsafe_allow_html=True)
        if expanded:
            render_children(g, group_cols, week_cols, path + [val], level + 1)

# ---------------- Main app ----------------
def main():
    st.title("📊 Toolio Lite - Merchandise Plan Demo")
    st.caption("Metrics fixed in first column • Click ▶ next to a group to expand • Weeks as columns")

    config_tab, view_tab = st.tabs(["⚙️ Configuration", "📊 Data View"])

    with config_tab:
        st.header("Location Configuration")
        with st.expander("📍 Configure Locations (collapsed by default)", expanded=False):
            if not st.session_state.locations:
                st.session_state.locations = [{} for _ in range(3)]

            c1, c2 = st.columns(2)
            with c1:
                if st.button("➕ Add Location", disabled=len(st.session_state.locations) >= 10):
                    st.session_state.locations.append({})
                    st.rerun()
            with c2:
                if st.button("➖ Remove Last Location", disabled=len(st.session_state.locations) <= 1):
                    st.session_state.locations.pop()
                    st.rerun()

            for i, loc in enumerate(st.session_state.locations):
                with st.expander(f"📍 Location {i+1}", expanded=False):
                    a, b, c = st.columns(3)
                    with a:
                        loc["name"] = st.text_input("Location Name", value=loc.get("name", ""), key=f"loc_name_{i}")
                    with b:
                        loc["channel"] = st.text_input("Channel", value=loc.get("channel", ""), key=f"loc_channel_{i}")
                    with c:
                        loc["channel_group"] = st.text_input("Channel Group", value=loc.get("channel_group", ""), key=f"loc_channel_group_{i}")
                    loc["selling_channel"] = st.text_input("Selling Channel", value=loc.get("selling_channel", ""), key=f"loc_sell_{i}")
                    a, b, c = st.columns(3)
                    with a:
                        loc["source_location"] = st.checkbox("Source", value=loc.get("source_location", False), key=f"loc_src_{i}")
                    with b:
                        loc["inventory_location"] = st.checkbox("Inventory", value=loc.get("inventory_location", False), key=f"loc_inv_{i}")
                    with c:
                        loc["selling_location"] = st.checkbox("Selling", value=loc.get("selling_location", False), key=f"loc_sel_{i}")

        st.divider()
        if st.button("🔄 Generate Data", type="primary", use_container_width=True):
            valid = [l for l in st.session_state.locations if l.get("name", "").strip()]
            if not valid:
                st.error("Add at least one named location.")
            else:
                with st.spinner("Generating data..."):
                    st.session_state.data = generate_sample_data(valid)
                    st.success(f"✓ Data generated for {len(valid)} location(s)")
                    st.rerun()

        if st.session_state.data is not None:
            st.subheader("Preview")
            st.dataframe(st.session_state.data.head(10), use_container_width=True, hide_index=True)

    with view_tab:
        if st.session_state.data is None:
            st.warning("Generate data first in the Configuration tab.")
            return

        df = st.session_state.data
        attrs = [c for c in df.columns if c not in METRICS]

        with st.sidebar:
            st.header("⚙️ Controls")
            group_cols = st.multiselect(
                "Group by (rows)",
                options=[c for c in attrs if c != "Week"],
                default=["Channel", "Channel Group", "Selling Channel"]
            )
            st.session_state.group_by_rows = group_cols

            st.subheader("Filters")
            filt = {}
            for a in [c for c in attrs if c != "Week"]:
                vals = sorted(df[a].dropna().unique().tolist())
                sel = st.multiselect(f"{a}", options=vals, key=f"flt_{a}")
                if sel: filt[a] = sel
            st.session_state.filters = filt

            if st.button("Collapse All"):
                st.session_state.expanded_groups.clear()
                st.rerun()

        df_f = apply_filters(df, st.session_state.filters)
        df_wide = melt_pivot_weeks(df_f)
        week_cols = [c for c in df_wide.columns if c not in [*attrs, "Metric"]]

        st.subheader("Toolio-style Grid (click ▶ next to a value to expand)")
        render_grid(df_wide, st.session_state.group_by_rows, week_cols)

if __name__ == "__main__":
    main()
