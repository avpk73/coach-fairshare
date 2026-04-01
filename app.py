import streamlit as st
import pandas as pd
import io
from coach_engine import CoachFairShareEngine  # Import the logic engine

# --- PAGE SETUP ---
st.set_page_config(
    page_title="Coach Fair-Share v28",
    layout="wide",
    page_icon="🚌"
)

# --- CLEAN UI STYLING (CSS) ---
st.markdown("""
<style>
.main { background-color: #f8f9fa; }
.stMetric {
    background-color: #ffffff;
    padding: 15px;
    border-radius: 10px;
    border: 1px solid #e0e0e0;
}
.stMetric label { color: #333333 !important; font-weight: 600; }
.stMetric div[data-testid="stMetricValue"] { color: #000000 !important; }

/* Tabs Styling */
button[data-baseweb="tab"] {
    background-color: #111827 !important;
    color: #bbb !important;
    border-radius: 10px !important;
    padding: 10px 16px !important;
    margin-right: 6px !important;
    font-weight: 600 !important;
}
button[aria-selected="true"] {
    background: linear-gradient(135deg, #4facfe, #00f2fe) !important;
    color: white !important;
}
div[data-testid="stTabs"] div[role="tablist"] { border-bottom: none !important; }
</style>
""", unsafe_allow_html=True)

st.title("🚌 Coach Travel Fair-Share Calculator")
st.caption("Strategic Cost Allocation Engine | Modular v28 (Stable)")

# --- CONCEPT EXPLAINER ---
with st.expander("📖 Logic Overview & Concepts"):
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
**Core Principles:**
- No more than standalone trip (SLC)
- Savings are shared fairly
- Total collection = actual cost
""")
    with col_b:
        st.markdown("""
**Definitions:**
- Outbound: Base → City | Return: City → Base
- Transit: Previous City → Current City
- Block: Group of cities with Transit = 0
""")

# --- TABS ---
tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Costs & Route", "👥 Attendance", "💰 Final Settlement", "📘 Guide"])

# =========================
# TAB 1: COST INPUT
# =========================
with tab1:
    st.header("Step 1: Define Trip Costs")
    col_left, _ = st.columns([1, 2])
    with col_left:
        num_cities = st.number_input("Number of Cities", 2, 10, 3)
        strategy = st.selectbox(
            "Loss Allocation Strategy",
            ["Current Participants", "Traveling Players Alone (Bridgers)"]
        )
        if strategy == "Current Participants":
            st.info("Loss is shared among all players in the current block.")
        else:
            st.info(
                "Loss is assigned only to players traveling across cities (bridgers).")

    city_data, city_names = [], []
    st.markdown("---")
    grid = st.columns(3)
    for i in range(num_cities):
        with grid[i % 3]:
            with st.container(border=True):
                default_names = ["Delhi", "Dehradun",
                                 "Raipur", "City 4", "City 5"]
                name = st.text_input("City Name", default_names[i] if i < len(
                    default_names) else f"City {i+1}", key=f"name_{i}")
                u = st.number_input(
                    f"Outbound (Base→{name})", value=7000.0 if i != 1 else 12800.0, key=f"u_{i}")
                d = st.number_input(
                    f"Return ({name}→Base)", value=7000.0 if i != 1 else 12800.0, key=f"d_{i}")
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
        "Enter Player Names (one per line)", "Karthika\nDisha\nShree\nYash\nAbhivadya")
    player_names = [p.strip() for p in player_input.split("\n") if p.strip()]

    if not player_names:
        st.warning("⚠️ Enter player names to continue")
        st.stop()

    if "master_df" not in st.session_state:
        st.session_state["master_df"] = pd.DataFrame(
            False, index=player_names, columns=city_names)

    # Sync dataframe
    if list(st.session_state["master_df"].index) != player_names or list(st.session_state["master_df"].columns) != city_names:
        st.session_state["master_df"] = st.session_state["master_df"].reindex(
            index=player_names, columns=city_names, fill_value=False)

    final_attendance = st.data_editor(
        st.session_state["master_df"], use_container_width=True)
    st.session_state["ready_attendance"] = final_attendance[city_names]

    # --- JOURNEY MAP ---
    st.subheader("🧭 Player Journey Map")

    journey_df = st.session_state["ready_attendance"].astype(str).replace({
        "True": "🟢",
        "False": "⚪"
    })

    def build_row(row):
        journey = []
        for i, val in enumerate(row):
            journey.append(val)
            if i < len(row) - 1:
                journey.append("➡️")
        return journey

    journey_display = pd.DataFrame(
        [build_row(journey_df.loc[p]) for p in journey_df.index],
        index=journey_df.index
    )

    # ✅ Clean column names (NO hacks, NO duplicates issues now)
    new_cols = []
    for i, city in enumerate(city_names):
        new_cols.append(f"🏙️ {city}")
        if i < len(city_names) - 1:
            new_cols.append("➡️")

    journey_display.columns = new_cols

    # ✅ Stable rendering (NO .style)
    st.dataframe(journey_display, use_container_width=True)

    # --- BRIDGERS ---

    def is_bridger(row):
        return any(row.iloc[i] and row.iloc[i+1] for i in range(len(row)-1))
    bridger_list = st.session_state["ready_attendance"].index[st.session_state["ready_attendance"].apply(
        is_bridger, axis=1)].tolist()
    if bridger_list:
        st.success(f"🔗 Bridging Players: {', '.join(bridger_list)}")

# =========================
# TAB 3: RESULTS (ENGINE CALL)
# =========================
with tab3:
    st.header("Step 3: Settlement Report")
    if "ready_attendance" not in st.session_state:
        st.info("👋 Mark attendance first.")
        st.stop()

    if st.button("🚀 Generate Settlement Report", type="primary", use_container_width=True):
        # CALL THE EXTERNAL ENGINE
        engine = CoachFairShareEngine(
            city_data, player_names, st.session_state["ready_attendance"], strategy)
        res = engine.calculate_settlement()

        # METRICS
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Collected", f"₹{res['total_collected']:,.2f}")
        m2.metric("Actual Cost", f"₹{res['invoice_cost']:,.2f}")
        m3.metric("Difference",
                  f"₹{res['total_collected'] - res['invoice_cost']:.2f}")

        # BREAKDOWN
        col1, col2 = st.columns([3, 2])
        with col1:
            st.subheader("📋 Billing Breakdown")
            res_df = pd.DataFrame.from_dict(res['final_bills'], orient='index', columns=[
                                            'Final Bill (₹)']).sort_values(by="Final Bill (₹)", ascending=False)
            st.dataframe(res_df.style.format(
                "₹{:,.2f}"), use_container_width=True)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                res_df.to_excel(writer, sheet_name='FairShare_Report')
            st.download_button(
                "📥 Download Excel", data=output.getvalue(), file_name="coach_fairshare.xlsx")

        with col2:
            st.subheader("⚖️ Savings & Loss Log")
            log_df = pd.DataFrame(res['savings_log'])
            if not log_df.empty:
                log_df["Type"] = log_df["Type"].apply(
                    lambda x: "🟢 Saving" if x == "Saving" else "🔴 Loss")
                st.dataframe(log_df, use_container_width=True)

# =========================
# TAB 4: FULL GUIDE RESTORED
# =========================
with tab4:
    st.markdown("""
    # 📘 User Guide
    ---
    ## 🧭 Navigation
    This app has **4 tabs at the top**. Always use them **left → right**.

    # 🔵 TAB 1: Costs & Route
    ### 💰 Cost Fields
    For each city:
    - **Outbound (Base → City)**: Cost to reach the city  
    - **Return (City → Base)**: Cost to return  
    - **Transit (City → City)**: Cost from previous city  

    ### ⚠️ Important Block Rule
    - If **Transit = 0** → Cities are grouped in the same **Block**.
    - If **Transit > 0** → A new **Block** starts.

    # 🟢 TAB 2: Attendance
    - Type player names (one per line).
    - Check the boxes for the cities each player attended.
    - **Journey Map**: Visualizes the flow of movement.
    - **Bridgers**: Identified as players who continue travel across cities.

    # 🔴 TAB 3: Final Settlement
    - Click **Generate Settlement Report**.
    - **Zero-Sum Verified**: Ensures the "Difference" is ₹0.
    - **Download Excel**: Get a record for your group accounts.

    # 🚨 Common Mistakes
    - Leaving a city with no players (the bus can't travel empty!).
    - Entering wrong transit values (remember: 0 means the coach stayed put).
    """)

# --- FOOTER ---
st.markdown("---")
st.caption("Fair-Share Engine | Zero-Sum Verified | v28 Modular Stable")
