import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
from datetime import datetime
import requests
import json

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

# ---------------- AI CONFIGURATION ----------------
st.sidebar.title("🤖 AI Settings")
ai_provider = st.sidebar.selectbox("Select AI Provider", ["Groq (Cloud - Recommended)", "Ollama (Local)"])

if ai_provider == "Groq (Cloud - Recommended)":
    api_key = st.sidebar.text_input("Enter Groq API Key", type="password", help="Get it from https://console.groq.com/")
    model = "llama-3.3-70b-versatile"
else:
    ollama_url = st.sidebar.text_input("Ollama URL", value="http://localhost:11434")
    model = st.sidebar.selectbox("Model", ["llama3.2", "mistral", "gemma2:2b"])

def call_ai(prompt):
    """Universal AI Caller for both Groq and Ollama"""
    if ai_provider == "Groq (Cloud - Recommended)":
        if not api_key:
            st.warning("Please enter Groq API Key in sidebar")
            return None
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}]
            }
            response = requests.post(url, headers=headers, json=payload)
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            st.error(f"Groq Error: {str(e)}")
            return None
    else:
        try:
            url = f"{ollama_url}/api/chat"
            payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False}
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                return response.json()["message"]["content"]
            return None
        except Exception as e:
            st.error(f"Ollama connection failed: {str(e)}")
            return None

# ---------------- FUNCTION DEFINITIONS ----------------

def add_expense():
    st.subheader("➕ Add Daily Expense")
    cursor = conn.cursor() # Fixed NameError by defining cursor locally
    
    col1, col2 = st.columns([2, 1])
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
        st.balloons()

def view_expenses():
    st.subheader("📋 Expense Records")
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
        data['date'] = pd.to_datetime(data['date'])
        data['month'] = data['date'].dt.to_period('M')
        monthly_total = data.groupby('month')['amount'].sum()
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("### 📊 Monthly Expense Trend")
            fig, ax = plt.subplots(figsize=(8, 4))
            monthly_total.plot(kind='line', marker='o', linewidth=2, ax=ax)
            ax.set_title('Monthly Spending Trend', fontweight='bold')
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)
        
        with col2:
            try:
                current_month = monthly_total.iloc[-1]
                if len(monthly_total) > 1:
                    previous_month = monthly_total.iloc[-2]
                    growth_rate = (current_month - previous_month) / previous_month
                    predicted_next = current_month * (1 + growth_rate)
                    st.info(f"**Predicted Next Month**: ₹{predicted_next:,.2f}")
                else:
                    st.info(f"**Predicted Next Month (Est.)**: ₹{current_month * 1.1:,.2f}")
                st.success(f"**Current Month Total**: ₹{current_month:,.2f}")
            except Exception:
                st.error("Could not calculate prediction.")
    else:
        st.warning("📊 No data available for prediction.")

def agent_suggestion():
    st.subheader("🤖 AI-Powered Saving Suggestions")
    data = pd.read_sql("SELECT * FROM expenses", conn)
    
    if not data.empty:
        category_sum = data.groupby('category')['amount'].sum().sort_values(ascending=False)
        highest_category = category_sum.index[0]
        highest_amount = category_sum.iloc[0]
        total_spent = data['amount'].sum()
        
        st.metric("🏆 Highest Spending", f"{highest_category}", f"₹{highest_amount:,.2f}")
        
        prompt = f"""
        You are a personal finance expert in India. User spending analysis:
        - Highest category: {highest_category} (₹{highest_amount:.2f})
        - Total monthly spend: ₹{total_spent:.2f}
        Give 3 practical, actionable saving tips in Telugu and English.
        """
        
        if st.button("💡 Get AI Suggestions"):
            with st.spinner("🤖 Thinking..."):
                suggestion = call_ai(prompt)
                if suggestion:
                    st.success(suggestion)
    else:
        st.warning("📈 Add expenses to get AI suggestions!")

def ai_chat():
    st.subheader("💬 Finance Chat Assistant")
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    if prompt := st.chat_input("మీ ఖర్చుల గురించి అడగండి..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            data = pd.read_sql("SELECT * FROM expenses", conn)
            finance_summary = f"Total spent: ₹{data['amount'].sum():.2f}" if not data.empty else "No data"
            
            full_prompt = f"Context: {finance_summary}. User asks: {prompt}. Answer in Telugu/English friendly way."
            
            with st.spinner("Thinking..."):
                response = call_ai(full_prompt)
                if response:
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})

# ---------------- MAIN APP LOGIC ----------------
menu = ["Add Expense", "View Expenses", "Budget Prediction", "Agent Suggestion", "💬 AI Chat"]
choice = st.sidebar.selectbox("Menu", menu)

if choice == "Add Expense": add_expense()
elif choice == "View Expenses": view_expenses()
elif choice == "Budget Prediction": budget_prediction()
elif choice == "Agent Suggestion": agent_suggestion()
elif choice == "💬 AI Chat": ai_chat()

st.sidebar.markdown("---")
st.sidebar.info("Tip: Use Groq for 24/7 cloud access without local Ollama.")
