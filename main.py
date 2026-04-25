import os
import sqlite3
import pandas as pd
import streamlit as st
from langchain_groq import ChatGroq

# --- 1. SESSION STATE (The Engine's Memory) ---
if "chats" not in st.session_state:
    st.session_state.chats = [] # Archived chats
if "active_chat_index" not in st.session_state:
    st.session_state.active_chat_index = None # Current viewed history
if "current_messages" not in st.session_state:
    st.session_state.current_messages = [] # Active conversation

# --- CONFIG & PATHS ---
st.set_page_config(page_title="InsightSQL: Universal Pro", layout="wide", page_icon="🤖")
current_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_dir, "student.db")

# --- 2. SIDEBAR (History & Data Source) ---
with st.sidebar:
    st.header("⚙️ Data Connection")
    source_type = st.radio("Select Source:", ["Default Student DB", "Multi-CSV Upload"])
    
    uploaded_files = []
    if source_type == "Multi-CSV Upload":
        uploaded_files = st.file_uploader("Upload CSVs (Multiple allowed)", type="csv", accept_multiple_files=True)
        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)} Files Linked")

    st.divider()
    st.header("🕒 Chat History")
    
    # NEW CHAT LOGIC
    if st.button("➕ New Chat", use_container_width=True):
        if st.session_state.current_messages:
            title = st.session_state.current_messages[0]["content"][:20] + "..."
            st.session_state.chats.append({"title": title, "messages": st.session_state.current_messages})
        
        st.session_state.current_messages = []
        st.session_state.active_chat_index = None
        st.rerun()

    # RENDER HISTORY LIST
    for i, chat in enumerate(reversed(st.session_state.chats)):
        real_idx = len(st.session_state.chats) - 1 - i
        is_active = st.session_state.active_chat_index == real_idx
        if st.button(f"💬 {chat['title']}", key=f"chat_{real_idx}", 
                     use_container_width=True, type="primary" if is_active else "secondary"):
            st.session_state.current_messages = chat['messages']
            st.session_state.active_chat_index = real_idx
            st.rerun()

# --- 3. UNIVERSAL DATABASE ENGINE ---
def get_active_connection():
    if source_type == "Default Student DB":
        if os.path.exists(db_path):
            return sqlite3.connect(db_path), ["STUDENT"]
        return None, None
    
    elif source_type == "Multi-CSV Upload" and uploaded_files:
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        table_names = []
        for file in uploaded_files:
            df = pd.read_csv(file)
            t_name = file.name.split('.')[0].upper().replace(' ', '_')
            df.columns = [c.strip().replace(' ', '_') for c in df.columns]
            df.to_sql(t_name, conn, index=False)
            table_names.append(t_name)
        return conn, table_names
    return None, None

# --- 4. THE UNIVERSAL SEMANTIC AGENT ---
def get_unified_agent_response(user_query, table_names, conn):
    api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
    llm = ChatGroq(model_name="llama-3.3-70b-versatile", groq_api_key=api_key)
    
    master_schema = ""
    for t in table_names:
        cursor = conn.execute(f"SELECT * FROM {t} LIMIT 0")
        cols = [d[0] for d in cursor.description]
        master_schema += f"Table {t}: ({', '.join(cols)})\n"
    
    history_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.current_messages[-3:]])

    prompt = f"""
    You are a Universal Data Analyst. 
    Available Tables: {master_schema}
    Recent History: {history_context}
    
    [SEMANTIC RULES]:
    1. COUNTING: 'How many', 'Total number', 'Count', 'Strength' -> Use COUNT(*)
    2. SUPERLATIVES: 'Highest', 'Maximum', 'Top', 'Best' -> Use MAX() or ORDER BY DESC
    3. AMBIGUITY: 'Maximum number of students' means COUNT(*). 'Maximum marks' means MAX(MARKS).
    
    Instruction:
    - If greeting: Reply naturally.
    - If data request: Start with 'SQL_QUERY:' then 1 line of SQL, then a natural insight.
    """
    return llm.invoke(prompt).content.strip()

# --- 5. MAIN UI ---
st.title("🤖 InsightSQL: Universal Agent")
conn, active_tables = get_active_connection()

# Render History
for msg in st.session_state.current_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "sql" in msg: 
            with st.expander("🛠️ View SQL"):
                st.code(msg["sql"], language="sql")
        if "df" in msg: 
            st.dataframe(msg["df"], use_container_width=True)
        if "notes" in msg and msg["notes"]:
            with st.expander("🔍 View Analyst Insights"):
                st.info(msg["notes"])

# Chat Input
if user_input := st.chat_input("Ask anything about your data..."):
    st.session_state.current_messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"): 
        st.markdown(user_input)

    with st.chat_message("assistant"):
        if not conn:
            st.info("👈 Please connect a data source in the sidebar.")
        else:
            response = get_unified_agent_response(user_input, active_tables, conn)
            
            if "SQL_QUERY:" in response:
                try:
                    parts = response.split("SQL_QUERY:")
                    txt, sql = parts[0].strip(), parts[1].strip().split('\n')[0].replace(';', '') + ';'
                    df = pd.read_sql_query(sql, conn)
                    
                    if txt: st.write(txt)
                    with st.expander("🛠️ View SQL"):
                        st.code(sql, language="sql")
                    st.dataframe(df, use_container_width=True)
                    
                    # Analyst Section (Hidden in Dropdown)
                    analysis_notes = ""
                    if not df.empty:
                        with st.expander("🔍 View Analyst Insights"):
                            with st.spinner("Analyzing patterns..."):
                                try:
                                    api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
                                    llm_analyst = ChatGroq(model_name="llama-3.3-70b-versatile", groq_api_key=api_key)
                                    analysis_notes = llm_analyst.invoke(f"Data: {df.to_string()}\nAnalyze for: {user_input}").content.strip()
                                    st.info(analysis_notes)
                                except:
                                    analysis_notes = "Detailed insights currently unavailable."
                                    st.warning(analysis_notes)

                    st.session_state.current_messages.append({
                        "role": "assistant", "content": txt or "Result:", 
                        "sql": sql, "df": df, "notes": analysis_notes
                    })
                except Exception as e:
                    st.write("I found the query, but the data structure is unique. Could you try rephrasing?")
            else:
                st.write(response)
                st.session_state.current_messages.append({"role": "assistant", "content": response})