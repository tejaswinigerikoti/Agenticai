import streamlit as st
import sqlite3
import matplotlib.pyplot as plt
from datetime import datetime, date
import hashlib
import os

# Page config
st.set_page_config(page_title="💰 Family Budget Tracker", layout="wide")

# Create DB
if not os.path.exists('budget.db'):
    open('budget.db', 'a').close()

# Session setup
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
    st.session_state.user_table = None
    st.session_state.add_success = False
    st.session_state.income_success = False
    st.session_state.monthly_income = 50000
    st.session_state.custom_categories = []

def login_page():
    st.markdown("## 👨‍👩‍👧‍👦 **Family Budget Planner**")
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

# Safe DB connection
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
    conn.commit()
    return conn

conn = get_user_connection()
user_table = st.session_state.user_table
cursor = conn.cursor()

# ---------------- MAIN DASHBOARD ----------------
st.title(f"💰 {st.session_state.user_email.split('@')[0]}'s **Family Budget**")

# Top metrics
cursor.execute(f"SELECT SUM(amount) FROM {user_table} WHERE type='expense'")
total_expense = cursor.fetchone()[0] or 0
cursor.execute(f"SELECT SUM(amount) FROM {user_table} WHERE type='income'")
total_income = cursor.fetchone()[0] or st.session_state.monthly_income
remaining = total_income - total_expense

col1, col2, col3 = st.columns(3)
col1.metric("💰 Spent", f"₹{total_expense:,.0f}")
col2.metric("💎 Left", f"₹{remaining:,.0f}")
col3.metric("💵 Salary", f"₹{st.session_state.monthly_income:,.0f}")

# Sidebar
st.sidebar.title(f"👨‍👩‍👧‍👦 {st.session_state.user_email}")
st.session_state.monthly_income = st.sidebar.slider("💰 Monthly Salary", 30000, 80000, 50000)
if st.sidebar.button("🚪 Logout"): 
    st.session_state.clear()
    st.rerun()

# CUSTOM CATEGORY MANAGEMENT
st.sidebar.subheader("🏷️ **Manage Categories**")
new_category = st.sidebar.text_input("➕ Add New Category", placeholder="EMI, Netflix...")
if st.sidebar.button("✅ Add Category") and new_category.strip():
    if new_category.strip() not in st.session_state.custom_categories:
        st.session_state.custom_categories.append(new_category.strip())
        st.sidebar.success(f"✅ Added: {new_category.strip()}")

# Show all categories
all_categories = [
    "🍚 Grocery", "🏠 Rent/House", "🚗 Petrol/Auto", "👨‍⚕️ Medical", 
    "👦 Kids School", "📱 Mobile/Recharge", "🍽️ Eating Out", "👗 Clothes",
    "💡 Electricity", "💧 Water Bill", "📺 Netflix/OTT", "🎯 EMI/Loan",
    "🚀 Milkman", "🧹 Maid", "🎪 Festival", "✈️ Travel"
] + st.session_state.custom_categories

menu = ["➕ Add Expense", "➕ Add Income", "📊 Dashboard", "🎯 Budget"]
choice = st.sidebar.selectbox("Choose:", menu)

# ---------------- ADD EXPENSE WITH CUSTOM CATEGORIES ----------------
def add_expense():
    st.subheader("➕ **Add Expense**")
    
    if st.session_state.get('add_success', False):
        st.success("✅ **Expense added successfully!**")
        st.session_state.add_success = False
    
    col1, col2 = st.columns([1,1])
    
    with col1:
        st.markdown("**📅 Date**")
        date_input = st.date_input("", value=date.today())
        
        st.markdown("**🏷️ Category** (20+ Options + Custom)")
        selected_cat = st.selectbox("", all_categories, key="expense_cat")
        
        # CUSTOM CATEGORY INLINE
        custom_cat = st.text_input("➕ Or type new:", placeholder="Ex: Amazon Shopping", key="custom_exp")
        final_category = custom_cat.strip() if custom_cat.strip() else selected_cat
    
    with col2:
        st.markdown("**💰 Amount**")
        amount = st.number_input("₹", min_value=10.0, step=50.0, format="%.0f")
        
        st.markdown("**📝 Details**")
        desc = st.text_input("", placeholder="Ex: Grocery from D-Mart")
    
    col1, col2 = st.columns(2)
    if col1.button("✅ Save Expense", type="primary", use_container_width=True):
        try:
            cursor.execute(f"INSERT INTO {user_table} (date, amount, category, description, type) VALUES(?,?,?,?,?)", 
                          (str(date_input), float(amount), final_category, desc, 'expense'))
            conn.commit()
            st.session_state.add_success = True
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error: {e}")

# ---------------- ADD INCOME ----------------
def add_income():
    st.subheader("💵 **Add Income**")
    
    if st.session_state.get('income_success', False):
        st.success("✅ **Income added!**")
        st.session_state.income_success = False
    
    col1, col2 = st.columns(2)
    with col1:
        date_input = st.date_input("📅 Date")
        income_type = st.selectbox("💼 Type", ["Salary", "Freelance", "Bonus", "Rent Income"])
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
    st.subheader("📊 **Spending Breakdown**")
    
    cursor.execute(f"SELECT category, SUM(amount) FROM {user_table} WHERE type='expense' GROUP BY category ORDER BY SUM(amount) DESC")
    data = cursor.fetchall()
    
    if data:
        categories, amounts = zip(*data[:8])  # Top 8
        fig, ax = plt.subplots(figsize=(12,8))
        colors = plt.cm.Pastel1(range(len(categories)))
        ax.pie(amounts, labels=categories, autopct='%1.1f%%', colors=colors)
        ax.set_title("Spending Pattern")
        st.pyplot(fig)
        plt.close(fig)
    
    # Recent expenses table
    st.subheader("📋 Recent Expenses")
    cursor.execute(f"SELECT date, amount, category, description FROM {user_table} WHERE type='expense' ORDER BY date DESC, amount DESC LIMIT 10")
    recent = cursor.fetchall()
    if recent:
        st.table(recent)

# ---------------- BUDGET ----------------
def budget():
    st.subheader("🎯 **50-30-20 Budget Rule**")
    
    budget_50 = st.session_state.monthly_income * 0.5  # Needs
    budget_30 = st.session_state.monthly_income * 0.3  # Wants  
    budget_20 = st.session_state.monthly_income * 0.2  # Savings
    
    cursor.execute(f"SELECT SUM(amount) FROM {user_table} WHERE type='expense'")
    total_spent = cursor.fetchone()[0] or 0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🏠 Needs 50%", f"₹{budget_50:,.0f}", f"₹{total_spent:,.0f}")
    col2.metric("🍽️ Wants 30%", f"₹{budget_30:,.0f}")
    col3.metric("💎 Save 20%", f"₹{budget_20:,.0f}")
    col4.metric("📊 Spent", f"₹{total_spent:,.0f}", f"{(total_spent/st.session_state.monthly_income)*100:.0f}%")

# ---------------- MAIN ----------------
if choice == "➕ Add Expense":
    add_expense()
elif choice == "➕ Add Income":
    add_income()
elif choice == "📊 Dashboard":
    dashboard()
elif choice == "🎯 Budget":
    budget()

st.markdown("─" * 80)
st.caption("👨‍👩‍👧‍👦 **Family Budget Tracker** | ➕ Custom Categories | 20+ Categories")
