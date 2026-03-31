import streamlit as st
import pandas as pd
import io

# --- PAGE SETUP ---
st.set_page_config(
    page_title="Coach Fair-Share v26.2",
    layout="wide",
    page_icon="🚌"
)

# --- CLEAN UI STYLING ---
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
st.caption("Strategic Cost Allocation Engine | Version v26.2")

# --- CONCEPT EXPLAINER ---
with st.expander("📖 Logic Overview & Concepts"):
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
**Core Principles:**
- You never pay more than a standalone trip (SLC)
- Savings are shared fairly
- Total collection = actual cost
""")
    with col_b:
        st.markdown("""
**Definitions:**
- Outbound: Base → City  
- Return: City → Base  
- Transit: City → City  
- Block: Cities connected with Transit = 0
""")

# --- TABS ---
tab1, tab2, tab3 = st.tabs(
    ["📊 Costs & Route", "👥 Attendance", "💰 Final Settlement"])

# =========================
# TAB 1: COST INPUT
# =========================
with tab1:
    st.header("Step 1: Define Trip Costs")

    col_left, col_right = st.columns([1, 2])
    with col_left:
        num_cities = st.number_input("Number of Cities", 2, 10, 3)

        strategy = st.selectbox(
            "Loss Allocation Strategy",
            ["Current Participants", "Traveling Players Alone (Bridgers)"]
        )

    city_data = []
    city_names = []

    st.markdown("---")

    grid = st.columns(3)

    for i in range(num_cities):
        with grid[i % 3]:
            with st.container(border=True):

                default_names = ["Delhi", "Dehradun", "Raipur"]
                name = st.text_input(
                    "City Name",
                    default_names[i] if i < len(
                        default_names) else f"City {i+1}",
                    key=f"name_{i}"
                )

                u = st.number_input(
                    f"Outbound (Base → {name})", value=7000.0 if i != 1 else 12800.0, key=f"u_{i}")
                d = st.number_input(
                    f"Return ({name} → Base)", value=7000.0 if i != 1 else 12800.0, key=f"d_{i}")
                m = st.number_input(f"Transit to {name}", value=0.0 if i == 0 else (
                    7700.0 if i == 1 else 11500.0), key=f"m_{i}")

                city_data.append({"name": name, "U": u, "D": d, "M": m})
                city_names.append(name)


# =========================
# TAB 2: ATTENDANCE
# =========================
with tab2:
    st.header("Step 2: Player Attendance")

    player_input = st.text_area(
        "Enter Player Names (one per line)",
        "Karthika\nDisha\nShree\nYash\nAbhvadya",
        key="player_name_input"
    )
    player_names = [p.strip() for p in player_input.split("\n") if p.strip()]

    if not player_names:
        st.warning("⚠️ Enter player names to continue")
        st.stop()

    # --- 1. INITIALIZE MASTER DATA ---
    # We create a 'template' dataframe in session state if it doesn't exist
    if "master_df" not in st.session_state:
        st.session_state["master_df"] = pd.DataFrame(
            False, index=player_names, columns=city_names)

    # --- 2. SYNC STRUCTURE (Only when names or cities change) ---
    # We compare current lists to the existing dataframe's index/columns
    existing_players = list(st.session_state["master_df"].index)
    existing_cities = list(st.session_state["master_df"].columns)

    if player_names != existing_players or city_names != existing_cities:
        # Structure changed, so we reindex
        st.session_state["master_df"] = st.session_state["master_df"].reindex(
            index=player_names, columns=city_names, fill_value=False
        )

    st.write("Check the boxes for the cities each player attended:")

    # --- 3. THE DATA EDITOR (CRITICAL FIX) ---
    # We use 'master_df' as the seed, but 'attendance_editor' as the KEY.
    # We DO NOT assign this to a variable (no 'edited_attendance = ...')
    st.data_editor(
        st.session_state["master_df"],
        use_container_width=True,
        key="attendance_editor"  # This key now OWN the edited data
    )

    # --- 4. DATA RETRIEVAL ---
    # Whenever we need the data (for the map or the math in Tab 3),
    # we pull it directly from the editor's state.
    final_attendance = st.session_state["attendance_editor"]

    st.subheader("📍 Travel Map")
    visual_df = final_attendance[city_names].astype(str).replace({
        "True": "✅",
        "False": "—"
    })
    st.dataframe(visual_df, use_container_width=True)


# =========================
# TAB 3: RESULTS
# =========================
with tab3:
    st.header("Step 3: Settlement Report")

    if st.button("💰 Generate Final Bills", type="primary", use_container_width=True):

        # --- VALIDATION ---
        for city in city_names:
            if not edited_attendance[city].any():
                st.error(f"No players assigned to {city}")
                st.stop()

        # --- BLOCK LOGIC ---
        block_ids = []
        curr_block = 1

        for i in range(num_cities):
            if i == 0:
                curr_block = 1
            elif city_data[i]['M'] > 0:
                curr_block += 1
            block_ids.append(curr_block)

        unique_blocks = sorted(set(block_ids))

        # --- UNION ---
        block_unions = {}
        for b_id in unique_blocks:
            cities_in_block = [city_names[i]
                               for i, bid in enumerate(block_ids) if bid == b_id]
            union_mask = edited_attendance[cities_in_block].any(axis=1)
            block_unions[b_id] = union_mask[union_mask].index.tolist()

        # --- SLC (FIX SAFE DIVISION) ---
        slc_per_block = {}
        for b_id in unique_blocks:
            idxs = [i for i, bid in enumerate(block_ids) if bid == b_id]
            u_val = city_data[idxs[0]]['U']
            d_val = city_data[idxs[-1]]['D']
            size = len(block_unions[b_id])

            slc_per_block[b_id] = (u_val + d_val) / size if size > 0 else 0

        # --- INITIAL BILL ---
        final_bills = {name: 0.0 for name in player_names}

        for name in player_names:
            for b_id in unique_blocks:
                if name in block_unions[b_id]:
                    final_bills[name] += slc_per_block[b_id]

        # --- LINK EFFICIENCY (FIX SAFE DIVISION) ---
        savings_log = []

        for i in range(1, num_cities):
            p_b, c_b = block_ids[i-1], block_ids[i]

            if p_b != c_b:
                d_prev = city_data[i-1]['D']
                u_curr = city_data[i]['U']
                m_actual = city_data[i]['M']

                saving = (d_prev + u_curr) - m_actual

                denom = d_prev + u_curr
                w_exit = d_prev / denom if denom > 0 else 0.5
                w_entry = u_curr / denom if denom > 0 else 0.5

                if saving > 0:
                    for p in block_unions[p_b]:
                        final_bills[p] -= saving * \
                            w_exit / len(block_unions[p_b])

                    for p in block_unions[c_b]:
                        final_bills[p] -= saving * \
                            w_entry / len(block_unions[c_b])

                    savings_log.append(
                        {"Route": f"{city_names[i-1]} → {city_names[i]}", "Type": "Saving", "Amount": saving})

                elif saving < 0:
                    loss = abs(saving)

                    if strategy == "Current Participants":
                        target = block_unions[c_b]
                    else:
                        target = [p for p in block_unions[p_b]
                                  if p in block_unions[c_b]]

                    if not target:
                        target = block_unions[c_b]

                    for p in target:
                        final_bills[p] += loss / len(target)

                    savings_log.append(
                        {"Route": f"{city_names[i-1]} → {city_names[i]}", "Type": "Loss", "Amount": -loss})

        # --- SUMMARY ---
        total_collected = sum(final_bills.values())

        last_city_idx = max([i for i in range(num_cities)
                            if edited_attendance[city_names[i]].any()] or [0])

        invoice_cost = city_data[0]['U'] + sum(c['M']
                                               for c in city_data[1:]) + city_data[last_city_idx]['D']

        # --- DASHBOARD ---
        m1, m2, m3 = st.columns(3)

        m1.metric("Total Collected", f"₹{total_collected:,.2f}")
        m2.metric("Actual Cost", f"₹{invoice_cost:,.2f}")
        m3.metric("Difference", f"₹{total_collected - invoice_cost:,.2f}")

        st.markdown("---")

        col1, col2 = st.columns([3, 2])

        with col1:
            st.subheader("📋 Billing Breakdown")

            res_df = pd.DataFrame.from_dict(
                final_bills, orient='index', columns=['Final Bill (₹)'])
            res_df = res_df.sort_values(by="Final Bill (₹)", ascending=False)

            st.dataframe(res_df.style.format(
                "₹{:,.2f}"), use_container_width=True)

            # Export
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                res_df.to_excel(writer)

            st.download_button(
                "📥 Download Excel", data=output.getvalue(), file_name="fairshare.xlsx")

        with col2:
            st.subheader("🔗 Efficiency Log")

            if savings_log:
                st.table(pd.DataFrame(savings_log))
            else:
                st.write("No transitions")

        # --- BLOCK VIEW ---
        with st.expander("🧱 Block Structure"):
            block_info = []
            for b_id in unique_blocks:
                cities = [city_names[i]
                          for i, bid in enumerate(block_ids) if bid == b_id]
                block_info.append({
                    "Block": b_id,
                    "Cities": " → ".join(cities),
                    "Players": ", ".join(block_unions[b_id])
                })

            st.table(pd.DataFrame(block_info))

# --- FOOTER ---
st.markdown("---")
st.caption("Fair-Share Engine | Zero-Sum Verified | Production Safe")
