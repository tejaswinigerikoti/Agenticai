import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import hashlib

st.set_page_config(page_title="💰 Finance Manager", layout="wide")

# ---------------- SIMPLE LOGIN ----------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None

if not st.session_state.logged_in:
    st.title("🔐 Login")
    col1, col2 = st.columns(2)
    
    with col1:
        email = st.text_input("Email", "user1@gmail.com")
        password = st.text_input("Password", type="password", value="123456")
    
    with col2:
        st.info("**Demo Login:**\nuser1@gmail.com\n123456")
    
    if st.button("Login"):
        st.session_state.logged_in = True
        st.session_state.user_id = hashlib.md5(email.encode()).hexdigest()[:8]
        st.rerun()
    st.stop()

# ---------------- DATABASE ----------------
def get_db():
    conn = sqlite3.connect('finance.db', check_same_thread=False)
    table_name = f"expenses_{st.session_state.user_id}"
    
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            amount REAL,
            category TEXT,
            description TEXT
        )
    """)
    conn.commit()
    return conn, table_name

conn, table_name = get_db()

# ---------------- UI ----------------
st.title("💰 Your Finance Tracker")
st.sidebar.write(f"👤 User: {st.session_state.user_id}")

tab1, tab2, tab3 = st.tabs(["➕ Add Expense", "📊 View Expenses", "📈 Budget"])

# ---------------- TAB 1: ADD EXPENSE ----------------
with tab1:
    st.subheader("➕ Add Expense")
    
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("Date", datetime.now())
        category = st.selectbox("Category", [
            "Food", "Travel", "Education", "Entertainment", 
            "Shopping", "Bills", "Gym", "Medical", "Fuel", 
            "Rent", "Netflix", "Other"
        ])
    
    with col2:
        amount = st.number_input("Amount (₹)", min_value=1.0, step=10.0)
        desc = st.text_input("Description")
    
    if st.button("✅ Save Expense", type="primary"):
        try:
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT INTO {table_name} (date, amount, category, description)
                VALUES (?, ?, ?, ?)
            """, (str(date), amount, category, desc))
            conn.commit()
            st.success("✅ **Expense Successfully Saved!** 🎉")
            st.balloons()
        except Exception as e:
            st.error(f"Error: {e}")

# ---------------- TAB 2: VIEW EXPENSES ----------------
with tab2:
    st.subheader("📊 Your Expenses")
    
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name} ORDER BY id DESC")
    rows = cursor.fetchall()
    
    if not rows:
        st.info("📭 No expenses added yet!")
    else:
        df = pd.DataFrame(rows, columns=['ID', 'Date', 'Amount', 'Category', 'Description'])
        
        # Beautiful table
        st.dataframe(
            df.style.format({'Amount': '₹{:,.0f}'}),
            use_container_width=True
        )
        
        # Delete buttons
        for row in rows:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"**{row[1]}** | ₹{row[2]:,.0f} | {row[3]}")
            with col2:
                if st.button("🗑️", key=f"del_{row[0]}"):
                    cursor.execute(f"DELETE FROM {table_name} WHERE id=?", (row[0],))
                    conn.commit()
                    st.success("Deleted!")
                    st.rerun()
        
        # Charts
        col1, col2 = st.columns(2)
        with col1:
            cat_spending = df.groupby('Category')['Amount'].sum()
            st.bar_chart(cat_spending)
        
        with col2:
            st.metric("Total Spent", f"₹{df['Amount'].sum():,.0f}")

# ---------------- TAB 3: BUDGET ----------------
with tab3:
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    
    if rows:
        df = pd.DataFrame(rows, columns=['ID', 'Date', 'Amount', 'Category', 'Description'])
        total = df['Amount'].sum()
        avg = df['Amount'].mean()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("💰 Total", f"₹{total:,.0f}")
            st.metric("📊 Average", f"₹{avg:,.0f}")
        with col2:
            st.success(f"📈 Monthly Estimate: ₹{total*1.1:,.0f}")

st.sidebar.button("🚪 Logout", on_click=lambda: st.session_state.clear())
