import streamlit as st
import sqlite3
import pandas as pd
from datetime import date
import hashlib
import os

st.set_page_config(page_title="Expense Tracker", layout="wide")

LOGIN_FILE = "login.txt"
DB_FILE = "expenses.db"

# ---------------- SESSION LOGIN ----------------
if "user_email" not in st.session_state:
    if os.path.exists(LOGIN_FILE):
        with open(LOGIN_FILE, "r") as f:
            st.session_state.user_email = f.read().strip()
    else:
        st.session_state.user_email = None


# ---------------- LOGIN PAGE ----------------
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


# ---------------- DATABASE ----------------
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

user_id = hashlib.md5(st.session_state.user_email.encode()).hexdigest()[:8]
user_table = f"expenses_{user_id}"

cursor.execute(f"""
CREATE TABLE IF NOT EXISTS {user_table}(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    amount REAL,
    category TEXT,
    description TEXT
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
    ["Add Expense", "View Expenses"]
)

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

        st.success("Expense Added Successfully")


# ====================================================
# VIEW EXPENSES
# ====================================================

if menu == "View Expenses":

    st.subheader("🔎 Search Expenses")

    col1, col2 = st.columns(2)

    with col1:
        selected_month = st.selectbox(
            "Select Month",
            ["01","02","03","04","05","06","07","08","09","10","11","12"]
        )

    with col2:
        selected_date = st.date_input("Select Date")

    # -------- MONTH FILTER --------

    cursor.execute(f"""
    SELECT date, amount, category, description
    FROM {user_table}
    WHERE strftime('%m', date) = ?
    ORDER BY date DESC
    """, (selected_month,))

    month_rows = cursor.fetchall()

    if month_rows:

        df_month = pd.DataFrame(
            month_rows,
            columns=["Date","Amount","Category","Description"]
        )

        df_month["Amount"] = df_month["Amount"].apply(lambda x: f"₹{x:,.0f}")

        st.subheader("📅 Selected Month Expenses")

        st.dataframe(df_month, use_container_width=True)

    else:
        st.info("No expenses in this month")


    # -------- DATE FILTER --------

    cursor.execute(f"""
    SELECT date, amount, category, description
    FROM {user_table}
    WHERE date = ?
    """, (str(selected_date),))

    day_rows = cursor.fetchall()

    if day_rows:

        df_day = pd.DataFrame(
            day_rows,
            columns=["Date","Amount","Category","Description"]
        )

        df_day["Amount"] = df_day["Amount"].apply(lambda x: f"₹{x:,.0f}")

        st.subheader("📆 Selected Day Expenses")

        st.dataframe(df_day, use_container_width=True)

    else:
        st.info("No expenses on this day")


    # ====================================================
    # MONTHLY REPORT TABLE
    # ====================================================

    st.subheader("📅 Monthly Expense Report")

    cursor.execute(f"""
    SELECT strftime('%Y-%m', date) AS Month, SUM(amount)
    FROM {user_table}
    GROUP BY Month
    ORDER BY Month DESC
    """)

    month_data = cursor.fetchall()

    if month_data:

        df_month_report = pd.DataFrame(
            month_data,
            columns=["Month","Total Spent"]
        )

        df_month_report["Total Spent"] = df_month_report["Total Spent"].apply(
            lambda x: f"₹{x:,.0f}"
        )

        st.dataframe(df_month_report, use_container_width=True)


    # ====================================================
    # YEARLY REPORT TABLE
    # ====================================================

    st.subheader("📆 Yearly Expense Report")

    cursor.execute(f"""
    SELECT strftime('%Y', date) AS Year, SUM(amount)
    FROM {user_table}
    GROUP BY Year
    ORDER BY Year DESC
    """)

    year_data = cursor.fetchall()

    if year_data:

        df_year = pd.DataFrame(
            year_data,
            columns=["Year","Total Spent"]
        )

        df_year["Total Spent"] = df_year["Total Spent"].apply(
            lambda x: f"₹{x:,.0f}"
        )

        st.dataframe(df_year, use_container_width=True)


st.markdown("---")
st.caption("💰 Personal Expense Tracker (Streamlit + SQLite)")
