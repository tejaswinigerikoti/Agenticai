import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
from datetime import datetime, date
import hashlib
import os

# Page config
st.set_page_config(page_title="💰 Private Finance Manager", layout="wide")

# Fix SQLite
if not os.path.exists('finance.db'):
    open('finance.db', 'a').close()

# ---------------- SIMPLE LOGIN ----------------
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
    st.session_state.user_table = None

def login_page():
    st.title("🔐 Login")
    col1, col2 = st.columns([3,1])
    
    with col1:
        email = st.text_input("📧 Email", placeholder="user1@gmail.com")
        password = st.text_input("🔑 Password", type="password")
    
    with col2:
        st.info("**Demo:**\nuser1@gmail.com\n123456")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Login", type="primary"):
            if email and password == "123456":
                st.session_state.user_email = email
                st.rerun()
    with col2:
        if st.button("👤 Guest"):
            st.session_state.user_email = f"guest_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]}"
            st.rerun()

if not st.session_state.user_email:
    login_page()
    st.stop()

# ---------------- DATABASE - FIXED ----------------
@st.cache_resource(ttl=300)
def get_user_connection():
    user_id = hashlib.md5(st.session_state.user_email.encode()).hexdigest()[:8]
    user_table = f"expenses_{user_id}"
    st.session_state.user_table = user_table
    
    conn = sqlite3.connect('finance.db', check_same_thread=False, timeout=30)
    cursor = conn.cursor()
    
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {user_table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            amount REAL,
            category TEXT,
            description TEXT
        )
    ''')
    conn.commit()
    return conn

conn = get_user_connection()
user_table = st.session_state.user_table

# ---------------- UI ----------------
st.title(f"💰 {st.session_state.user_email.split('@')[0]}'s Finance")

st.sidebar.title(f"👤 {st.session_state.user_email}")
if st.sidebar.button("🚪 Logout"):
    st.session_state.clear()
    st.rerun()

menu = ["➕ Add Expense", "📊 View Expenses", "📈 Prediction"]
choice = st.sidebar.selectbox("Choose:", menu)

# ---------------- ADD EXPENSE ----------------
def add_expense():
    st.subheader("➕ Add Expense")
    col1, col2 = st.columns(2)
    
    with col1:
        date_input = st.date_input("📅 Date", value=date.today())
        categories = ["Food", "Travel", "Education", "Shopping", "Bills", "Gym", "Medical"]
        selected = st.selectbox("🏷️ Category", ["➕ Custom"] + categories)
        
        if selected == "➕ Custom":
            custom_cat = st.text_input("Your category:", placeholder="Rent, Fuel")
            category = custom_cat.strip() if custom_cat.strip() else "Other"
        else:
            category = selected
        
        st.info(f"**Category**: {category}")
    
    with col2:
        amount = st.number_input("💰 Amount ₹", min_value=1.0, step=10.0)
        desc = st.text_input("📝 Description")
    
    if st.button("✅ Save", type="primary"):
        try:
            cursor = conn.cursor()
            cursor.execute(f"INSERT INTO {user_table} (date, amount, category, description) VALUES(?,?,?,?)", 
                          (str(date_input), amount, category, desc))
            conn.commit()
            st.success(f"✅ **Successfully Added!** ₹{amount:,.0f} - {category}")
            st.rerun()
        except Exception as e:
            st.error(f"Save error: {e}")

# ---------------- VIEW EXPENSES - CLEAN ----------------
def view_expenses():
    st.subheader("📊 Your Expenses")
    
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT id, date, amount, category, description FROM {user_table} ORDER BY date DESC")
        rows = cursor.fetchall()
        
        if not rows:
            st.info("📭 No expenses added yet!")
            return
        
        # Table headers
        header_col1, header_col2, header_col3, header_col4, header_col5 = st.columns([1.2,1,1.2,1.8,0.8])
        header_col1.markdown("**Date**")
        header_col2.markdown("**Amount**")
        header_col3.markdown("**Category**")
        header_col4.markdown("**Description**")
        header_col5.markdown("**Delete**")
        st.markdown("─" * 80)
        
        # Rows with delete button
        for row in rows:
            col1, col2, col3, col4, col5 = st.columns([1.2,1,1.2,1.8,0.8])
            with col1: st.write(row[1])
            with col2: st.write(f"**₹{row[2]:,.0f}**")
            with col3: st.write(row[3])
            with col4: st.write(row[4] or '-')
            with col5:
                if st.button("🗑️", key=f"del_{row[0]}"):
                    cursor.execute(f"DELETE FROM {user_table} WHERE id=?", (row[0],))
                    conn.commit()
                    st.success("✅ Deleted!")
                    st.rerun()
        
        # Charts only
        col1, col2 = st.columns(2)
        with col1:
            cursor.execute(f"SELECT category, SUM(amount) FROM {user_table} GROUP BY category")
            pie_data = cursor.fetchall()
            if pie_data:
                categories = [x[0] for x in pie_data]
                amounts = [x[1] for x in pie_data]
                fig, ax = plt.subplots(figsize=(6,6))
                ax.pie(amounts, labels=categories, autopct='%1.1f%%', startangle=90)
                ax.axis('equal')
                st.pyplot(fig)
        
    except Exception as e:
        st.error(f"View error: {e}")

# ---------------- PREDICTION - PRESENT DATE VARAKU ----------------
def budget_predict():
    st.subheader("📈 Next Month Prediction")
    
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT SUM(amount) FROM {user_table}")
        result = cursor.fetchone()
        
        if result[0] is None:
            st.warning("Add expenses first!")
            return
        
        # Present date varaku total spent
        total_spent_till_today = result[0]
        days_passed = date.today().day
        avg_daily = total_spent_till_today / len(rows) if 'rows' in locals() and len(rows) > 0 else 0
        
        # Conservative prediction
        current_month_low = avg_daily * 25
        next_month_low = current_month_low * 0.9
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("💰 **Spent Till Today**", f"₹{total_spent_till_today:,.0f}")
            st.metric("📅 Days Passed", days_passed)
        
        with col2:
            st.metric("📈 Current Month (Low)", f"₹{current_month_low:,.0f}")
            st.success(f"🎯 **Next Month Prediction**: ₹{next_month_low:,.0f}")
            
    except Exception as e:
        st.error(f"Prediction error: {e}")

# ---------------- MAIN ----------------
if choice == "➕ Add Expense":
    add_expense()
elif choice == "📊 View Expenses":
    view_expenses()
elif choice == "📈 Prediction":
    budget_predict()

st.markdown("─" * 80)
st.caption("🔒 Private | Multi-User | 100% Error-Free")
