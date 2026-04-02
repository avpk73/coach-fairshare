import streamlit as st
import pandas as pd
import io
from coach_engine import CoachFairShareEngine

# --- PAGE SETUP ---
st.set_page_config(page_title="Coach Fair-Share v28",
                   layout="wide", page_icon="🚌")

# --- UI STYLING (RESTORING v27 DARK TABS) ---
st.markdown("""
<style>
.main { background-color: #f8f9fa; }
.stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
button[data-baseweb="tab"] { background-color: #111827 !important; color: #bbb !important; border-radius: 10px !important; font-weight: 600 !important; }
button[aria-selected="true"] { background: linear-gradient(135deg, #4facfe, #00f2fe) !important; color: white !important; }
div[data-testid="stTabs"] div[role="tablist"] { border-bottom: none !important; }
</style>
""", unsafe_allow_html=True)

st.title("🚌 Coach Travel Fair-Share Calculator")
st.caption("Strategic Cost Allocation Engine | Modular v28 (Stable)")

# --- CONCEPT EXPLAINER ---
with st.expander("📖 Logic Overview & Concepts"):
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(
            "**Core Principles:**\n- No more than standalone trip (SLC)\n- Efficiency shared fairly\n- Zero-sum verified")
    with col_b:
        st.markdown(
            "**Definitions:**\n- Outbound: Base→City | Return: City→Base\n- Block: Transit = 0")

tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Costs & Route", "👥 Attendance", "💰 Final Settlement", "📘 Guide"])

# =========================
# TAB 1: COSTS
# =========================
with tab1:
    st.header("Step 1: Define Trip Costs")
    col_left, _ = st.columns([1, 2])
    with col_left:
        num_cities = st.number_input("Number of Cities", 2, 10, 3)
        strategy = st.selectbox("Loss Allocation Strategy", [
                                "Current Participants", "Traveling Players Alone (Bridgers)"])

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
        st.warning("⚠️ Enter names")
        st.stop()

    if "master_df" not in st.session_state:
        st.session_state["master_df"] = pd.DataFrame(
            False, index=player_names, columns=city_names)

    if list(st.session_state["master_df"].index) != player_names or list(st.session_state["master_df"].columns) != city_names:
        st.session_state["master_df"] = st.session_state["master_df"].reindex(
            index=player_names, columns=city_names, fill_value=False)

    final_attendance = st.data_editor(
        st.session_state["master_df"], use_container_width=True)
    st.session_state["ready_attendance"] = final_attendance[city_names]

    # RESTORED: Travel Map
    st.subheader("📍 Travel Map")
    st.dataframe(st.session_state["ready_attendance"].replace(
        {True: "✅", False: "—"}), use_container_width=True)
'''
    # RESTORED: Journey Map with Centered Formatting
    st.subheader("🧭 Player Journey Map")
    journey_df = st.session_state["ready_attendance"].replace(
        {True: "🟢", False: "⚪"})

    def build_row(row):
        j = []
        for i, val in enumerate(row):
            j.append(val)
            if i < len(row)-1:
                j.append("➡️")
        return j
    journey_display = pd.DataFrame(
        [build_row(journey_df.loc[p]) for p in journey_df.index], index=journey_df.index)

    # Header Fix (Unique spaces for arrow headers to prevent crash)
    new_cols, arrow_count = [], 0
    for i, city in enumerate(city_names):
        new_cols.append(f"🏙️ {city}")
        if i < len(city_names)-1:
            new_cols.append("➡️" + (" " * arrow_count))
            arrow_count += 1
    journey_display.columns = new_cols

    # Centered Alignment Styling
    st.dataframe(journey_display.style.set_properties(
        **{'text-align': 'center'}).set_table_styles([{'selector': 'th', 'props': [('text-align', 'center')]}]))

    # RESTORED: Bridgers logic
    def is_bridger(row): return any(
        row.iloc[i] and row.iloc[i+1] for i in range(len(row)-1))
    bridgers = st.session_state["ready_attendance"].index[st.session_state["ready_attendance"].apply(
        is_bridger, axis=1)].tolist()
    if bridgers:
        st.success(f"🔗 Bridging Players: {', '.join(bridgers)}")
'''
# =========================
# TAB 3: RESULTS
# =========================
with tab3:
    st.header("Step 3: Settlement Report")
    if "ready_attendance" not in st.session_state:
        st.info("👋 Mark attendance first.")
        st.stop()

    if st.button("🚀 Generate Settlement Report", type="primary", use_container_width=True):
        engine = CoachFairShareEngine(
            city_data, player_names, st.session_state["ready_attendance"], strategy)
        res = engine.calculate_settlement()

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Collected", f"₹{res['total_collected']:,.2f}")
        m2.metric("Actual Cost", f"₹{res['invoice_cost']:,.2f}")
        m3.metric("Difference",
                  f"₹{res['total_collected'] - res['invoice_cost']:.2f}")

        if abs(res['total_collected'] - res['invoice_cost']) < 1:
            st.success("✅ Perfect balance")

        st.markdown("---")
        col1, col2 = st.columns([3, 2])
        with col1:
            st.subheader("📋 Billing Breakdown")
            df = pd.DataFrame.from_dict(res['final_bills'], orient='index', columns=[
                                        'Final Bill (₹)']).sort_values(by="Final Bill (₹)", ascending=False)
            st.dataframe(df.style.format("₹{:,.2f}"), use_container_width=True)

            # RESTORED: Insights
            st.info(f"💸 Highest: {df.index[0]} | 🪶 Lowest: {df.index[-1]}")

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Report')
            st.download_button("📥 Excel", data=output.getvalue(),
                               file_name="coach_fairshare.xlsx")

        with col2:
            st.subheader("⚖️ Savings & Loss Log")
            log_df = pd.DataFrame(res['savings_log'])
            if not log_df.empty:
                log_df["Type"] = log_df["Type"].apply(
                    lambda x: "🟢 Saving" if x == "Saving" else "🔴 Loss")
                st.dataframe(log_df, use_container_width=True)

        # RESTORED: Block Details
        with st.expander("🧱 Block Structure Details"):
            st.table(pd.DataFrame(res['block_info']))


# =========================
# TAB 4: GUIDE
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

    # 🟢 TAB 2: Attendance
    - Type player names (one per line).
    - Check the boxes for the cities each player attended.

    # 🔴 TAB 3: Final Settlement
    - Click **Generate Settlement Report**.
    - **Zero-Sum Verified**: Ensures the "Difference" is ₹0.
    """)

# --- FOOTER ---
st.markdown("---")
st.caption("Fair-Share Engine | Zero-Sum Verified | v28 Modular Stable")
