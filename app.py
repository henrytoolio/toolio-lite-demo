import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Toolio Lite Demo App (Weeks in columns, true hierarchical expand/collapse, metrics always visible)

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
# Sample Data Generation
# -----------------------------
def generate_sample_data(locations):
    np.random.seed(42)
    start_date = datetime.now().replace(day=1)
    weeks = [(start_date + timedelta(weeks=i)).strftime("%Y-%m-%d") for i in range(3)]

    divisions = ["Mens", "Womens"]
    departments = ["Bottoms", "Tops"]
    classes = {"Tops": ["Long Sleeve", "Short Sleeve"], "Bottoms": ["Short Leg", "Long Leg"]}

    rows = []
    for week in weeks:
        for loc in locations:
            for div in divisions:
                for dept in departments:
                    for cls in classes[dept]:
                        rows.append(
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
    return pd.DataFrame(rows)

# -----------------------------
# Helpers
# -----------------------------
METRICS = ["Gross Sales Units", "Receipts Units", "BOP Units", "On Order Units"]


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    out = df.copy()
    for col, vals in filters.items():
        if vals:
            out = out[out[col].isin(vals)]
    return out


def key_tuple_to_str(parts) -> str:
    if isinstance(parts, tuple):
        return "|".join(map(str, parts))
    return str(parts)


def pivot_weeks(df: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    """Return df with wide columns per metric per week, like Toolio (Week across columns)."""
    # Ensure Week is string/categorical for stable column ordering
    df = df.copy()
    df["Week"] = df["Week"].astype(str)

    # Build a wide table for each metric and merge
    # Exclude both METRICS and "Week" from index since Week is used as columns
    index_cols = [c for c in df.columns if c not in METRICS and c != "Week"]
    
    wide = None
    for m in metrics:
        if m not in df.columns:
            continue
        pv = pd.pivot_table(df, values=m, index=index_cols, columns=["Week"], aggfunc="sum", fill_value=0)
        # Flatten columns: Metric | Week
        pv.columns = [f"{m} | {w}" for w in pv.columns]
        pv = pv.reset_index()
        # Merge on the index columns (excluding Week and metrics)
        merge_cols = [c for c in pv.columns if c in index_cols]
        wide = pv if wide is None else pd.merge(wide, pv, on=merge_cols, how="outer")
    return wide if wide is not None else df


def sum_week_columns(df: pd.DataFrame, prefix: str) -> dict:
    """Sum all columns that start with metric prefix (e.g., 'Gross Sales Units | ')."""
    cols = [c for c in df.columns if c.startswith(prefix + " | ")]
    return {c: df[c].sum() for c in cols}


def build_expandable_rows(df_wide: pd.DataFrame, row_attrs: list[str], level: int, parent_key: tuple, rows: list[dict]):
    """Recursive builder for hierarchical expand/collapse with Week-in-columns totals.
    - df_wide: already pivoted so Week columns are like 'Metric | 2025-11-03'
    - row_attrs: grouping hierarchy (only attributes the user selected)
    - level: current depth
    - parent_key: tuple of keys up to this level
    - rows: accumulator list of dict rows for display
    """
    if level >= len(row_attrs):
        return

    attr = row_attrs[level]
    groups = df_wide.groupby(attr, dropna=False)

    for value, gdf in groups:
        key_tuple = parent_key + (value,)
        key_str = key_tuple_to_str(key_tuple)

        # Determine expansion state
        expanded = key_str in st.session_state.expanded_groups

        # Header (roll-up) row for this group
        header = {a: "" for a in row_attrs}
        header[attr] = ("  " * level) + (str(value) if value is not None else "(blank)")
        header["_expand_indicator"] = "▼" if expanded else "▶"

        # Add all week columns (for all metrics) as rolled-up sums
        for m in METRICS:
            totals = sum_week_columns(gdf, m)
            header.update(totals)
        rows.append(header)

        # If expanded, either go deeper or (at leaf) render no extra attribute columns (metrics are already visible)
        if expanded:
            if level + 1 < len(row_attrs):
                build_expandable_rows(gdf, row_attrs, level + 1, key_tuple, rows)
            else:
                # Leaf level: show a detail breakdown at the same attribute (optional). We can skip to keep it clean.
                # If you want leaf records (e.g., by Location when not grouped), uncomment below to show child lines.
                pass

# -----------------------------
# UI & App
# -----------------------------

def main():
    st.title("📊 Toolio Lite - Merchandise Plan Demo")
    st.markdown("Weeks across columns • hierarchical expand/collapse on rows • metrics always visible")

    config_tab, view_tab = st.tabs(["⚙️ Configuration", "📊 Data View"])

    # ---------------- Configuration ----------------
    with config_tab:
        st.header("Location Configuration")
        st.markdown("**Configure up to 10 locations with their properties**")

        if not st.session_state.locations:
            st.session_state.locations = [{} for _ in range(5)]

        # Controls to add/remove locations
        c_add, c_remove = st.columns(2)
        with c_add:
            if st.button("➕ Add Location", disabled=len(st.session_state.locations) >= 10):
                st.session_state.locations.append({})
                st.rerun()
        with c_remove:
            if st.button("➖ Remove Last Location", disabled=len(st.session_state.locations) <= 1):
                st.session_state.locations.pop()
                st.rerun()

        st.divider()

        # Per-location inputs
        for i, loc in enumerate(st.session_state.locations):
            with st.expander(f"📍 Location {i+1}", expanded=i < 3):
                c1, c2, c3 = st.columns(3)
                loc["name"] = c1.text_input("Location Name", value=loc.get("name", ""), key=f"name_{i}")
                loc["channel"] = c2.text_input("Channel", value=loc.get("channel", ""), key=f"channel_{i}")
                loc["channel_group"] = c3.text_input("Channel Group", value=loc.get("channel_group", ""), key=f"channel_group_{i}")
                loc["selling_channel"] = st.text_input("Selling Channel", value=loc.get("selling_channel", ""), key=f"selling_channel_{i}")

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
            valids = [l for l in st.session_state.locations if l.get("name", "").strip()]
            if not valids:
                st.error("⚠️ Please add at least one location with a name before generating data.")
            else:
                with st.spinner("Generating data..."):
                    st.session_state.data = generate_sample_data(valids)
                    st.session_state.filtered_data = st.session_state.data.copy()
                    st.success("✓ Data generated successfully!")
                    st.rerun()

        if st.session_state.data is not None:
            st.subheader("📊 Data Preview")
            st.dataframe(st.session_state.data.head(10), use_container_width=True, hide_index=True)

    # ---------------- Data View ----------------
    with view_tab:
        if st.session_state.data is None:
            st.warning("⚠️ Generate data first in the Configuration tab.")
            st.info("💡 Click on the '⚙️ Configuration' tab above to set up your locations.")
            return

        df = st.session_state.data
        all_attributes = [c for c in df.columns if c not in METRICS]

        # Sidebar controls
        with st.sidebar:
            st.header("⚙️ Controls")
            st.caption("Pick ONLY the attributes you want in rows — nothing else will be shown.")
            row_attrs = st.multiselect(
                "Group by Rows",
                options=[c for c in all_attributes if c != "Week"],
                default=["Channel", "Channel Group"],
                help="Only selected attributes appear in the table."
            )

            # Filter controls (optional)
            st.divider()
            st.subheader("🔍 Filters")
            filters = {}
            for a in [c for c in all_attributes if c != "Week"]:
                vals = sorted(df[a].dropna().unique().tolist())
                picked = st.multiselect(f"Filter by {a}", options=vals, key=f"flt_{a}")
                if picked:
                    filters[a] = picked

            st.session_state.group_by_rows = row_attrs
            st.session_state.filters = filters

            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Expand All"):
                    tmp = pivot_weeks(apply_filters(df, filters), METRICS)
                    if row_attrs:
                        groups = tmp.groupby(row_attrs)
                        st.session_state.expanded_groups = {key_tuple_to_str(k if isinstance(k, tuple) else (k,)) for k, _ in groups}
                    st.rerun()
            with c2:
                if st.button("Collapse All"):
                    st.session_state.expanded_groups.clear()
                    st.rerun()

        # Apply filters
        df_filtered = apply_filters(df, st.session_state.filters)

        # Pivot weeks into columns (Toolio-style)
        df_wide = pivot_weeks(df_filtered, METRICS)

        # Build hierarchical, expandable rows that include ONLY selected attributes
        display_rows: list[dict] = []
        if row_attrs:
            build_expandable_rows(df_wide, row_attrs, level=0, parent_key=tuple(), rows=display_rows)
        else:
            # No row grouping: show a single roll-up line
            rollup = {"_expand_indicator": ""}
            for m in METRICS:
                rollup.update(sum_week_columns(df_wide, m))
            display_rows.append(rollup)

        # Prepare final DataFrame for display
        if display_rows:
            display_df = pd.DataFrame(display_rows)
        else:
            display_df = pd.DataFrame()

        # Order columns: expand indicator, row attributes, then all metric-week columns (sorted by week within metric)
        mw_cols = [c for c in df_wide.columns if any(c.startswith(m + " | ") for m in METRICS)]
        # Sort week columns by metric then by week label
        def mw_sort_key(col: str):
            m, _, w = col.partition(" | ")
            return (METRICS.index(m) if m in METRICS else 99, w)
        mw_cols_sorted = sorted(mw_cols, key=mw_sort_key)

        ordered_cols = ["_expand_indicator"] + row_attrs + mw_cols_sorted
        for col in ordered_cols:
            if col not in display_df.columns:
                display_df[col] = ""
        display_df = display_df[ordered_cols]

        # Expand/Collapse buttons row (for current top-level groups)
        st.subheader("🔽 Expand / Collapse")
        if row_attrs:
            top = row_attrs[0]
            tops = df_wide[top].drop_duplicates().tolist()
            cols = st.columns(min(4, max(1, len(tops))))
            for i, v in enumerate(tops):
                key = key_tuple_to_str((v,))
                expanded = key in st.session_state.expanded_groups
                label = str(v)
                with cols[i % len(cols)]:
                    if st.button(f"{'▼' if expanded else '▶'} {label[:24]}", key=f"btn_top_{i}"):
                        if expanded:
                            st.session_state.expanded_groups.discard(key)
                        else:
                            st.session_state.expanded_groups.add(key)
                        st.rerun()

        st.divider()
        st.subheader("📈 Data Table (Weeks in Columns)")
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        st.caption("Metrics are always visible. Only the attributes you bring into Rows are shown. Weeks are in columns like Toolio.")

        # Instructions
        st.divider()
        with st.expander("ℹ️ How to Use This Demo"):
            st.markdown(
                """
                ### Configuration Tab:
                1. **Locations**: Add up to 10 locations with:
                   - Location Name, Channel, Channel Group, Selling Channel
                2. **Attributes** (fixed for the sample data):
                   - Division (Mens, Womens)
                   - Department (Bottoms, Tops)
                   - Class (Long/Short Sleeve for Tops, Long/Short Leg for Bottoms)
                3. **Generate Data**: Click to create sample data

                ### Data View Tab:
                1. **Group By Rows**: Choose only the attributes you want to see (e.g., Channel → Channel Group). Others are hidden.
                2. **Weeks as Columns**: Time is always across columns. Each metric displays values for each week.
                3. **Expand/Collapse**: Click triangles to roll up to higher levels or expand to see child groups.
                4. **Metrics**: Always visible on every level. Collapsing a parent keeps rolled‑up metrics visible.

                ### Example Workflow:
                1. Configure 3–5 locations with different channels
                2. Generate data
                3. Group by Rows: `Channel`, `Channel Group`
                4. Use **Expand/Collapse** to roll up to Channel, then expand to see Channel Group breakdown
                5. Observe each metric by **Week** across the top
                """
            )


if __name__ == "__main__":
    main()

