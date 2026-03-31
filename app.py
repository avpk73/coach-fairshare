import streamlit as st
import pandas as pd
import io

# --- PAGE SETUP ---
st.set_page_config(page_title="Coach Fair-Share v26.1",
                   layout="wide", page_icon="🚌")

st.title("🚌 Coach Travel Fair-Share Calculator")
st.caption("Version v26.1")

st.info("""
This tool calculates fair sharing of coach travel costs across multiple tournaments.

🧭 Concepts:
• Outbound: Base → City  
• Return: City → Base  
• Transit: Cost between cities  

💡 If Transit = 0 → treated as continuous travel (same group/block)
""")

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📊 Costs", "👥 Attendance", "💰 Results"])

# =========================
# TAB 1: COST INPUT
# =========================
with tab1:
    st.header("Step 1: Trip Costs")

    num_cities = st.slider("Number of Cities/Tournaments", 2, 10, 3)

    city_data = []
    city_names = []

    for i in range(num_cities):
        with st.expander(f"City {i+1}", expanded=(i < 3)):
            default_names = ["Delhi", "Dehradun", "Raipur"]
            name = st.text_input(
                "City Name",
                default_names[i] if i < len(default_names) else f"City {i+1}",
                key=f"name_{i}"
            )

            col1, col2, col3 = st.columns(3)

            u = col1.number_input(
                f"Outbound (Base → {name})", value=7000.0 if i != 1 else 12800.0, key=f"u_{i}")
            d = col2.number_input(
                f"Return ({name} → Base)", value=7000.0 if i != 1 else 12800.0, key=f"d_{i}")
            m = col3.number_input(f"Transit to {name}", value=0.0 if i == 0 else (
                7700.0 if i == 1 else 11500.0), key=f"m_{i}")

            city_data.append({"name": name, "U": u, "D": d, "M": m})
            city_names.append(name)

    strategy = st.selectbox(
        "Loss Allocation Strategy",
        ["Current Participants", "Traveling Players Alone (Bridgers)"]
    )

# =========================
# TAB 2: ATTENDANCE
# =========================
with tab2:
    st.header("Step 2: Player Attendance")

    player_input = st.text_area(
        "Enter Player Names (one per line)",
        "Karthika\nDisha\nShree\nYash\nAbhvadya"
    )

    player_names = [p.strip() for p in player_input.split("\n") if p.strip()]

    if not player_names:
        st.warning("Please enter at least one player")

    if len(set(player_names)) != len(player_names):
        st.error("Duplicate player names detected")

    attendance_df = pd.DataFrame(False, index=player_names, columns=city_names)

    edited_attendance = st.data_editor(attendance_df, use_container_width=True)

    st.subheader("📍 Travel Map")
    visual_df = edited_attendance.astype(
        str).replace({"True": "✅", "False": "—"})
    st.dataframe(visual_df, use_container_width=True)

# =========================
# TAB 3: RESULTS
# =========================
with tab3:
    st.header("Step 3: Results")

    if st.button("💰 Calculate Fair Share", type="primary"):

        if not player_names:
            st.error("No players defined")
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
            cities_in_b = [city_names[i]
                           for i, bid in enumerate(block_ids) if bid == b_id]
            union_mask = edited_attendance[cities_in_b].any(axis=1)
            block_unions[b_id] = union_mask[union_mask].index.tolist()

        # --- SLC ---
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

        # --- LINK EFFICIENCY ---
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
                        {"Link": f"{city_names[i-1]} → {city_names[i]}", "Type": "Saving", "Amount": saving})

                elif saving < 0:
                    loss = abs(saving)

                    if strategy == "Current Participants":
                        for p in block_unions[c_b]:
                            final_bills[p] += loss / len(block_unions[c_b])
                    else:
                        bridgers = [p for p in block_unions[p_b]
                                    if p in block_unions[c_b]]
                        if bridgers:
                            for p in bridgers:
                                final_bills[p] += loss / len(bridgers)
                        else:
                            for p in block_unions[c_b]:
                                final_bills[p] += loss / len(block_unions[c_b])

                    savings_log.append(
                        {"Link": f"{city_names[i-1]} → {city_names[i]}", "Type": "Loss", "Amount": -loss})

        # --- RESULTS DISPLAY ---
        res_df = pd.DataFrame.from_dict(
            final_bills, orient='index', columns=['Final Bill (₹)'])
        res_df = res_df.sort_values(by="Final Bill (₹)", ascending=False)

        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("💰 Player Costs")
            st.dataframe(res_df.style.format(
                "₹{:,.2f}"), use_container_width=True)

            # Excel export
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                res_df.to_excel(writer)

            st.download_button(
                "📥 Download Excel",
                data=output.getvalue(),
                file_name="fair_share.xlsx"
            )

        with col2:
            st.subheader("📊 Summary")

            total_collected = sum(final_bills.values())

            last_city_idx = max(
                [i for i in range(num_cities) if edited_attendance[city_names[i]].any()] or [0])

            actual_cost = city_data[0]['U'] + sum(c['M']
                                                  for c in city_data[1:]) + city_data[last_city_idx]['D']

            st.metric("Total Collected", f"₹{total_collected:,.0f}")
            st.metric("Actual Cost", f"₹{actual_cost:,.0f}")

            diff = total_collected - actual_cost
            if abs(diff) < 1:
                st.success("Balanced ✅")
            else:
                st.error(f"Mismatch ₹{diff:.2f}")

        # --- BLOCK VIEW ---
        st.subheader("🧱 Travel Blocks")

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

        # --- SAVINGS ---
        if savings_log:
            st.subheader("🔗 Savings / Loss")
            st.dataframe(pd.DataFrame(savings_log))

# --- FOOTER ---
with st.expander("🔍 How this works"):
    st.markdown("""
Each player pays:
1. Their share of block travel  
2. Minus savings from efficient routing  
3. Plus any additional cost from inefficient transitions  

✔ Ensures fairness  
✔ Ensures full cost recovery  
✔ No overcharging
""")
