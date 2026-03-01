import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
from datetime import datetime

# Page config
st.set_page_config(page_title="💰 Finance Manager", layout="wide")

# ---------------- DATABASE ----------------
@st.cache_resource
def init_db():
    conn = sqlite3.connect('finance.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS expenses(
        date TEXT,
        amount REAL,
        category TEXT,
        description TEXT
    )
    ''')
    conn.commit()
    return conn

conn = init_db()

# ---------------- APP TITLE ----------------
st.title("💰 Personal Finance Manager")
st.markdown("---")

# ---------------- SIDEBAR (Only Menu) ----------------
st.sidebar.title("📌 Navigation")
menu = ["Add Expense", "View Expenses", "Budget Prediction"]
choice = st.sidebar.selectbox("Menu", menu)

# ---------------- FUNCTIONS ----------------

def add_expense():
    st.subheader("➕ Add Daily Expense")
    cursor = conn.cursor() # Fixed NameError
    
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("📅 Date", datetime.now())
        category = st.selectbox("🏷️ Category", ["Food", "Travel", "Education", "Entertainment", "Shopping", "Bills", "Other"])
    with col2:
        amount = st.number_input("💰 Amount (₹)", min_value=0.0, step=10.0)
        description = st.text_input("📝 Description")
    
    if st.button("✅ Add Expense", type="primary"):
        cursor.execute("INSERT INTO expenses VALUES(?,?,?,?)", (str(date), amount, category, description))
        conn.commit()
        st.success("✅ Expense Added Successfully!")
        # st.balloons() - Removed as per your request

def view_expenses():
    st.subheader("📋 Expense Records")
    # Fetching data using connection
    data = pd.read_sql("SELECT * FROM expenses ORDER BY date DESC", conn)
    
    if not data.empty:
        st.dataframe(data, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            category_sum = data.groupby('category')['amount'].sum().sort_values(ascending=False)
            st.subheader("🏆 Category Wise Spending")
            fig, ax = plt.subplots()
            ax.pie(category_sum, labels=category_sum.index, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')
            st.pyplot(fig)
        
        with col2:
            total_spent = data['amount'].sum()
            avg_daily = data['amount'].mean()
            st.metric("💎 Total Spent", f"₹{total_spent:,.2f}")
            st.metric("📊 Avg Daily Spend", f"₹{avg_daily:.2f}")
    else:
        st.warning("📭 No expenses found. Add some expenses first!")

def budget_prediction():
    st.subheader("📈 Monthly Expense Prediction")
    data = pd.read_sql("SELECT * FROM expenses", conn)
    
    if not data.empty:
        total = data['amount'].sum()
        st.info(f"**Total Spending so far**: ₹{total:,.2f}")
        # Simple prediction logic (10% growth)
        predicted_next = total * 1.1
        st.success(f"**Predicted Next Month (Estimated)**: ₹{predicted_next:,.2f}")
    else:
        st.warning("📊 Add expenses to see trends!")

# ---------------- RUN SELECTED FUNCTION ----------------
if choice == "Add Expense":
    add_expense()
elif choice == "View Expenses":
    view_expenses()
elif choice == "Budget Prediction":
    budget_prediction()

# Footer
st.markdown("---")
st.caption("Simplified Finance Manager 🚀")
