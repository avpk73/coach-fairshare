import streamlit as st
import pandas as pd
import io

# --- PAGE SETUP ---
st.set_page_config(
    page_title="Coach Fair-Share v26.3",
    layout="wide",
    page_icon="🚌"
)

# --- STYLING ---
st.markdown("""
<style>
.main { background-color: #f8f9fa; }
.stMetric {
    background-color: #ffffff;
    padding: 15px;
    border-radius: 10px;
    border: 1px solid #e0e0e0;
}
</style>
""", unsafe_allow_html=True)

st.title("🚌 Coach Travel Fair-Share Calculator")
st.caption("Strategic Cost Allocation Engine | Version v26.3 Stable")

# --- EXPLAINER ---
with st.expander("📖 Logic Overview"):
    st.markdown("""
- **SLC (Standalone Logical Cost):** Baseline cost if a block was a private trip.
- **Efficiency Credits:** Shared when transit is cheaper than sending the bus back to base.
- **Loss Surcharges:** Allocated when transit cost exceeds standalone travel costs.
- **Zero-Sum Integrity:** Total collected always equals the actual coach invoice.
""")

# --- TABS ---
tab1, tab2, tab3 = st.tabs(
    ["📊 Costs & Route", "👥 Attendance", "💰 Final Settlement"])

# =========================
# TAB 1: COST INPUT
# =========================
with tab1:
    st.header("Step 1: Define Trip Costs")

    col1, col2 = st.columns([1, 2])

    with col1:
        num_cities = st.number_input("Number of Cities", 2, 10, 3)
        strategy = st.selectbox(
            "Loss Allocation Strategy",
            ["Current Participants", "Traveling Players Alone (Bridgers)"],
            help="If a trip is inefficient, who pays for the extra cost?"
        )

    city_data = []
    city_names = []

    st.markdown("---")
    grid = st.columns(3)

    for i in range(num_cities):
        with grid[i % 3]:
            with st.container(border=True):
                # Standardized naming for logic reliability
                default_names = ["Delhi", "Dehradun",
                                 "Raipur", "City 4", "City 5"]
                name = st.text_input(
                    "City Name",
                    default_names[i] if i < len(
                        default_names) else f"City {i+1}",
                    key=f"name_{i}"
                )

                u = st.number_input(
                    f"Outbound → {name}", value=0.0, step=100.0, key=f"u_{i}")
                d = st.number_input(
                    f"Return ← {name}", value=0.0, step=100.0, key=f"d_{i}")
                m = st.number_input(
                    f"Transit to {name}", value=0.0, step=100.0, key=f"m_{i}")

                city_data.append({"name": name, "U": u, "D": d, "M": m})
                city_names.append(name)

# =========================
# TAB 2: ATTENDANCE (STABLE)
# =========================
with tab2:
    st.header("Step 2: Player Attendance")

    player_input = st.text_area(
        "Enter Player Names (one per line)",
        "Karthika\nDisha\nShree\nYash\nAbhvadya",
        key="player_input"
    )
    player_names = [p.strip() for p in player_input.split("\n") if p.strip()]

    if not player_names:
        st.warning("Please enter at least one player to continue.")
        st.stop()

    # --- SESSION STATE STABILITY ---
    if "master_df" not in st.session_state:
        st.session_state["master_df"] = pd.DataFrame(
            False, index=player_names, columns=city_names)

    # Reindex if players or cities change to prevent crashes
    if list(st.session_state["master_df"].index) != player_names or list(st.session_state["master_df"].columns) != city_names:
        st.session_state["master_df"] = st.session_state["master_df"].reindex(
            index=player_names, columns=city_names, fill_value=False
        )

    # --- QUICK ACTIONS ---
    colA, colB, colC = st.columns([1, 1, 2])
    with colA:
        if st.button("✅ Select All (City 1)"):
            st.session_state["master_df"][city_names[0]] = True
            st.rerun()
    with colB:
        if st.button("🗑️ Clear All"):
            st.session_state["master_df"][:] = False
            st.rerun()

    st.write("Mark checkboxes for the tournaments each player attended:")

    # The Editor
    edited = st.data_editor(
        st.session_state["master_df"],
        use_container_width=True,
        key="attendance_editor"
    )

    # Sync back to master
    st.session_state["master_df"] = edited
    ordered = edited[city_names]
    st.session_state["ready_attendance"] = ordered

    # --- VISUAL MAP ---
    with st.expander("📍 Visual Travel Map", expanded=True):
        # Using map instead of applymap for Pandas 2.0+ compatibility
        visual = ordered.map(lambda x: "✅" if x else "")
        st.dataframe(visual, use_container_width=True)

# =========================
# TAB 3: RESULTS
# =========================
with tab3:
    st.header("Step 3: Settlement Report")

    if "ready_attendance" not in st.session_state:
        st.info("👋 Please go to the Attendance tab to verify player rosters first.")
        st.stop()

    attendance = st.session_state["ready_attendance"]

    if st.button("💰 Calculate Fair Share", type="primary", use_container_width=True):

        # --- VALIDATION ---
        for c in city_names:
            if not attendance[c].any():
                st.error(
                    f"🛑 Error: No players assigned to **{c}**. A coach trip requires passengers.")
                st.stop()

        # --- BLOCKS (M=0 logic) ---
        block_ids = []
        curr = 1
        for i in range(num_cities):
            if i > 0 and city_data[i]["M"] > 0:
                curr += 1
            block_ids.append(curr)
        blocks = sorted(set(block_ids))

        # --- UNIONS (Unique players per block) ---
        unions = {}
        for b in blocks:
            cities_in_b = [city_names[i]
                           for i, bid in enumerate(block_ids) if bid == b]
            mask = attendance[cities_in_b].any(axis=1)
            unions[b] = mask[mask].index.tolist()

        # --- SLC (Standalone Logical Cost) ---
        slc = {}
        for b in blocks:
            idxs = [i for i, bid in enumerate(block_ids) if bid == b]
            u_val = city_data[idxs[0]]["U"]
            d_val = city_data[idxs[-1]]["D"]
            size = len(unions[b])
            slc[b] = (u_val + d_val) / size if size > 0 else 0

        # --- INITIAL BILL (SLC Sum) ---
        bills = {p: 0.0 for p in player_names}
        for p in player_names:
            for b in blocks:
                if p in unions[b]:
                    bills[p] += slc[b]

        # --- LINK EFFICIENCY (Credits/Losses) ---
        log = []
        for i in range(1, num_cities):
            pb, cb = block_ids[i-1], block_ids[i]

            if pb != cb:
                d_val = city_data[i-1]["D"]
                u_val = city_data[i]["U"]
                m_val = city_data[i]["M"]

                diff = (d_val + u_val) - m_val
                denom = d_val + u_val
                w1 = d_val/denom if denom > 0 else 0.5
                w2 = u_val/denom if denom > 0 else 0.5

                if diff > 0:
                    # Distribute Savings
                    for p in unions[pb]:
                        bills[p] -= (diff * w1 / len(unions[pb]))
                    for p in unions[cb]:
                        bills[p] -= (diff * w2 / len(unions[cb]))
                    log.append(
                        {"Route": f"{city_names[i-1]} → {city_names[i]}", "Status": "Saving (Credit)", "Amount": diff})

                elif diff < 0:
                    # Distribute Losses (Using Strategy Selection)
                    loss = abs(diff)
                    bridgers = [p for p in unions[pb] if p in unions[cb]]

                    # LOGIC FIX: Apply strategy from Tab 1
                    if strategy == "Traveling Players Alone (Bridgers)" and bridgers:
                        target = bridgers
                    else:
                        target = unions[cb]  # Fallback to current participants

                    for p in target:
                        bills[p] += (loss / len(target))
                    log.append(
                        {"Route": f"{city_names[i-1]} → {city_names[i]}", "Status": "Loss (Surcharge)", "Amount": -loss})

        # --- AUDIT & DASHBOARD ---
        total = sum(bills.values())
        last_idx = max([i for i in range(num_cities)
                       if attendance[city_names[i]].any()] or [0])
        actual = city_data[0]["U"] + sum(c["M"]
                                         for c in city_data[1:]) + city_data[last_idx]["D"]

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Collected", f"₹{total:,.2f}")
        m2.metric("Actual Cost", f"₹{actual:,.2f}")

        diff_audit = total - actual
        m3.metric("Audit Balance", f"₹{diff_audit:,.2f}", delta="Balanced" if abs(
            diff_audit) < 1 else "Error")

        st.markdown("---")
        col_res1, col_res2 = st.columns([3, 2])

        with col_res1:
            st.subheader("📋 Billing Breakdown")
            df_final = pd.DataFrame.from_dict(bills, orient='index', columns=[
                                              "Final Bill (₹)"]).sort_values("Final Bill (₹)", ascending=False)
            st.dataframe(
                df_final.style.format("₹{:,.2f}").background_gradient(
                    cmap="Blues", axis=0),
                use_container_width=True
            )

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_final.to_excel(writer, sheet_name='FinalBills')
            st.download_button("📥 Download Official Report", data=output.getvalue(
            ), file_name="coach_fairshare_v26.xlsx")

        with col_res2:
            st.subheader("🚛 Transit Log")
            if log:
                st.table(pd.DataFrame(log))
            else:
                st.info("No city-to-city transit processed.")

        with st.expander("🛠 Structural Details (Blocks)"):
            b_info = []
            for b in blocks:
                c_in_b = [city_names[i]
                          for i, bid in enumerate(block_ids) if bid == b]
                b_info.append({"Block": b, "Route": " ⮕ ".join(
                    c_in_b), "Union Size": len(unions[b])})
            st.table(pd.DataFrame(b_info))

# --- FOOTER ---
st.markdown("---")
st.caption("Fair-Share Engine | Zero-Sum Integrity Verified | v26.3 Build")
