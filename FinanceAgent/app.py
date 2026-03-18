import streamlit as st
import sqlite3
import pandas as pd
from datetime import date
import hashlib
import os

st.set_page_config(page_title="Expense Tracker", layout="wide")

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
    st.title("🔐 Expense Tracker Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    st.info("Demo Login\nEmail: user@gmail.com\nPassword: 123456")

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
["Dashboard","Add Expense","Reports"]
)

st.title(f"💰 {st.session_state.user_email.split('@')[0]}'s Expense Tracker")


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

    cursor.execute(f"""
    SELECT SUM(amount)
    FROM {user_table}
    WHERE date=date('now')
    """)
    today_spent = cursor.fetchone()[0] or 0

    cursor.execute(f"""
    SELECT category,SUM(amount)
    FROM {user_table}
    GROUP BY category
    ORDER BY SUM(amount) DESC
    LIMIT 1
    """)
    top_cat = cursor.fetchone()

    top_category = top_cat[0] if top_cat else "-"

    c1,c2,c3,c4 = st.columns(4)

    c1.metric("💰 Total Spent",f"₹{total_spent:,.0f}")
    c2.metric("📅 This Month",f"₹{month_spent:,.0f}")
    c3.metric("📆 Today",f"₹{today_spent:,.0f}")
    c4.metric("🏆 Top Category",top_category)


    st.subheader("🏷 Category Wise Spending")

    cursor.execute(f"""
    SELECT category,SUM(amount)
    FROM {user_table}
    GROUP BY category
    ORDER BY SUM(amount) DESC
    """)

    cat_data = cursor.fetchall()

    if cat_data:
        df_cat = pd.DataFrame(cat_data,columns=["Category","Total"])
        df_cat["Total"] = df_cat["Total"].apply(lambda x:f"₹{x:,.0f}")
        st.dataframe(df_cat,use_container_width=True)


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
        amount = st.number_input("Amount ₹",min_value=1.0,step=10.0)
        description = st.text_input("Description")

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
        st.info("No expenses added yet")
        st.stop()

    df = pd.DataFrame(data,columns=["ID","Date","Amount","Category","Description"])
    total = df["Amount"].sum()

    st.metric("Total Spent",f"₹{total:,.0f}")


# ---------------- MONTHLY ----------------
    st.subheader("📅 Monthly Expense Report")

    cursor.execute(f"""
    SELECT strftime('%Y-%m',date) as Month,SUM(amount)
    FROM {user_table}
    GROUP BY Month
    ORDER BY Month DESC
    """)

    month_data = cursor.fetchall()

    df_month = pd.DataFrame(month_data,columns=["Month","Total"])
    df_month["Total"] = df_month["Total"].apply(lambda x:f"₹{x:,.0f}")
    st.dataframe(df_month,use_container_width=True)

    month_list = [row[0] for row in month_data]
    selected_month = st.selectbox("Select Month",month_list)

    cursor.execute(f"""
    SELECT id,date,amount,category,description
    FROM {user_table}
    WHERE strftime('%Y-%m',date)=?
    ORDER BY date DESC
    """,(selected_month,))

    month_rows = cursor.fetchall()

    if month_rows:
        st.subheader(f"📋 Expenses in {selected_month}")

        for row in month_rows:
            c1,c2,c3,c4,c5 = st.columns([2,1,2,3,1])

            c1.write(row[1])
            c2.write(f"₹{row[2]:,.0f}")
            c3.write(row[3])
            c4.write(row[4])

            if c5.button("Delete",key=row[0]):
                cursor.execute(f"DELETE FROM {user_table} WHERE id=?",(row[0],))
                conn.commit()
                st.rerun()


# ---------------- DATE FILTER ----------------
    st.subheader("📆 Search by Date")

    selected_date = st.date_input("Select Date")

    cursor.execute(f"""
    SELECT date,amount,category,description
    FROM {user_table}
    WHERE date=?
    """,(str(selected_date),))

    day_rows = cursor.fetchall()

    if day_rows:
        df_day = pd.DataFrame(day_rows,columns=["Date","Amount","Category","Description"])
        df_day["Amount"] = df_day["Amount"].apply(lambda x:f"₹{x:,.0f}")
        st.dataframe(df_day,use_container_width=True)
    else:
        st.info("No expenses on this day")


# ---------------- YEARLY ----------------
    st.subheader("📆 Yearly Expense Report")

    cursor.execute(f"""
    SELECT strftime('%Y',date) as Year,SUM(amount)
    FROM {user_table}
    GROUP BY Year
    ORDER BY Year DESC
    """)

    year_data = cursor.fetchall()

    df_year = pd.DataFrame(year_data,columns=["Year","Total"])
    df_year["Total"] = df_year["Total"].apply(lambda x:f"₹{x:,.0f}")
    st.dataframe(df_year,use_container_width=True)


st.markdown("---")
st.caption("💰 Professional Expense Tracker (Streamlit + SQLite)")
