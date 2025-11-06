import streamlit as st
from streamlit.components.v1 import html as st_html
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ---------- Page setup ----------
st.set_page_config(page_title="Toolio Lite - Merchandise Plan Demo", page_icon="📊", layout="wide")

# Initialize session state
for k, v in [
    ("data", None),
    ("group_by_rows", []),
    ("filters", {}),
    ("locations", []),
]:
    if k not in st.session_state:
        st.session_state[k] = v

METRICS = ["Gross Sales Units", "Receipts Units", "BOP Units", "On Order Units"]

# ---------- Data Generation ----------
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

                        # Multi-select location types
                        loc_types = loc.get("types", ["Selling"])

                        # initialize all to zero
                        r["Gross Sales Units"] = 0
                        r["Receipts Units"] = 0
                        r["BOP Units"] = 0
                        r["On Order Units"] = 0

                        if "Selling" in loc_types:
                            r["Gross Sales Units"] = np.random.randint(50, 500)

                        if "Source" in loc_types:
                            r["Receipts Units"] = np.random.randint(30, 400)
                            r["BOP Units"] = np.random.randint(100, 1000)
                            r["On Order Units"] = np.random.randint(0, 300)

                        if "Inventory" in loc_types:
                            # Inventory contributes BOP; if Source also selected, BOP will be overwritten anyway by another rand
                            r["BOP Units"] = np.random.randint(100, 1000)

                        rows.append(r)
    return pd.DataFrame(rows)

# ---------- Helpers ----------
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

# ---------- Grid (rendered via components.html so JS works) ----------
def build_grid_html(df_wide, group_cols, week_cols) -> str:
    def render_header():
        cols = ["Metric"] + group_cols + [f"Week {w}" for w in week_cols]
        return "<thead><tr>" + "".join(f"<th>{html_escape(c)}</th>" for c in cols) + "</tr></thead>"

    def week_sums(df):
        return [int(df[w].sum()) if w in df.columns else 0 for w in week_cols]

    def render_children(df_metric, path, level, rows):
        if level >= len(group_cols):
            return
        col = group_cols[level]
        for val, g in df_metric.groupby(col, dropna=False, sort=False):
            lbl = "(blank)" if val in [None, ""] else str(val)
            node_key = key_str(path + [val])
            nums = week_sums(g)

            tds = ["<td></td>"]
            for i, _ in enumerate(group_cols):
                if i == level:
                    indent = "&nbsp;" * (level * 4)
                    arrow_html = f"<span class='toolio-arrow' data-key='{node_key}' data-level='{level}'>▶</span>"
                    tds.append(f"<td>{indent}{arrow_html}{html_escape(lbl)}</td>")
                else:
                    tds.append("<td></td>")
            tds += [f"<td class='toolio-num'>{v:,}</td>" for v in nums]
            row_html = f"<tr class='child-row hidden-row' data-key='{node_key}' data-parent='{key_str(path)}'>{''.join(tds)}</tr>"
            rows.append(row_html)
            # Recurse
            render_children(g, path + [val], level + 1, rows)

    rows = []
    # Build per-metric top rows (start collapsed)
    for metric, df_m in df_wide.groupby("Metric"):
        metric_key = key_str([metric])
        nums = week_sums(df_m)
        arrow_html = f"<span class='toolio-arrow' data-key='{metric_key}' data-level='-1'>▶</span>"
        tds = [f"<td class='toolio-metric'>{arrow_html}{html_escape(metric)}</td>"]
        tds += ["<td class='toolio-metric'></td>" for _ in group_cols]
        tds += [f"<td class='toolio-metric toolio-num'>{v:,}</td>" for v in nums]
        rows.append(f"<tr data-key='{metric_key}' class='metric-row'>{''.join(tds)}</tr>")
        # Children rows
        render_children(df_m, [metric], 0, rows)

    # CSS + JS inside the component (runs normally)
    css = """
    <style>
      .toolio-wrap { width:100%; overflow-x:auto; }
      .toolio-table { border-collapse:collapse; width:100%; table-layout:fixed; border:1px solid #e0e0e0; font-size:0.95rem; }
      .toolio-table th, .toolio-table td { border:1px solid #e0e0e0; padding:6px 10px; vertical-align:middle; }
      .toolio-table th { background:#fafafa; font-weight:700; text-align:left; white-space:nowrap; }
      .toolio-num { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
      .toolio-metric { background:#f9f9f9; font-weight:700; }
      .toolio-arrow { cursor:pointer; color:#333; font-weight:bold; margin-right:4px; }
      .toolio-arrow:hover { color:#000; }
      .hidden-row { display:none; }
      body { margin:0; font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,'Helvetica Neue',Arial; }
    </style>
    """

    js = """
    <script>
      // Attach after DOM ready
      window.addEventListener('DOMContentLoaded', function() {
        function toggle(key, makeExpand) {
          const btns = document.querySelectorAll('.toolio-arrow[data-key="' + key + '"]');
          btns.forEach(b => b.textContent = makeExpand ? '▼' : '▶');
          const rows = document.querySelectorAll('[data-parent="' + key + '"]');
          rows.forEach(r => {
            if (makeExpand) {
              r.classList.remove('hidden-row');
            } else {
              // Collapse subtree recursively
              r.classList.add('hidden-row');
              const childKey = r.getAttribute('data-key');
              if (childKey) {
                toggle(childKey, false);
              }
            }
          });
        }

        document.querySelectorAll('.toolio-arrow').forEach(btn => {
          btn.addEventListener('click', (e) => {
            const key = btn.dataset.key;
            const expanded = btn.textContent === '▼';
            toggle(key, !expanded);
          });
        });
      });
    </script>
    """

    html = f"""
    {css}
    <div class='toolio-wrap'>
      <table class='toolio-table'>
        {render_header()}
        <tbody>
          {''.join(rows)}
        </tbody>
      </table>
    </div>
    {js}
    """
    return html

# ---------- Main App ----------
def main():
    st.title("📊 Toolio Lite - Merchandise Plan Demo")
    st.caption("Utilize this demo to show how locations would looks like in Toolio. This is best used to show On Order and Receipt considerations and how to organize virtual warehouses.")

    config_tab, view_tab = st.tabs(["⚙️ Configuration", "📊 Data View"])

    with config_tab:
        st.header("Location Configuration")
        with st.expander("📍 Configure Locations", expanded=False):
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

                    loc["types"] = st.multiselect(
                        "Location Type(s)",
                        options=["Selling", "Source", "Inventory"],
                        default=loc.get("types", ["Selling"]),
                        key=f"loc_types_{i}",
                    )

        st.divider()
        if st.button("🔄 Generate Data", type="primary", use_container_width=True):
            valid = [l for l in st.session_state.locations if l.get("name", "").strip()]
            if not valid:
                st.error("Add at least one named location.")
            else:
                st.session_state.data = generate_sample_data(valid)
                st.success(f"✓ Data generated for {len(valid)} location(s)")
                st.rerun()

    with view_tab:
        if st.session_state.data is None:
            st.warning("Generate data first.")
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
                if sel:
                    filt[a] = sel
            st.session_state.filters = filt

        df_f = apply_filters(df, st.session_state.filters)
        df_wide = melt_pivot_weeks(df_f)
        week_cols = [c for c in df_wide.columns if c not in [*attrs, "Metric"]]

        # Render grid via components.html so the JS runs
        grid_html = build_grid_html(df_wide, st.session_state.group_by_rows, week_cols)
        # Height heuristic: 120px header + ~28px per row (collapsed shows only metrics)
        st_html(grid_html, height=600, scrolling=True)

if __name__ == "__main__":
    main()
