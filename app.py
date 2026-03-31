import streamlit as st
import pandas as pd
import io

# --- PAGE SETUP ---
st.set_page_config(page_title="Coach Fair-Share v26.0",
                   layout="wide", page_icon="🚌")

st.title("🚌 Coach Travel Fair-Share Calculator")
st.markdown("""
This calculator implements the **v26.0 Transitive Group Cost Model**. 
It ensures no player pays more than their Standalone Logical Cost while sharing efficiency savings from link-bridging.
""")
st.markdown("---")

# --- 1. INPUT SECTION (SIDEBAR) ---
st.sidebar.header("Step 1: Trip Costs")
num_cities = st.sidebar.slider("Number of Cities/Tournaments", 2, 10, 3)

city_data = []
for i in range(num_cities):
    with st.sidebar.expander(f"City {i+1} Details", expanded=(i < 3)):
        default_names = ["Delhi", "Dehradun", "Raipur", "City 4", "City 5"]
        name = st.text_input(f"City {i+1} Name", default_names[i] if i < len(
            default_names) else f"City {i+1}", key=f"name_{i}")

        # v26.0 Default Logic
        u_def = 7000.0 if i != 1 else 12800.0
        d_def = 7000.0 if i != 1 else 12800.0
        m_def = 0.0 if i == 0 else (7700.0 if i == 1 else 11500.0)

        col_u, col_d, col_m = st.columns(3)
        u_cost = col_u.number_input(
            f"Base->{name} (U)", value=u_def, key=f"u_{i}")
        d_cost = col_d.number_input(
            f"{name}->Base (D)", value=d_def, key=f"d_{i}")
        m_cost = col_m.number_input(
            f"Transit to {name} (M)", value=m_def, key=f"m_{i}")

        city_data.append({"name": name, "U": u_cost, "D": d_cost, "M": m_cost})

st.sidebar.header("Step 2: Configuration")
strategy = st.sidebar.selectbox(
    "Loss Allocation Strategy",
    ["Current Participants", "Traveling Players Alone (Bridgers)"],
    help="If a transit costs more than sending the bus back to base (Saving < 0), who pays the difference?"
)

# --- 2. ATTENDANCE SECTION ---
st.header("Step 2: Attendance Matrix")
st.info("Check the box if the player attended the tournament in that city. The engine will automatically calculate 'Block Unions'.")

player_input = st.text_area(
    "Enter Player Names (one per line)", "Karthika\nDisha\nShree\nYash\nAbhvadya")
player_names = [p.strip() for p in player_input.split("\n") if p.strip()]

city_names = [c['name'] for c in city_data]
attendance_df = pd.DataFrame(False, index=player_names, columns=city_names)

# Pre-fill sample data for convenience
if "Disha" in attendance_df.index:
    attendance_df.loc["Disha", :] = True
if "Shree" in attendance_df.index:
    attendance_df.loc["Shree", city_names[0]] = True
    if num_cities > 1:
        attendance_df.loc["Shree", city_names[1]] = True

edited_attendance = st.data_editor(attendance_df, use_container_width=True)

# --- 3. THE CALCULATION ENGINE ---
if st.button("🚀 Calculate Final Bills", type="primary"):
    # A. Block Logic (Merge if Transit M = 0)
    block_ids = []
    curr_block = 0
    for i in range(num_cities):
        # Start a new block if M > 0 or if it's the first city
        if i == 0:
            curr_block = 1
        elif city_data[i]['M'] > 0:
            curr_block += 1
        block_ids.append(curr_block)

    # B. Union Membership
    unique_blocks = sorted(list(set(block_ids)))
    block_unions = {}
    for b_id in unique_blocks:
        cities_in_b = [city_names[i]
                       for i, bid in enumerate(block_ids) if bid == b_id]
        # A player is in the block union if they attended ANY city in that block
        union_mask = edited_attendance[cities_in_b].any(axis=1)
        block_unions[b_id] = union_mask[union_mask == True].index.tolist()

    # C. SLC Calculation
    slc_per_block = {}
    for b_id in unique_blocks:
        idxs = [i for i, bid in enumerate(block_ids) if bid == b_id]
        u_val = city_data[idxs[0]]['U']
        d_val = city_data[idxs[-1]]['D']
        size = len(block_unions[b_id])
        slc_per_block[b_id] = (u_val + d_val) / size if size > 0 else 0

    # D. Initialization
    final_bills = {name: 0.0 for name in player_names}
    for name in player_names:
        for b_id in unique_blocks:
            if name in block_unions[b_id]:
                final_bills[name] += slc_per_block[b_id]

    # E. Link Efficiency (Savings/Credits)
    savings_log = []
    for i in range(1, num_cities):
        p_b, c_b = block_ids[i-1], block_ids[i]

        # Only process if we are crossing between two different blocks
        if p_b != c_b:
            d_prev = city_data[i-1]['D']
            u_curr = city_data[i]['U']
            m_actual = city_data[i]['M']

            saving = (d_prev + u_curr) - m_actual

            # Weighted splits
            w_exit = d_prev / \
                (d_prev + u_curr) if (d_prev + u_curr) > 0 else 0.5
            w_entry = u_curr / \
                (d_prev + u_curr) if (d_prev + u_curr) > 0 else 0.5

            if saving > 0:
                # Credit Exiters (Previous Block Union)
                for p in block_unions[p_b]:
                    final_bills[p] -= (saving * w_exit /
                                       len(block_unions[p_b]))
                # Credit Joiners (Current Block Union)
                for p in block_unions[c_b]:
                    final_bills[p] -= (saving * w_entry /
                                       len(block_unions[c_b]))
                savings_log.append(
                    {"Link": f"{city_names[i-1]} -> {city_names[i]}", "Status": "Saving", "Amount": saving})

            elif saving < 0:
                loss = abs(saving)
                if strategy == "Current Participants":
                    for p in block_unions[c_b]:
                        final_bills[p] += (loss / len(block_unions[c_b]))
                else:  # Traveling Players Alone (Bridgers)
                    bridgers = [p for p in block_unions[p_b]
                                if p in block_unions[c_b]]
                    if bridgers:
                        for p in bridgers:
                            final_bills[p] += (loss / len(bridgers))
                    else:
                        # Fallback to current participants if no one bridged
                        for p in block_unions[c_b]:
                            final_bills[p] += (loss / len(block_unions[c_b]))
                savings_log.append(
                    {"Link": f"{city_names[i-1]} -> {city_names[i]}", "Status": "Loss", "Amount": -loss})

    # --- 4. OUTPUT ---
    st.header("Step 3: Final Billing Results")
    res_df = pd.DataFrame.from_dict(
        final_bills, orient='index', columns=['Final Bill (₹)'])
    res_df.index.name = "Player Name"

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Individual Breakdown")
        st.dataframe(res_df.style.format("₹{:,.2f}"), use_container_width=True)

        # Excel Download Button
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            res_df.to_excel(writer, sheet_name='Bills')
        st.download_button(
            label="📥 Download Results as Excel",
            data=output.getvalue(),
            file_name="Coach_FairShare_Results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with col2:
        st.subheader("Audit Trail")
        total_collected = sum(final_bills.values())
        # Actual cost = Arrival + all Transits + Final Departure
        # To find final departure, find the last city that actually had players
        last_city_idx = 0
        for i in range(num_cities):
            if edited_attendance[city_names[i]].any():
                last_city_idx = i

        actual_cost = city_data[0]['U'] + sum(c['M']
                                              for c in city_data[1:]) + city_data[last_city_idx]['D']

        st.metric("Total to Collect", f"₹{total_collected:,.2f}")
        st.metric("Actual Coach Invoice", f"₹{actual_cost:,.2f}")

        diff = total_collected - actual_cost
        if abs(diff) < 1:
            st.success("✅ Audit: Zero-Sum Integrity Maintained!")
        else:
            st.error(f"❌ Audit: ₹{diff:.2f} mismatch")

        if savings_log:
            st.write("**Link Efficiencies:**")
            st.table(savings_log)

# --- 5. LOGIC DOCUMENTATION ---
with st.expander("View Mathematical Logic (v26.0)"):
    st.markdown(f"""
    1. **Block Identification**: If $M_i = 0$, cities merge into one block.
    2. **SLC (Standalone Logical Cost)**: $(U + D) / N$ (where $N$ is the count of unique players who attended any city in the block).
    3. **Link Efficiency ($S$)**: $(D_{{prev}} + U_{{curr}}) - M_{{actual}}$.
    4. **Credits**: Distributed to players on the bus during transition using $W_{{exit}}$ and $W_{{entry}}$ weights.
    """)
