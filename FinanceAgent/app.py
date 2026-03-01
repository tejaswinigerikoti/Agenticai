import streamlit as st
import sqlite3
import matplotlib.pyplot as plt
from datetime import datetime, date
import hashlib
import os

# Page config
st.set_page_config(page_title="💰 Middle Class Budget Tracker", layout="wide")

# Create DB
if not os.path.exists('budget.db'):
    open('budget.db', 'a').close()

# ---------------- MIDDLE CLASS SESSION SETUP ----------------
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
    st.session_state.user_table = None
    st.session_state.add_success = False
    st.session_state.monthly_income = 50000  # Default middle class salary

def login_page():
    st.markdown("## 👨‍👩‍👧‍👦 **Middle Class Budget Planner**")
    st.info("👨‍💼 **Salary**: ₹50,000/month | 🏠 **Rent**: ₹12,000 | 👨‍👩‍👧‍👦 **Family of 4**")
    
    col1, col2 = st.columns([3,1])
    with col1:
        email = st.text_input("📧 Email", placeholder="family@gmail.com")
        password = st.text_input("🔑 Password", type="password")
    with col2:
        st.info("**Demo:**\nfamily@gmail.com\n123456")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Start Budgeting", type="primary"):
            if email and password == "123456":
                st.session_state.user_email = email
                st.rerun()
    with col2:
        if st.button("👤 Quick Start"):
            st.session_state.user_email = f"family_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:6]}"
            st.rerun()

if not st.session_state.user_email:
    login_page()
    st.stop()

# ---------------- DATABASE ----------------
@st.cache_resource(ttl=600)
def get_user_connection():
    user_id = hashlib.md5(st.session_state.user_email.encode()).hexdigest()[:8]
    user_table = f"budget_{user_id}"
    st.session_state.user_table = user_table
    
    conn = sqlite3.connect('budget.db', check_same_thread=False, timeout=30)
    cursor = conn.cursor()
    
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {user_table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            amount REAL,
            category TEXT,
            description TEXT,
            type TEXT DEFAULT 'expense'
        )
    ''')
    
    # Default middle class categories
    default_cats = ["🍚 Grocery", "🏠 Rent/House", "🚗 Petrol/Auto", "👨‍⚕️ Medical", "👦 Kids School", 
                   "📱 Mobile/Recharge", "🍽️ Eating Out", "👗 Clothes", "💊 Medicine"]
    
    for cat in default_cats:
        cursor.execute(f"INSERT OR IGNORE INTO {user_table} (category, amount) VALUES (?, 0)", (cat,))
    
    conn.commit()
    return conn

conn = get_user_connection()
user_table = st.session_state.user_table

# ---------------- MAIN DASHBOARD ----------------
st.title(f"💰 {st.session_state.user_email.split('@')[0]}'s **Family Budget**")

# Top metrics - MIDDLE CLASS FOCUS
cursor = conn.cursor()
cursor.execute(f"SELECT SUM(amount) FROM {user_table} WHERE type='expense'")
total_expense = cursor.fetchone()[0] or 0

cursor.execute(f"SELECT SUM(amount) FROM {user_table} WHERE type='income'")
total_income = cursor.fetchone()[0] or st.session_state.monthly_income

remaining = total_income - total_expense
save_rate = (remaining/total_income)*100 if total_income > 0 else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Total Spent", f"₹{total_expense:,.0f}", f"₹{st.session_state.monthly_income:,.0f}")
col2.metric("💵 Salary", f"₹{total_income:,.0f}")
col3.metric("💎 Remaining", f"₹{remaining:,.0f}", delta=f"{save_rate:.1f}%")
col4.metric("🎯 Save Goal", "₹10,000", f"₹{max(0,10000-remaining):,.0f} left")

st.sidebar.title(f"👨‍👩‍👧‍👦 {st.session_state.user_email}")
st.sidebar.slider("💰 Monthly Salary", 30000, 80000, 50000, key="salary")
st.session_state.monthly_income = st.sidebar.slider("💰 Monthly Salary", 30000, 80000, 50000, key="salary")
if st.sidebar.button("🚪 Logout"): st.session_state.clear(); st.rerun()

menu = ["➕ Add Expense", "➕ Add Income", "📊 Dashboard", "🎯 Budget Planner"]
choice = st.sidebar.selectbox("Choose:", menu)

# ---------------- ADD EXPENSE ----------------
def add_expense():
    st.subheader("🥘 **Daily Expenses** (Grocery, Auto, Kids School)")
    
    if st.session_state.get('add_success', False):
        st.success("✅ **Added successfully!**")
        st.session_state.add_success = False
    
    col1, col2 = st.columns(2)
    with col1:
        date_input = st.date_input("📅 Date", value=date.today())
        cursor.execute(f"SELECT DISTINCT category FROM {user_table}")
        categories = [row[0] for row in cursor.fetchall()]
        category = st.selectbox("🏷️ Category", categories)
    
    with col2:
        amount = st.number_input("💰 Amount ₹", min_value=10.0, step=50.0, format="%.0f")
        desc = st.text_input("📝 What?", placeholder="Ex: Grocery from D-Mart")
    
    if st.button("✅ Save Expense", type="primary"):
        cursor.execute(f"INSERT INTO {user_table} (date, amount, category, description, type) VALUES(?,?,?,?,?)", 
                      (str(date_input), float(amount), category, desc, 'expense'))
        conn.commit()
        st.session_state.add_success = True
        st.rerun()

# ---------------- ADD INCOME ----------------
def add_income():
    st.subheader("💵 **Salary / Side Income**")
    
    if st.session_state.get('income_success', False):
        st.success("✅ **Income added!**")
        st.session_state.income_success = False
    
    col1, col2 = st.columns(2)
    with col1:
        date_input = st.date_input("📅 Salary Date")
        income_type = st.selectbox("💼 Type", ["Salary", "Freelance", "Bonus"])
    with col2:
        amount = st.number_input("💰 Amount ₹", min_value=1000.0, step=5000.0)
        desc = st.text_input("📝 Source")
    
    if st.button("✅ Add Income", type="primary"):
        cursor.execute(f"INSERT INTO {user_table} (date, amount, category, description, type) VALUES(?,?,?,?,?)", 
                      (str(date_input), float(amount), income_type, desc, 'income'))
        conn.commit()
        st.session_state.income_success = True
        st.rerun()

# ---------------- DASHBOARD ----------------
def dashboard():
    st.subheader("📊 **Monthly Spending Pattern**")
    
    # Category wise spending
    cursor.execute(f"SELECT category, SUM(amount) FROM {user_table} WHERE type='expense' GROUP BY category ORDER BY SUM(amount) DESC")
    data = cursor.fetchall()
    
    if data:
        categories, amounts = zip(*data)
        fig, ax = plt.subplots(figsize=(10,6))
        colors = plt.cm.Set3(range(len(categories)))
        ax.pie(amounts, labels=categories, autopct='%1.1f%%', colors=colors)
        ax.set_title("🍚 Grocery 32% | 🏠 Rent 24% | 🚗 Petrol 15%")
        st.pyplot(fig)
        plt.close()
    
    # Top 5 expenses table
    st.subheader("🔥 Top Expenses This Month")
    cursor.execute(f"SELECT date, amount, category, description FROM {user_table} WHERE type='expense' ORDER BY amount DESC LIMIT 5")
    top_expenses = cursor.fetchall()
    
    if top_expenses:
        st.dataframe(top_expenses, use_container_width=True)

# ---------------- BUDGET PLANNER ----------------
def budget_planner():
    st.subheader("🎯 **Middle Class Budget Rule** - 50-30-20")
    st.info("**50% Needs** (Rent, Grocery, Bills) | **30% Wants** (Eating Out) | **20% Savings**")
    
    cursor.execute(f"SELECT category, SUM(amount) FROM {user_table} WHERE type='expense' GROUP BY category")
    expenses = dict(cursor.fetchall())
    
    budget_50 = st.session_state.monthly_income * 0.5
    budget_30 = st.session_state.monthly_income * 0.3
    budget_20 = st.session_state.monthly_income * 0.2
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🏠 NEEDS (50%)", f"₹{budget_50:,.0f}", f"₹{expenses.get('Rent/House',0):,.0f}")
    with col2:
        st.metric("🍽️ WANTS (30%)", f"₹{budget_30:,.0f}", f"₹{expenses.get('Eating Out',0):,.0f}")
    with col3:
        st.metric("💎 SAVE (20%)", f"₹{budget_20:,.0f}", f"₹{budget_20-expenses.get('Savings',0):,.0f}")

# ---------------- MAIN MENU ----------------
if choice == "➕ Add Expense":
    add_expense()
elif choice == "➕ Add Income":
    add_income()
elif choice == "📊 Dashboard":
    dashboard()
elif choice == "🎯 Budget Planner":
    budget_planner()

st.markdown("─" * 80)
st.caption("👨‍👩‍👧‍👦 **Made for Middle Class Families** | 50-30-20 Rule | Family of 4")
