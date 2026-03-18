import streamlit as st
import sqlite3
import pandas as pd
from datetime import date
import hashlib
import os
import io

st.set_page_config(page_title="Smart AI Expense Tracker", layout="wide")

LOGIN_FILE = "login.txt"
DB_FILE = "expenses.db"

# ---------------- SESSION ----------------
if "user_email" not in st.session_state:
    if os.path.exists(LOGIN_FILE):
        with open(LOGIN_FILE,"r") as f:
            st.session_state.user_email = f.read().strip()
    else:
        st.session_state.user_email = None

# ---------------- LOGIN ----------------
def login_page():
    st.title("🔐 Smart AI Expense Tracker")
    st.caption("AI Powered Financial Assistant 💡")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if email and password == "123456":
            st.session_state.user_email = email
            with open(LOGIN_FILE,"w") as f:
                f.write(email)
            st.rerun()
        else:
            st.error("Invalid Login")

if not st.session_state.user_email:
    login_page()
    st.stop()

# ---------------- DATABASE ----------------
conn = sqlite3.connect(DB_FILE,check_same_thread=False)
cursor = conn.cursor()

user_id = hashlib.md5(st.session_state.user_email.encode()).hexdigest()[:8]
user_table = f"expenses_{user_id}"

# Expense table
cursor.execute(f"""
CREATE TABLE IF NOT EXISTS {user_table}(
id INTEGER PRIMARY KEY AUTOINCREMENT,
date TEXT,
amount REAL,
category TEXT,
description TEXT
)
""")

# Budget table
cursor.execute("""
CREATE TABLE IF NOT EXISTS user_budget(
user TEXT PRIMARY KEY,
budget REAL
)
""")

conn.commit()

# ---------------- SIDEBAR ----------------
st.sidebar.title("Menu")

if st.sidebar.button("Logout"):
    st.session_state.clear()
    if os.path.exists(LOGIN_FILE):
        os.remove(LOGIN_FILE)
    st.rerun()

menu = st.sidebar.selectbox(
"Choose",
["Dashboard","Add Expense","Reports","Insights"]
)

st.title(f"💰 Smart AI Expense Tracker - {st.session_state.user_email}")

# =====================================================
# DASHBOARD
# =====================================================
if menu == "Dashboard":

    st.subheader("📊 Dashboard")

    cursor.execute(f"SELECT SUM(amount) FROM {user_table}")
    total_spent = cursor.fetchone()[0] or 0

    cursor.execute(f"""
    SELECT SUM(amount)
    FROM {user_table}
    WHERE strftime('%Y-%m',date)=strftime('%Y-%m','now')
    """)
    month_spent = cursor.fetchone()[0] or 0

    # Load saved budget
    cursor.execute("SELECT budget FROM user_budget WHERE user=?",(user_id,))
    result = cursor.fetchone()
    budget = result[0] if result else 0

    # Set budget
    new_budget = st.number_input("Set Monthly Budget ₹",min_value=100.0,step=500.0)

    if st.button("Save Budget"):
        cursor.execute("REPLACE INTO user_budget(user,budget) VALUES(?,?)",(user_id,new_budget))
        conn.commit()
        st.success("Budget Saved ✅")
        st.rerun()

    if budget > 0:
        percent = (month_spent / budget) * 100
        progress = min(month_spent / budget, 1.0)

        st.progress(progress)
        st.write(f"Budget Used: {percent:.1f}%")

        if percent >= 100:
            st.error("❌ Budget Exceeded!")
        elif percent >= 80:
            st.warning("⚠️ 80% budget used")
        elif percent >= 50:
            st.info("ℹ️ 50% budget used")

    c1,c2 = st.columns(2)
    c1.metric("Total Spent",f"₹{total_spent:,.0f}")
    c2.metric("This Month",f"₹{month_spent:,.0f}")

# =====================================================
# ADD EXPENSE
# =====================================================
if menu == "Add Expense":

    st.subheader("➕ Add Expense")

    col1,col2 = st.columns(2)

    with col1:
        expense_date = st.date_input("Date",value=date.today())

        categories = ["Food","Transport","Shopping","Bills","Medical","Other"]
        category = st.selectbox("Category",categories)

        custom = ""
        if category == "Other":
            custom = st.text_input("Enter Custom Category")

        final_category = custom.strip() if custom.strip() else category

    with col2:
        amount = st.number_input("Amount ₹",min_value=1.0)
        description = st.text_input("Description")

    # Auto category
    if description:
        desc = description.lower()
        if "uber" in desc or "bus" in desc:
            final_category = "Transport"
        elif "pizza" in desc or "food" in desc:
            final_category = "Food"
        elif "amazon" in desc:
            final_category = "Shopping"

    if st.button("Save Expense"):
        cursor.execute(
        f"INSERT INTO {user_table} (date,amount,category,description) VALUES (?,?,?,?)",
        (str(expense_date),amount,final_category,description)
        )
        conn.commit()
        st.success("Expense Added ✅")

# =====================================================
# REPORTS
# =====================================================
if menu == "Reports":

    cursor.execute(f"SELECT * FROM {user_table}")
    data = cursor.fetchall()

    if not data:
        st.info("No data")
        st.stop()

    df = pd.DataFrame(data,columns=["ID","Date","Amount","Category","Description"])

    st.dataframe(df,use_container_width=True)

    # Excel download
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer,index=False,sheet_name='Expenses')

    st.download_button(
        "📥 Download Excel",
        data=output.getvalue(),
        file_name="expenses.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Date filter
    st.subheader("📅 Search by Date")

    selected_date = st.date_input("Select Date")

    cursor.execute(f"""
    SELECT date,amount,category,description
    FROM {user_table}
    WHERE date=?
    """,(str(selected_date),))

    rows = cursor.fetchall()

    if rows:
        df_day = pd.DataFrame(rows,columns=["Date","Amount","Category","Description"])
        st.dataframe(df_day,use_container_width=True)
    else:
        st.info("No expenses on this date")

# =====================================================
# INSIGHTS
# =====================================================
if menu == "Insights":

    st.subheader("🧠 Smart Insights")

    cursor.execute(f"""
    SELECT category,SUM(amount)
    FROM {user_table}
    GROUP BY category
    """)
    data = cursor.fetchall()

    if data:
        df = pd.DataFrame(data,columns=["Category","Total"])
        total = df["Total"].sum()

        for _,row in df.iterrows():
            percent = (row["Total"]/total)*100

            st.write(f"👉 {row['Category']} takes {percent:.1f}%")

            if percent > 40:
                st.warning(f"⚠️ High spending on {row['Category']}")
            elif percent < 10:
                st.success(f"✅ Good control on {row['Category']}")

    st.subheader("📈 Prediction")

    cursor.execute(f"""
    SELECT strftime('%Y-%m',date),SUM(amount)
    FROM {user_table}
    GROUP BY 1
    ORDER BY 1 DESC
    LIMIT 3
    """)

    last3 = cursor.fetchall()

    if len(last3) >= 3:
        avg = sum([x[1] for x in last3]) / 3
        st.success(f"Estimated next month spend: ₹{avg:,.0f}")

st.markdown("---")
st.caption("🏆 Final Hackathon Ready Project")
