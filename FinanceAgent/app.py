import streamlit as st
import sqlite3
import matplotlib.pyplot as plt
import pandas as pd
from datetime import date
import hashlib
import os

st.set_page_config(page_title="Expense Tracker", layout="wide")

LOGIN_FILE = "login.txt"
DB_FILE = "expenses.db"

# ---------- LOGIN SESSION ----------
if 'user_email' not in st.session_state:
    if os.path.exists(LOGIN_FILE):
        with open(LOGIN_FILE, "r") as f:
            st.session_state.user_email = f.read().strip()
    else:
        st.session_state.user_email = None


# ---------- LOGIN PAGE ----------
def login_page():
    st.title("🔐 Expense Tracker Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    st.info("Demo Login\nEmail: user@gmail.com\nPassword: 123456")

    if st.button("Login"):
        if email and password == "123456":
            st.session_state.user_email = email

            with open(LOGIN_FILE, "w") as f:
                f.write(email)

            st.rerun()
        else:
            st.error("Invalid login")


if not st.session_state.user_email:
    login_page()
    st.stop()

# ---------- DATABASE ----------
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

user_id = hashlib.md5(st.session_state.user_email.encode()).hexdigest()[:8]
user_table = f"expenses_{user_id}"

cursor.execute(f'''
CREATE TABLE IF NOT EXISTS {user_table}(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    amount REAL,
    category TEXT,
    description TEXT
)
''')

conn.commit()

# ---------- SIDEBAR ----------
st.sidebar.title("Menu")

if st.sidebar.button("Logout"):
    st.session_state.clear()
    if os.path.exists(LOGIN_FILE):
        os.remove(LOGIN_FILE)
    st.rerun()

menu = st.sidebar.selectbox(
    "Choose",
    ["Add Expense", "View Expenses"]
)

# ---------- TITLE ----------
st.title(f"💰 {st.session_state.user_email.split('@')[0]}'s Expense Tracker")

# ====================================================
# ADD EXPENSE
# ====================================================

if menu == "Add Expense":

    st.subheader("➕ Add Expense")

    col1, col2 = st.columns(2)

    with col1:
        expense_date = st.date_input("Date", value=date.today())

        categories = ["Food","Transport","Shopping","Bills","Medical","Other"]
        category = st.selectbox("Category", categories)

        custom = st.text_input("Custom Category (optional)")
        if custom.strip():
            category = custom.strip()

    with col2:
        amount = st.number_input("Amount ₹", min_value=1.0, step=10.0)

        description = st.text_input("Description")

    if st.button("Save Expense"):

        cursor.execute(
            f"INSERT INTO {user_table} (date,amount,category,description) VALUES (?,?,?,?)",
            (str(expense_date), amount, category, description)
        )

        conn.commit()

        st.success("Expense Added")

# ====================================================
# VIEW EXPENSE
# ====================================================

if menu == "View Expenses":

    st.subheader("📊 All Expenses")

    cursor.execute(f"SELECT * FROM {user_table} ORDER BY date DESC")
    data = cursor.fetchall()

    if not data:
        st.info("No expenses added")
        st.stop()

    df = pd.DataFrame(data, columns=["ID","Date","Amount","Category","Description"])

    # ---------- TOTAL ----------
    total = df["Amount"].sum()
    st.metric("Total Spent", f"₹{total:,.0f}")

    # ---------- TABLE ----------
    st.subheader("Expense List")

    for i,row in df.iterrows():

        c1,c2,c3,c4,c5 = st.columns([2,1,2,3,1])

        c1.write(row["Date"])
        c2.write(f"₹{row['Amount']}")
        c3.write(row["Category"])
        c4.write(row["Description"])

        if c5.button("🗑", key=row["ID"]):
            cursor.execute(
                f"DELETE FROM {user_table} WHERE id=?",
                (row["ID"],)
            )
            conn.commit()
            st.rerun()

    # ====================================================
    # CATEGORY PIE CHART
    # ====================================================

    st.subheader("📈 Category Breakdown")

    pie = df.groupby("Category")["Amount"].sum()

    fig, ax = plt.subplots()
    ax.pie(pie, labels=pie.index, autopct='%1.1f%%')
    ax.set_title("Category Expenses")

    st.pyplot(fig)

    # ====================================================
    # MONTHLY REPORT
    # ====================================================

    st.subheader("📅 Monthly Report")

    cursor.execute(f"""
    SELECT strftime('%Y-%m', date) as month, SUM(amount)
    FROM {user_table}
    GROUP BY month
    ORDER BY month
    """)

    month_data = cursor.fetchall()

    if month_data:

        df_month = pd.DataFrame(month_data, columns=["Month","Total"])

        st.table(df_month)

        fig2, ax2 = plt.subplots()

        ax2.bar(df_month["Month"], df_month["Total"])

        ax2.set_xlabel("Month")
        ax2.set_ylabel("Amount ₹")
        ax2.set_title("Monthly Expenses")

        st.pyplot(fig2)

    # ====================================================
    # YEARLY REPORT
    # ====================================================

    st.subheader("📆 Yearly Report")

    cursor.execute(f"""
    SELECT strftime('%Y', date) as year, SUM(amount)
    FROM {user_table}
    GROUP BY year
    ORDER BY year
    """)

    year_data = cursor.fetchall()

    if year_data:

        df_year = pd.DataFrame(year_data, columns=["Year","Total"])

        st.table(df_year)

        fig3, ax3 = plt.subplots()

        ax3.bar(df_year["Year"], df_year["Total"])

        ax3.set_xlabel("Year")
        ax3.set_ylabel("Amount ₹")
        ax3.set_title("Yearly Expenses")

        st.pyplot(fig3)

st.markdown("---")
st.caption("Personal Expense Tracker")
