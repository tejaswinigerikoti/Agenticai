import streamlit as st
import sqlite3
import matplotlib.pyplot as plt
import pandas as pd
from datetime import date
import hashlib
import os

# Page config
st.set_page_config(page_title="💰 Expense Tracker", layout="wide")

# Create DB
if not os.path.exists('expenses.db'):
    open('expenses.db', 'w').close()

# Session state
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
    st.session_state.user_table = None
    st.session_state.add_success = False

# Simple Login
def login_page():
    st.title("🔐 Login")
    col1, col2 = st.columns([3,1])
    
    with col1:
        email = st.text_input("📧 Email", placeholder="user@gmail.com")
        password = st.text_input("🔑 Password", type="password")
    
    with col2:
        st.info("**Demo:**\nuser@gmail.com\n123456")
    
    if st.button("🚀 Login", type="primary"):
        if email and password == "123456":
            st.session_state.user_email = email
            st.rerun()

if not st.session_state.user_email:
    login_page()
    st.stop()

# Database
user_id = hashlib.md5(st.session_state.user_email.encode()).hexdigest()[:8]
user_table = f"expenses_{user_id}"
st.session_state.user_table = user_table

conn = sqlite3.connect('expenses.db', check_same_thread=False)
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

# Main UI
st.title(f"💰 {st.session_state.user_email.split('@')[0]}'s Expenses")

# Sidebar
st.sidebar.title(f"👤 {st.session_state.user_email}")
if st.sidebar.button("🚪 Logout"):
    st.session_state.clear()
    st.rerun()

menu = ["➕ Add Expense", "📊 View Expenses"]
choice = st.sidebar.selectbox("Choose:", menu)

# ---------------- ADD EXPENSE ----------------
if choice == "➕ Add Expense":
    st.subheader("➕ Add New Expense")
    
    if st.session_state.get('add_success', False):
        st.success("✅ **Expense added successfully!**")
        st.session_state.add_success = False
    
    col1, col2 = st.columns(2)
    
    with col1:
        date_input = st.date_input("📅 Date", value=date.today())
        categories = ["Food", "Rent", "Transport", "Shopping", "Bills", "Medical", "EMI", "Other"]
        category = st.selectbox("🏷️ Category", categories)
        custom_cat = st.text_input("➕ Custom category:", placeholder="Ex: Netflix")
        final_category = custom_cat.strip() if custom_cat.strip() else category
    
    with col2:
        amount = st.number_input("💰 Amount ₹", min_value=1.0, step=10.0, format="%.0f")
        description = st.text_input("📝 Description", placeholder="Ex: Lunch at canteen")
    
    if st.button("✅ Save Expense", type="primary"):
        try:
            cursor.execute(f"INSERT INTO {user_table} (date, amount, category, description) VALUES(?,?,?,?)",
                          (str(date_input), float(amount), final_category, description))
            conn.commit()
            st.session_state.add_success = True
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error: {e}")

# ---------------- VIEW EXPENSES WITH DELETE + PIE CHART ----------------
elif choice == "📊 View Expenses":
    st.subheader("📊 All Expenses")
    
    cursor.execute(f"SELECT id, date, amount, category, description FROM {user_table} ORDER BY date DESC")
    rows = cursor.fetchall()
    
    if not rows:
        st.info("📭 **No expenses added yet!** Add some expenses first.")
        st.stop()
    
    # Total spent
    cursor.execute(f"SELECT SUM(amount) FROM {user_table}")
    total = cursor.fetchone()[0] or 0
    st.metric("💰 Total Spent", f"₹{total:,.0f}")
    
    # Table with DELETE column
    st.subheader("📋 Expenses Table")
    header_col1, header_col2, header_col3, header_col4, header_col5 = st.columns([1.5,1.2,1.5,2,0.8])
    header_col1.markdown("**Date**")
    header_col2.markdown("**Amount**")
    header_col3.markdown("**Category**")
    header_col4.markdown("**Description**")
    header_col5.markdown("**Delete**")
    st.markdown("─" * 80)
    
    for row in rows:
        col1, col2, col3, col4, col5 = st.columns([1.5,1.2,1.5,2,0.8])
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
    
    # PIE CHART
    st.subheader("📈 Category Breakdown")
    cursor.execute(f"SELECT category, SUM(amount) FROM {user_table} GROUP BY category ORDER BY SUM(amount) DESC")
    pie_data = cursor.fetchall()
    
    if pie_data:
        categories = [x[0] for x in pie_data]
        amounts = [x[1] for x in pie_data]
        
        col1, col2 = st.columns(2)
        with col1:
            fig, ax = plt.subplots(figsize=(6,6))
            ax.pie(amounts, labels=categories, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')
            ax.set_title("Expense Breakdown")
            st.pyplot(fig)
            plt.close(fig)
        
        with col2:
            for cat, amt in pie_data:
                pct = (amt/total)*100
                st.write(f"**{cat}**: ₹{amt:,.0f} ({pct:.1f}%)")

st.markdown("─" * 80)
st.caption("💰 **Expense Tracker** - Add, View, Delete + Pie Chart")
