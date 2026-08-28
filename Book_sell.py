import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- Page Configuration ---
st.set_page_config(
    page_title="PJC Textbook Exchange",
    page_icon="📚",
    layout="wide"
)

# --- Direct Google Sheets Connection Setup ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_gspread_client():
    # Pulls credentials directly from st.secrets matching your TOML structure
    creds_dict = dict(st.secrets["connections"]["gsheets"])
    creds_dict.pop("spreadsheet", None)
    creds_dict.pop("type", None)
    
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client

def load_data():
    client = get_gspread_client()
    spreadsheet_url = "https://docs.google.com/spreadsheets/d/1nOYLY09PtuhZYuAEKED8Y5jSKTz1e4Bulh4mWtEsJbY/edit?gid=0#gid=0"
    sheet = client.open_by_url(spreadsheet_url).worksheet("Sheet1")
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def update_data(df):
    client = get_gspread_client()
    spreadsheet_url = "https://docs.google.com/spreadsheets/d/1nOYLY09PtuhZYuAEKED8Y5jSKTz1e4Bulh4mWtEsJbY/edit?gid=0#gid=0"
    sheet = client.open_by_url(spreadsheet_url).worksheet("Sheet1")
    
    # Clear and rewrite the sheet with updated dataframe values
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

if "books_db" not in st.session_state:
    try:
        st.session_state.books_db = load_data()
    except Exception as e:
        st.session_state.books_db = pd.DataFrame()
        st.error(f"Error loading initial data: {e}")

# --- Header Section with Logo ---
col_logo, col_title = st.columns([1, 5])

with col_logo:
    try:
        st.image("logo_pjc.png", width=110)
    except Exception:
        st.warning("Logo file not found. Please save 'logo_pjc.png' in the app directory.")

with col_title:
    title_color1 = "#2ca02c"
    title_color2 = "#1f77b4"
    st.markdown(f"<h1 style='color: {title_color1};'>Textbook Exchange Platform</h1>", unsafe_allow_html=True)
    st.markdown(f"<h1 style='color: {title_color1};'>Maintained by</h1>", unsafe_allow_html=True)
    st.markdown(f"<h1 style='color: {title_color2};'>Prabhu Jagatbandhu College</h1>", unsafe_allow_html=True)
    #st.title("Prabhu Jagatbandhu College")
    st.subheader("Campus Textbook Exchange Programme")
    st.caption("© 2026 PJC Textbook Exchange. All rights reserved.")

st.markdown(
    "Welcome to the official peer-to-peer textbook marketplace for students. "
    "Pass down your old books to juniors at affordable prices and buy what you need directly from your seniors!"
	"  " "© 2026 PJC Textbook Exchange. All rights reserved."
)
st.divider()

# --- Sidebar Navigation ---
menu = st.sidebar.selectbox("Navigation", ["Browse Available Books", "List a Book for Sale", "About the Programme"])

# ==========================================
# 1. BROWSE & MARK AS SOLD SECTION
# ==========================================
if menu == "Browse Available Books":
    st.header("📖 Browse Available Textbooks")
    
    try:
        st.session_state.books_db = load_data()
    except Exception:
        pass
        
    df = st.session_state.books_db
    
    if df is None or df.empty or "Status" not in df.columns:
        st.info("No books are currently listed.")
    else:
        # Filter dataframe to show ONLY available books for students
        available_df = df[df["Status"].astype(str).str.lower() == "available"]
        
        if available_df.empty:
            st.info("No active books available right now. Check back later or list your old book!")
        else:
            # Search & Filters
            col1, col2, col3 = st.columns(3)
            
            with col1:
                search_query = st.text_input("🔍 Search by Title or Author", "").lower()
            with col2:
                departments = ["All"] + sorted(available_df["Department"].dropna().unique().tolist())
                selected_dept = st.selectbox("Filter by Department", departments)
            with col3:
                semesters = ["All"] + sorted(available_df["Semester"].dropna().unique().tolist())
                selected_sem = st.selectbox("Filter by Semester", semesters)
                
            filtered_df = available_df.copy()
            
            if search_query:
                filtered_df = filtered_df[
                    filtered_df["Title"].astype(str).str.lower().str.contains(search_query, na=False) | 
                    filtered_df["Author"].astype(str).str.lower().str.contains(search_query, na=False)
                ]
            if selected_dept != "All":
                filtered_df = filtered_df[filtered_df["Department"] == selected_dept]
            if selected_sem != "All":
                filtered_df = filtered_df[filtered_df["Semester"] == selected_sem]
                
            st.markdown(f"### Showing {len(filtered_df)} available book(s)")
            
            # Display Listings with "Mark as Sold" Option
            for index, row in filtered_df.iterrows():
                with st.container():
                    col_a, col_b, col_c = st.columns([2.5, 1.2, 1])
                    with col_a:
                        st.markdown(f"#### {row['Title']} by *{row['Author']}*")
                        st.caption(f"**Department:** {row['Department']} | **Semester:** {row['Semester']} | **Condition:** {row['Condition']}")
                        st.write(f"🏷️ **Price:** ₹{row['Price (₹)']}")
                    with col_b:
                        st.markdown(f"**Seller:** {row['Seller Name']}")
                        st.info(f"📱 Contact:\n`{row['Contact (WhatsApp/Email)']}`")
                    with col_c:
                        st.markdown("### ") 
                        # Update Status to "Sold" using direct update handler
                        if st.button("Mark as Sold", key=f"sold_{index}"):
                            try:
                                full_df = load_data()
                                full_df.at[index, "Status"] = "Sold"
                                update_data(full_df)
                                st.session_state.books_db = full_df
                                st.success("Book marked as sold! Record preserved in college archive.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error updating status: {e}")
                    st.divider()

# ==========================================
# 2. LIST A BOOK SECTION
# ==========================================
elif menu == "List a Book for Sale":
    st.header("📝 Sell Your Old Textbooks")
    
    with st.form("book_list_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("Book Title*")
            author = st.text_input("Author / Publisher*")
            department = st.selectbox("Department / Stream*", [
                "Physics", "Mathematics", "Chemistry", "Computer Science","Zoology", "Botany", "Food & Nutrition", "Electronics", 
                "Bengali", "English", "History", "Geography", "Philosophy", "Physical Education", "Sanskrit", "Education", "Sociology", 			"Commerce / Accountancy", "General / Other"
            ])
            semester = st.selectbox("Target Semester*", [
                "1st Semester", "2nd Semester", "3rd Semester", 
                "4th Semester", "5th Semester", "6th Semester",
		"7th Semester", "8th Semester"
            ])
            
        with col2:
            price = st.number_input("Expected Price (₹)*", min_value=0, step=10, value=100)
            condition = st.selectbox("Book Condition*", ["Like New", "Good", "Fair / Heavily Used"])
            seller_name = st.text_input("Your Full Name*")
            contact = st.text_input("Your WhatsApp Number or Email*", placeholder="e.g., 9876543210 or email@domain.com")
            
        submitted = st.form_submit_button("Post Listing")
        
        if submitted:
            if not title or not author or not seller_name or not contact:
                st.error("Please fill in all required fields.")
            else:
                try:
                    current_df = load_data()
                    new_entry = pd.DataFrame([{
                        "Status": "Available",
                        "Title": title,
                        "Author": author,
                        "Department": department,
                        "Semester": semester,
                        "Price (₹)": price,
                        "Condition": condition,
                        "Seller Name": seller_name,
                        "Contact (WhatsApp/Email)": contact,
                        "Date Posted": datetime.now().strftime("%Y-%m-%d")
                    }])
                    
                    updated_df = pd.concat([current_df, new_entry], ignore_index=True)
                    update_data(updated_df)
                    st.session_state.books_db = updated_df
                    
                    st.success("🎉 Success! Your book has been listed.")
                    st.balloons()
                except Exception as e:
                    st.error(f"Failed to save listing: {e}")

# ==========================================
# 3. ABOUT SECTION
# ==========================================
else:
    st.header("ℹ️ About PJC Textbook Exchange")
    st.write("The Campus Textbook Exchange Programme helps PJC students save money by reusing books sustainably.")

# --- Footer ---
st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>Prabhu Jagatbandhu College • Student Welfare Initiative</p>", unsafe_allow_html=True)
