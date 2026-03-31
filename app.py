import streamlit as st
import pandas as pd
import io

# --- PAGE SETUP ---
st.set_page_config(
    page_title="Coach Fair-Share v27",
    layout="wide",
    page_icon="🚌"
)

# --- CLEAN UI STYLING ---
st.markdown("""
<style>
.main { background-color: #f8f9fa; }

/* Metric Card */
.stMetric {
    background-color: #ffffff;
    padding: 15px;
    border-radius: 10px;
    border: 1px solid #e0e0e0;
}

/* Metric LABEL (e.g., Total Collected) */
.stMetric label {
    color: #333333 !important;
    font-weight: 600;
}

/* Metric VALUE (₹ amount) */
.stMetric div[data-testid="stMetricValue"] {
    color: #000000 !important;
}

/* Metric DELTA (difference) */
.stMetric div[data-testid="stMetricDelta"] {
    color: #444444 !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>

/* Tabs container */
div[data-testid="stTabs"] {
    margin-top: 10px;
}

/* Each tab */
button[data-baseweb="tab"] {
    background-color: #111827 !important;
    color: #bbb !important;
    border-radius: 10px !important;
    padding: 10px 16px !important;
    margin-right: 6px !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    font-weight: 600 !important;
    transition: all 0.2s ease;
}

/* Hover effect */
button[data-baseweb="tab"]:hover {
    background-color: #1f2937 !important;
    color: #fff !important;
}

/* Active tab */
button[aria-selected="true"] {
    background: linear-gradient(135deg, #4facfe, #00f2fe) !important;
    color: white !important;
    border: none !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

/* Make tabs scrollable on mobile */
div[data-testid="stTabs"] > div {
    overflow-x: auto;
}

/* Remove ugly underline */
div[data-testid="stTabs"] div[role="tablist"] {
    border-bottom: none !important;
}

</style>
""", unsafe_allow_html=True)

st.title("🚌 Coach Travel Fair-Share Calculator")
st.caption("Strategic Cost Allocation Engine | Version v27 (UX Enhanced)")

# =========================
# 🧭 STEP PROGRESS BAR
# =========================
st.markdown("""
<style>
.step-container {
    display: flex;
    gap: 12px;
    margin: 20px 0;
}

.step-box {
    flex: 1;
    padding: 14px;
    border-radius: 12px;
    text-align: center;
    font-size: 14px;
    font-weight: 600;
    border: 1px solid rgba(255,255,255,0.1);
    transition: all 0.2s ease;
}

/* Step States */
.step-active {
    background: linear-gradient(135deg, #4facfe, #00f2fe);
    color: white;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

.step-done {
    background: #1e2a38;
    color: #8bc34a;
}

.step-pending {
    background: #111827;
    color: #888;
}
</style>

<div class="step-container">
    <div class="step-box step-active">📊 Step 1<br>Costs</div>
    <div class="step-box step-pending">👥 Step 2<br>Attendance</div>
    <div class="step-box step-pending">💰 Step 3<br>Settlement</div>
</div>
""", unsafe_allow_html=True)


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
tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Costs & Route", "👥 Attendance", "💰 Final Settlement", "📘 Guide"])

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

        # ✅ UX ADD
        if strategy == "Current Participants":
            st.info("Loss is shared among all players in the current block.")
        else:
            st.info(
                "Loss is assigned only to players traveling across cities (bridgers).")

    city_data = []
    city_names = []

    st.markdown("---")
    grid = st.columns(3)

    for i in range(num_cities):
        with grid[i % 3]:
            with st.container(border=True):
                default_names = ["Delhi", "Dehradun",
                                 "Raipur", "City 4", "City 5"]
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
        "Karthika\nDisha\nShree\nYash\nAbhivadya",
        key="player_name_input"
    )
    player_names = [p.strip() for p in player_input.split("\n") if p.strip()]

    if not player_names:
        st.warning("⚠️ Enter player names to continue")
        st.stop()

    if "master_df" not in st.session_state:
        st.session_state["master_df"] = pd.DataFrame(
            False, index=player_names, columns=city_names)

    existing_players = list(st.session_state["master_df"].index)
    existing_cities = list(st.session_state["master_df"].columns)

    if player_names != existing_players or city_names != existing_cities:
        st.session_state["master_df"] = st.session_state["master_df"].reindex(
            index=player_names, columns=city_names, fill_value=False
        )

    st.write("Check the boxes for the cities each player attended:")

    final_attendance = st.data_editor(
        st.session_state["master_df"],
        use_container_width=True,
        key="attendance_editor"
    )

    ordered_attendance = final_attendance[city_names]

    # ✅ VALIDATION UX
    if (ordered_attendance.sum(axis=1) == 0).any():
        st.warning("⚠️ Some players are not assigned to any city.")

    st.subheader("📍 Travel Map")
    visual_df = ordered_attendance.astype(
        str).replace({"True": "✅", "False": "—"})
    st.dataframe(visual_df, use_container_width=True)

    # =========================
    # 🧭 JOURNEY MAP
    # =========================
    st.subheader("🧭 Player Journey Map")

    journey_df = ordered_attendance.astype(str).replace({
        "True": "🟢",
        "False": "⚪"
    })

    def build_journey_row(row):
        journey = []
        for i, val in enumerate(row):
            journey.append(val)
            if i < len(row) - 1:
                journey.append("➡️")
        return journey

    journey_display = pd.DataFrame(
        [build_journey_row(journey_df.loc[player])
         for player in journey_df.index],
        index=journey_df.index
    )

    new_cols = []
    arrow_count = 1

    for i, city in enumerate(city_names):
        new_cols.append(f"🏙️ {city}")
        if i < len(city_names) - 1:
            new_cols.append(f"→{arrow_count}")
            arrow_count += 1

    journey_display.columns = new_cols

    # OPTIONAL: Clean display (hide numbering visually)
    journey_display.columns = [
        col if not col.startswith("→") else "→"
        for col in journey_display.columns
    ]
    journey_display.columns = new_cols
    st.dataframe(journey_display, use_container_width=True)

    # =========================
    # 🔗 BRIDGERS
    # =========================
    st.subheader("🔗 Bridging Players")

    def is_bridger(row):
        return any(row.iloc[i] and row.iloc[i+1] for i in range(len(row)-1))

    bridgers = ordered_attendance.apply(is_bridger, axis=1)
    bridger_list = ordered_attendance.index[bridgers].tolist()

    if bridger_list:
        st.success(f"👉 {', '.join(bridger_list)}")
    else:
        st.info("No bridging players detected.")

    st.session_state["ready_attendance"] = ordered_attendance

# =========================
# TAB 3: RESULTS
# =========================
with tab3:
    st.header("Step 3: Settlement Report")

    if "ready_attendance" not in st.session_state:
        st.info("👋 Go to the **Attendance** tab to select players first.")
        st.stop()

    attendance_data = st.session_state["ready_attendance"]

    if st.button("🚀 Generate Settlement Report", type="primary", use_container_width=True):

        # --- VALIDATION ---
        for city in city_names:
            if not attendance_data[city].any():
                st.error(
                    f"No players assigned to {city}. A coach trip requires at least one passenger.")
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
            union_mask = attendance_data[cities_in_block].any(axis=1)
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
                d_prev, u_curr, m_actual = city_data[i -
                                                     1]['D'], city_data[i]['U'], city_data[i]['M']
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
                    bridgers = [p for p in block_unions[p_b]
                                if p in block_unions[c_b]]
                    target = bridgers if (
                        strategy != "Current Participants" and bridgers) else block_unions[c_b]
                    for p in target:
                        final_bills[p] += loss / len(target)
                    savings_log.append(
                        {"Route": f"{city_names[i-1]} → {city_names[i]}", "Type": "Loss", "Amount": -loss})

        # --- SUMMARY ---
        total_collected = sum(final_bills.values())
        last_city_idx = max([i for i in range(num_cities)
                            if attendance_data[city_names[i]].any()] or [0])
        invoice_cost = city_data[0]['U'] + sum(c['M']
                                               for c in city_data[1:]) + city_data[last_city_idx]['D']

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Collected", f"₹{total_collected:,.2f}")
        m2.metric("Actual Cost", f"₹{invoice_cost:,.2f}")
        m3.metric("Difference", f"₹{total_collected - invoice_cost:,.2f}")

        # ✅ INSIGHT
        if abs(total_collected - invoice_cost) < 1:
            st.success("✅ Perfect balance")
        else:
            st.warning("⚠️ Mismatch detected")

        st.markdown("---")
        col1, col2 = st.columns([3, 2])

        with col1:
            st.subheader("📋 Billing Breakdown")
            res_df = pd.DataFrame.from_dict(final_bills, orient='index', columns=[
                                            'Final Bill (₹)']).sort_values(by="Final Bill (₹)", ascending=False)

            st.dataframe(res_df.style.format(
                "₹{:,.2f}"), use_container_width=True)

            # ✅ highlight
            st.info(
                f"💸 Highest: {res_df.index[0]} | 🪶 Lowest: {res_df.index[-1]}")

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                res_df.to_excel(writer, sheet_name='FairShare_Report')

            st.download_button(
                "📥 Download Excel", data=output.getvalue(), file_name="coach_fairshare.xlsx")

        with col2:
            st.subheader("⚖️ Savings & Loss Log")

            log_df = pd.DataFrame(savings_log)
            if not log_df.empty:
                log_df["Type"] = log_df["Type"].apply(
                    lambda x: "🟢 Saving" if x == "Saving" else "🔴 Loss"
                )
                st.dataframe(log_df, use_container_width=True)
            else:
                st.write("No transit adjustments.")

        with st.expander("🧱 Block Structure Details"):
            block_info = []
            for b_id in unique_blocks:
                cities = [city_names[i]
                          for i, bid in enumerate(block_ids) if bid == b_id]
                block_info.append({"Block": b_id, "Route": " → ".join(
                    cities), "Union Size": len(block_unions[b_id])})
            st.table(pd.DataFrame(block_info))


st.markdown("""
# 📘 User Guide

---

## 🧭 Navigation (Start Here)

This app has **4 tabs at the top**:

👉 📊 Costs & Route  
👉 👥 Attendance  
👉 💰 Final Settlement  
👉 📘 Guide  

⚠️ Always use them **left → right**

---

# 🔵 TAB 1: Costs & Route

This is where you define the **trip structure**

---

## 🧾 How to Fill This Section

### 🔢 Number of Cities
- Use the input box to select how many cities
- The app will automatically create input fields

👉 Example:
- 3 → Delhi, Dehradun, Raipur

---

### 🏙️ City Name
- You can edit names directly
- Click inside the box and type

---

### 💰 Cost Fields

For each city:

- **Outbound (Base → City)**  
  Cost to reach the city  

- **Return (City → Base)**  
  Cost to return  

- **Transit (City → City)**  
  Cost from previous city  

---

### ⚠️ Important Rule

- If **Transit = 0** → same block  
- If **Transit > 0** → new block  

---

## ⚙️ Strategy Selection

Choose how extra cost (loss) is shared:

- **Current Participants**
  → Shared by all players  

- **Traveling Players Alone (Bridgers)**
  → Only players continuing travel pay  

---

👉 After filling, go to **👥 Attendance tab**

---

# 🟢 TAB 2: Attendance

This is where you define **who traveled where**

---

## 👥 How to Add Players

- Type player names in the text box  
- One name per line  

👉 Example:
Karthika  
Yash  
Shree  

---

## ❌ How to Remove Players

- Delete the name from the list  
- The table will automatically update  

---

## ➕ How to Add More Players

- Just add a new line in the text box  
- Table updates automatically  

---

## ✅ How to Mark Attendance

- Use the table (checkbox grid)
- Tick the cities each player attended  

---

## 📊 What You See

### 📍 Travel Map
- ✅ = attended  
- — = not attended  

---

### 🧭 Player Journey Map
- 🟢 = present  
- ⚪ = absent  
- ➡️ = movement  

👉 Helps visualize travel flow  

---

### 🔗 Bridging Players
- Players who travel across cities  
- Important for loss calculation  

---

## ⚠️ Validation Rules

- Every city must have **at least one player**
- Every player should have **at least one city**

---

👉 After filling, go to **💰 Final Settlement**

---

# 🔴 TAB 3: Final Settlement

---

## ▶️ How to Generate Results

Click:

👉 **🚀 Generate Settlement Report**

---

## 📊 What You Get

### Summary
- Total Collected  
- Actual Cost  
- Difference  

---

### ✅ Balance Check
- ✔️ Perfect → all good  
- ⚠️ Mismatch → check inputs  

---

### 📋 Billing Breakdown
- Final amount per player  

---

### 💡 Insights
- Highest payer  
- Lowest payer  

---

### ⚖️ Savings & Loss Log
- 🟢 Saving  
- 🔴 Loss  

---

### 🧱 Block Structure
- Shows grouping of cities  

---

## 📥 Download

- Click **Download Excel**
- Save or share results  

---

# 📘 TAB 4: Guide

You are here 🙂

---

# 🔁 Quick Flow

1. Enter cities & costs  
2. Add players & mark attendance  
3. Generate settlement  

---

# 🚨 Common Mistakes

- Leaving a city with no players  
- Forgetting to mark attendance  
- Entering wrong transit values  

---

# 💡 Tips

- Use Journey Map to verify player paths  
- Check Bridging Players before finalizing  
- Ensure Difference = ₹0  
- Download Excel for records  

""")

# --- FOOTER ---
st.markdown("---")
st.caption("Fair-Share Engine | Zero-Sum Verified | v27 UX Enhanced")
