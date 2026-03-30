import streamlit as st
import pandas as pd

# --- PAGE SETUP ---
st.set_page_config(page_title="Coach Fair-Share v26.0", layout="wide", page_icon="🚌")

st.title("🚌 Coach Travel Fair-Share Calculator")
st.markdown("---")

# --- 1. INPUT SECTION (SIDEBAR) ---
st.sidebar.header("Step 1: Trip Costs")
num_cities = st.sidebar.slider("Number of Cities/Tournaments", 2, 10, 3)

city_data = []
for i in range(num_cities):
    with st.sidebar.expander(f"City {i+1} Details", expanded=(i < 3)):
        default_name = ["Delhi", "Dehradun", "Raipur"][i] if i < 3 else f"City {i+1}"
        name = st.text_input(f"City {i+1} Name", default_name, key=f"name_{i}")
        
        # Default values based on your sample data
        u_def = 7000.0 if i != 1 else 12800.0
        d_def = 7000.0 if i != 1 else 12800.0
        m_def = 0.0 if i == 0 else (7700.0 if i == 1 else 11500.0)
        
        u_cost = st.number_input(f"Base -> {name} (U)", value=u_def, key=f"u_{i}")
        d_cost = st.number_input(f"{name} -> Base (D)", value=d_def, key=f"d_{i}")
        m_cost = st.number_input(f"Transit to {name} (M)", value=m_def, key=f"m_{i}")
        
        city_data.append({"name": name, "U": u_cost, "D": d_cost, "M": m_cost})

strategy = st.sidebar.selectbox("Loss Allocation Strategy", ["Current Participants", "Traveling Player Alone"])

# --- 2. ATTENDANCE SECTION ---
st.header("Step 2: Attendance Matrix")
st.info("Check the box if the player attended the tournament in that city.")

player_input = st.text_area("Enter Player Names (one per line)", "Karthika\nDisha\nShree\nYash\nAbhvadya")
player_names = [p.strip() for p in player_input.split("\n") if p.strip()]

city_names = [c['name'] for c in city_data]
# Initialize empty matrix
attendance_df = pd.DataFrame(False, index=player_names, columns=city_names)

# Pre-fill sample logic for Disha and others
if "Disha" in attendance_df.index: attendance_df.loc["Disha", :] = True
if "Shree" in attendance_df.index: attendance_df.loc["Shree", city_names[0:min(2, num_cities)]] = True

edited_attendance = st.data_editor(attendance_df, use_container_width=True)

# --- 3. THE CALCULATION ENGINE ---
if st.button("🚀 Calculate Final Bills", type="primary"):
    # A. Block Logic (Merge if Transit M = 0)
    block_ids = []
    curr_block = 0
    for i in range(num_cities):
        if i > 0 and city_data[i]['M'] > 0:
            curr_block += 1
        block_ids.append(curr_block)
    
    # B. Union Membership
    unique_blocks = sorted(list(set(block_ids)))
    block_unions = {}
    for b_id in unique_blocks:
        cities_in_b = [city_names[i] for i, bid in enumerate(block_ids) if bid == b_id]
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

    # D. Final Bill logic
    final_bills = {name: 0.0 for name in player_names}
    for name in player_names:
        for b_id in unique_blocks:
            if name in block_unions[b_id]:
                final_bills[name] += slc_per_block[b_id]

    # E. Link Efficiency (Savings/Credits)
    for i in range(1, num_cities):
        p_b, c_b = block_ids[i-1], block_ids[i]
        if p_b != c_b:
            # S = (D_prev + U_curr) - M_actual
            saving = (city_data[i-1]['D'] + city_data[i]['U']) - city_data[i]['M']
            w_exit = city_data[i-1]['D'] / (city_data[i-1]['D'] + city_data[i]['U'])
            w_entry = city_data[i]['U'] / (city_data[i-1]['D'] + city_data[i]['U'])
            
            if saving > 0:
                # Credit Exiters
                for p in block_unions[p_b]:
                    final_bills[p] -= (saving * w_exit / len(block_unions[p_b]))
                # Credit Joiners
                for p in block_unions[c_b]:
                    final_bills[p] -= (saving * w_entry / len(block_unions[c_b]))
            elif saving < 0:
                loss = abs(saving)
                if strategy == "Current Participants":
                    for p in block_unions[c_b]: final_bills[p] += (loss / len(block_unions[c_b]))
                else: # Bridgers only
                    bridgers = [p for p in block_unions[p_b] if p in block_unions[c_b]]
                    if bridgers:
                        for p in bridgers: final_bills[p] += (loss / len(bridgers))

    # --- 4. OUTPUT ---
    st.header("Step 3: Final Billing Results")
    res_df = pd.DataFrame.from_dict(final_bills, orient='index', columns=['Final Bill (₹)'])
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.dataframe(res_df.style.format("₹{:,.2f}"), use_container_width=True)
    
    with col2:
        total_collected = sum(final_bills.values())
        actual_cost = city_data[0]['U'] + sum(c['M'] for c in city_data[1:]) + city_data[-1]['D']
        st.metric("Total to Collect", f"₹{total_collected:,.2f}")
        st.metric("Actual Coach Cost", f"₹{actual_cost:,.2f}")
        
        if abs(total_collected - actual_cost) < 1:
            st.success("✅ Audit: Balanced!")
        else:
            st.error(f"❌ Audit: ₹{total_collected - actual_cost:.2f} difference")