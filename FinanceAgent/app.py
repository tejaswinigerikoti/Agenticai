import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime
import hashlib
import os
import io

st.set_page_config(page_title="Expense Tracker", layout="wide")

DB_FILE = "expenses.db"
LOGIN_FILE = "login.txt"

# ---------------- AUTO LOGIN ----------------
if "user_email" not in st.session_state:
    if os.path.exists(LOGIN_FILE):
        with open(LOGIN_FILE, "r") as f:
            st.session_state.user_email = f.read().strip()
    else:
        st.session_state.user_email = None

# ---------------- DATABASE ----------------
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
email TEXT PRIMARY KEY,
password TEXT
)
""")
conn.commit()

# ---------------- LOGIN / REGISTER ----------------
def login_page():
    st.title("Expense Tracker")
    st.caption("Login or Register")

    option = st.radio("Select Option", ["Login", "Register"])
    email = st.text_input("Email")

    if option == "Register":
        new_pass = st.text_input("New Password", type="password")
        confirm_pass = st.text_input("Confirm Password", type="password")

        if st.button("Create Account"):
            if new_pass != confirm_pass:
                st.error("Passwords do not match")
            elif email == "" or new_pass == "":
                st.warning("Enter all details")
            else:
                cursor.execute("SELECT * FROM users WHERE email=?", (email,))
                if cursor.fetchone():
                    st.error("User already exists")
                else:
                    cursor.execute("INSERT INTO users(email,password) VALUES(?,?)", (email, new_pass))
                    conn.commit()
                    st.success("Account created! Please login.")

    if option == "Login":
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            cursor.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
            user = cursor.fetchone()

            if user:
                st.session_state.user_email = email
                with open(LOGIN_FILE, "w") as f:
                    f.write(email)
                st.rerun()
            else:
                st.error("Invalid Email or Password")

# If not logged in
if not st.session_state.user_email:
    login_page()
    st.stop()

# ---------------- USER ----------------
username = st.session_state.user_email.split("@")[0]

st.title("Expense Tracker Dashboard")
st.caption(f"Welcome, {username}")
st.divider()

# ---------------- USER DATABASE ----------------
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
    ["Dashboard", "Add Expense", "Reports", "Monthly Report", "Yearly Report", "Insights"]
)

# ---------------- DASHBOARD ----------------
if menu == "Dashboard":
    st.subheader("Dashboard Overview")

    cursor.execute(f"SELECT SUM(amount) FROM {user_table}")
    total_spent = cursor.fetchone()[0] or 0

    cursor.execute(f"""
    SELECT SUM(amount)
    FROM {user_table}
    WHERE strftime('%Y-%m',date)=strftime('%Y-%m','now')
    """)
    month_spent = cursor.fetchone()[0] or 0

    cursor.execute("SELECT budget FROM user_budget WHERE user=?", (user_id,))
    result = cursor.fetchone()

    if result:
        budget = result[0]
        st.success(f"Monthly Budget: ₹{budget}")

        percent = (month_spent / budget) * 100 if budget > 0 else 0
        st.progress(min(month_spent / budget, 1.0))
        st.write(f"Budget Used: {percent:.1f}%")

        with st.expander("Update Budget"):
            new_budget = st.number_input("Enter New Budget ₹", min_value=100.0, step=500.0)
            if st.button("Update Budget"):
                cursor.execute("UPDATE user_budget SET budget=? WHERE user=?", (new_budget, user_id))
                conn.commit()
                st.success("Budget Updated")
                st.rerun()
    else:
        st.warning("No budget set")
        new_budget = st.number_input("Set Monthly Budget ₹", min_value=100.0, step=500.0)
        if st.button("Save Budget"):
            cursor.execute("INSERT INTO user_budget(user,budget) VALUES(?,?)", (user_id, new_budget))
            conn.commit()
            st.success("Budget Saved")
            st.rerun()

    c1, c2 = st.columns(2)
    c1.metric("Total Spent", f"₹{total_spent:,.0f}")
    c2.metric("This Month", f"₹{month_spent:,.0f}")

# ---------------- ADD EXPENSE ----------------
if menu == "Add Expense":
    st.subheader("Add New Expense")

    col1, col2 = st.columns(2)

    with col1:
        expense_date = st.date_input("Date", value=date.today())
        category = st.selectbox("Category", ["Food", "Transport", "Shopping", "Bills", "Medical", "Other"])
        if category == "Other":
            category = st.text_input("Custom Category")

    with col2:
        amount = st.number_input("Amount ₹", min_value=1.0)
        description = st.text_input("Description")

    if st.button("Save Expense"):
        formatted_date = expense_date.strftime("%Y-%m-%d")
        cursor.execute(
            f"INSERT INTO {user_table} (date,amount,category,description) VALUES (?,?,?,?)",
            (formatted_date, amount, category, description)
        )
        conn.commit()
        st.success("Expense Added")

# ---------------- REPORTS ----------------
if menu == "Reports":
    st.subheader("All Expenses")

    cursor.execute(f"SELECT * FROM {user_table}")
    data = cursor.fetchall()

    if data:
        df = pd.DataFrame(data, columns=["ID", "Date", "Amount", "Category", "Description"])
        df = df.sort_values(by="ID", ascending=True).reset_index(drop=True)

        h1, h2, h3, h4, h5, h6 = st.columns([1,2,2,2,3,1])
        h1.write("S.No")
        h2.write("Date")
        h3.write("Amount")
        h4.write("Category")
        h5.write("Description")
        h6.write("Delete")
        st.write("---")

        for index, row in df.iterrows():
            c1, c2, c3, c4, c5, c6 = st.columns([1,2,2,2,3,1])

            c1.write(index + 1)
            formatted_date = datetime.strptime(row["Date"], "%Y-%m-%d").strftime("%d/%m/%Y")
            c2.write(formatted_date)
            c3.write(f"₹{row['Amount']}")
            c4.write(row["Category"])
            c5.write(row["Description"])

            if c6.button("🗑️", key=row["ID"]):
                cursor.execute(f"DELETE FROM {user_table} WHERE id=?", (row["ID"],))
                conn.commit()
                st.warning("Expense Deleted")
                st.rerun()

        # Excel Download
        st.write("---")
        df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%d/%m/%Y")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Expenses')

        st.download_button(
            "Download Excel",
            data=output.getvalue(),
            file_name="expenses.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    else:
        st.info("No data available")

    # Date filter
    st.subheader("Search by Date")
    selected_date = st.date_input("Select Date")

    cursor.execute(f"SELECT * FROM {user_table} WHERE date=?", (selected_date.strftime("%Y-%m-%d"),))
    rows = cursor.fetchall()

    if rows:
        df_day = pd.DataFrame(rows, columns=["ID", "Date", "Amount", "Category", "Description"])
        df_day["Date"] = pd.to_datetime(df_day["Date"]).dt.strftime("%d/%m/%Y")
        st.dataframe(df_day, use_container_width=True)
    else:
        st.info("No expenses on this date")

# ---------------- MONTHLY ----------------
if menu == "Monthly Report":
    st.subheader("Monthly Report")

    cursor.execute(f"""
    SELECT strftime('%Y-%m',date) as Month, SUM(amount)
    FROM {user_table}
    GROUP BY Month
    ORDER BY Month DESC
    """)
    data = cursor.fetchall()

    if data:
        df = pd.DataFrame(data, columns=["Month", "Total Spent"])
        df["Month"] = pd.to_datetime(df["Month"]).dt.strftime("%m/%Y")
        st.dataframe(df, use_container_width=True)

# ---------------- YEARLY ----------------
if menu == "Yearly Report":
    st.subheader("Yearly Report")

    cursor.execute(f"""
    SELECT strftime('%Y',date) as Year, SUM(amount)
    FROM {user_table}
    GROUP BY Year
    ORDER BY Year DESC
    """)
    data = cursor.fetchall()

    if data:
        df = pd.DataFrame(data, columns=["Year", "Total Spent"])
        st.dataframe(df, use_container_width=True)

# ---------------- INSIGHTS ----------------
if menu == "Insights":
    st.subheader("Spending Insights")

    cursor.execute(f"SELECT category,SUM(amount) FROM {user_table} GROUP BY category")
    data = cursor.fetchall()

    if data:
        df = pd.DataFrame(data, columns=["Category", "Total"])
        total = df["Total"].sum()

        for _, row in df.iterrows():
            percent = (row["Total"] / total) * 100
            st.write(f"{row['Category']} : {percent:.1f}%")

    st.subheader("Next Month Prediction")

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
