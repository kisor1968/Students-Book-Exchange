import base64
from datetime import datetime
from io import BytesIO
import random
import re
from zoneinfo import ZoneInfo
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import qrcode
import streamlit as st

# --- Page Configuration ---
st.set_page_config(
    page_title="PJC Textbook Exchange", page_icon="📚", layout="wide"
)


def set_background(image_file):
  try:
    with open(image_file, "rb") as f:
      encoded_string = base64.b64encode(f.read()).decode()
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpeg;base64,{encoded_string}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        [data-testid="stHeader"] {{
            background-color: rgba(0,0,0,0) !important;
        }}
        .main {{
            background-color: transparent !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
  except Exception:
    pass


set_background("background.png")

# --- Direct Google Sheets Connection Setup ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

wb_districts = [
    "Alipurduar",
    "Arambagh",
    "Bankura",
    "Basirhat",
    "Birbhum",
    "Cooch Behar",
    "Dakshin Dinajpur",
    "Darjeeling",
    "Hooghly",
    "Howrah",
    "Jalpaiguri",
    "Jangipur",
    "Jhargram",
    "Kalimpong",
    "Kolkata",
    "Malda",
    "Murshidabad",
    "Nadia",
    "North 24 Parganas",
    "Paschim Bardhaman",
    "Paschim Medinipur",
    "Purba Bardhaman",
    "Purba Medinipur",
    "Purulia",
    "South 24 Parganas",
    "Sundarban",
    "Uttar Dinajpur",
]

departments_list = sorted([
    "Physics",
    "Mathematics",
    "Chemistry",
    "Computer Science",
    "Zoology",
    "Botany",
    "Anthropology",
    "Food & Nutrition",
    "Electronics",
    "Bengali",
    "English",
    "History",
    "Geography",
    "Philosophy",
    "Physical Education",
    "Sanskrit",
    "Education",
    "Sociology",
    "Psychology",
    "Microbiology",
    "Biotechnology / Biochemistry",
    "Environmental Science",
    "Statistics",
    "Geology",
    "Journalism & Mass Communication",
    "Library & Information Science",
    "Urdu",
    "Hindi",
    "Arabic",
    "Law / B.A. LL.B.",
    "Business Administration (BBA)",
    "Commerce / Accountancy",
    "General / Other",
])

semesters_list = [
    "1st Semester",
    "2nd Semester",
    "3rd Semester",
    "4th Semester",
    "5th Semester",
    "6th Semester",
    "7th Semester",
    "8th Semester",
]


def contains_profanity(text):
  banned_words = [
      "sex",
      "porn",
      "xxx",
      "adult",
      "nude",
      "erotic",
      "gangbang",
      "rape",
      "slut",
      "whore",
      "fuck",
      "shit",
      "bitch",
  ]
  text_lower = text.lower()
  for word in banned_words:
    if word in text_lower:
      return True
  return False


def get_gspread_client():
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
  df = pd.DataFrame(data)
  if "Price (₹)" in df.columns:
    df["Price (₹)"] = (
        pd.to_numeric(df["Price (₹)"], errors="coerce").fillna(0).astype(int)
    )
  if "PIN" in df.columns:
    df["PIN"] = df["PIN"].astype(str)
  if "Secret Word" in df.columns:
    df["Secret Word"] = df["Secret Word"].astype(str)
  return df


def update_data(df):
  client = get_gspread_client()
  spreadsheet_url = "https://docs.google.com/spreadsheets/d/1nOYLY09PtuhZYuAEKED8Y5jSKTz1e4Bulh4mWtEsJbY/edit?gid=0#gid=0"
  sheet = client.open_by_url(spreadsheet_url).worksheet("Sheet1")
  sheet.update([df.columns.values.tolist()] + df.values.tolist(), "A1")


def load_reviews_data():
  try:
    client = get_gspread_client()
    spreadsheet_url = "https://docs.google.com/spreadsheets/d/1nOYLY09PtuhZYuAEKED8Y5jSKTz1e4Bulh4mWtEsJbY/edit?gid=0#gid=0"
    sheet = client.open_by_url(spreadsheet_url).worksheet("Reviews")
    data = sheet.get_all_records()
    return pd.DataFrame(data)
  except Exception:
    return pd.DataFrame(
        columns=[
            "Timestamp",
            "Name",
            "Department",
            "Rating",
            "Review / Suggestion",
        ]
    )


def append_review_data(new_row_df):
  client = get_gspread_client()
  spreadsheet_url = "https://docs.google.com/spreadsheets/d/1nOYLY09PtuhZYuAEKED8Y5jSKTz1e4Bulh4mWtEsJbY/edit?gid=0#gid=0"
  sheet = client.open_by_url(spreadsheet_url).worksheet("Reviews")
  existing_data = load_reviews_data()
  combined_df = pd.concat([existing_data, new_row_df], ignore_index=True)
  sheet.update(
      [combined_df.columns.values.tolist()] + combined_df.values.tolist(), "A1"
  )


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
    st.warning(
        "Logo file not found. Please save 'logo_pjc.png' in the app directory."
    )

with col_title:
  title_color1 = "#145A32"
  st.markdown(
      f"<h1 style='color: {title_color1}; margin-bottom: 0px;'>Textbook"
      " Exchange Platform</h1>",
      unsafe_allow_html=True,
  )
  st.markdown(
      '<p style="color: #8C6D36; font-style: italic; margin-bottom:'
      ' 2px;">Maintained by:</p>',
      unsafe_allow_html=True,
  )
  st.markdown(
      '<div style="color: #8C6D36; font-size: 32px; font-weight: bold; margin-top:'
      ' 0px;">Prabhu Jagatbandhu College</div>',
      unsafe_allow_html=True,
  )
  st.markdown(
      '<p style="color: #8C6D36; font-size: 16px; margin-top: -15px;">Andul-Mouri,'
      " Howrah, Pin- 711302</p>",
      unsafe_allow_html=True,
  )
  st.subheader("Campus Textbook Exchange Programme")

st.markdown(
    "Welcome to the official peer-to-peer textbook marketplace for students. "
    "Pass down your old books to juniors at affordable prices and buy what you"
    " need directly from your seniors!"
)
st.markdown(
    """<p style="color: #666666; font-size: 13px; text-align: center; margin-top: 30px;">© Dr. Kisor Mukhopadhyay, Prabhu Jagatbandhu College. All rights reserved.</p>""",
    unsafe_allow_html=True,
)
st.divider()

# --- Sidebar Sequential Radio Navigation ---
st.sidebar.header("Navigation")
menu = st.sidebar.radio(
    "Go to",
    [
        "About the Programme",
        "Browse available books",
        "List a book for sale",
        "App reviews and suggestions",
        "FAQ Chatbot",
    ],
)

# ==========================================
# 1. BROWSE, EDIT & MARK AS SOLD SECTION
# ==========================================
if menu == "Browse available books":
  st.header("📖 Browse Available Textbooks")

  try:
    st.session_state.books_db = load_data()
  except Exception:
    pass

  df = st.session_state.books_db

  if df is None or df.empty or "Status" not in df.columns:
    st.info("No books are currently listed.")
  else:
    available_df = df[df["Status"].astype(str).str.lower() == "available"]

    if available_df.empty:
      st.info(
          "No active books available right now. Check back later or list your"
          " old book!"
      )
    else:
      col1, col2, col3 = st.columns(3)

      with col1:
        search_query = st.text_input(
            "🔍 Search by Title, Author, or Institution", ""
        ).lower()
      with col2:
        departments = ["All"] + sorted(
            available_df["Department"].dropna().unique().tolist()
        )
        selected_dept = st.selectbox("Filter by Department", departments)
      with col3:
        semesters = ["All"] + sorted(
            available_df["Semester"].dropna().unique().tolist()
        )
        selected_sem = st.selectbox("Filter by Semester", semesters)

      filtered_df = available_df.copy()

      if search_query:
        filtered_df = filtered_df[
            filtered_df["Title"].astype(str).str.lower().str.contains(
                search_query, na=False
            )
            | filtered_df["Author"]
            .astype(str)
            .str.lower()
            .str.contains(search_query, na=False)
            | filtered_df["Institution"]
            .astype(str)
            .str.lower()
            .str.contains(search_query, na=False)
        ]
      if selected_dept != "All":
        filtered_df = filtered_df[filtered_df["Department"] == selected_dept]
      if selected_sem != "All":
        filtered_df = filtered_df[filtered_df["Semester"] == selected_sem]

      st.markdown(f"### Showing {len(filtered_df)} available book(s)")

      for index, row in filtered_df.iterrows():
        with st.container():
          col_a, col_b, col_c = st.columns([2.5, 1.2, 1])
          with col_a:
            st.markdown(
                f"#### {row['Title']} by <em>{row['Author']}</em>",
                unsafe_allow_html=True,
            )
            st.caption(
                f"**Department:** {row['Department']} | **Semester:**"
                f" {row['Semester']} | **Condition:** {row['Condition']}"
            )
            district_val = (
                row.get("District", "") if "District" in row else ""
            )
            inst_val = row.get("Institution", "") if "Institution" in row else ""
            if district_val or inst_val:
              st.caption(
                  f"📍 **District:** {district_val} | **Institution:**"
                  f" {inst_val}"
              )
            st.write(f"🏷️ **Price:** ₹{row['Price (₹)']}")

          with col_b:
            st.markdown(f"**Seller:** {row['Seller Name']}")
            st.info(f"📱 Contact:\n`{row['Contact (WhatsApp/Email)']}`")

          with col_c:
            st.markdown("### ")
            contact_info = str(row["Contact (WhatsApp/Email)"]).strip()

            parts = [p.strip() for p in contact_info.split(",")]
            phone_part = ""
            for part in parts:
              cleaned_digits = re.sub(r"\D", "", part)
              if len(cleaned_digits) >= 10:
                phone_part = cleaned_digits
                break

            if phone_part:
              clean_num = phone_part
              wa_num = "91" + clean_num if len(clean_num) == 10 else clean_num
              wa_text = f"Hi {row['Seller Name']}, I am interested in your textbook '{row['Title']}' listed on PJC Textbook Exchange."
              wa_url = (
                  f"https://wa.me/{wa_num}?text={wa_text.replace(' ', '%20')}"
              )

              if st.button(
                  "📱 WhatsApp QR", key=f"qr_btn_{index}", use_container_width=True
              ):
                st.session_state[f"show_qr_{index}"] = not st.session_state.get(
                    f"show_qr_{index}", False
                )

              if st.session_state.get(f"show_qr_{index}", False):
                st.markdown(
                    """
                            <div style="background-color: rgba(220, 225, 235, 0.65); padding: 8px; border-radius: 8px; border: 1px solid rgba(200, 205, 215, 0.8); text-align: center; margin-top: 5px; margin-bottom: 5px;">
                                <p style="margin: 0; font-size: 11px; color: #145A32; font-weight: bold;">SCAN TO CHAT</p>
                            </div>
                            """,
                    unsafe_allow_html=True,
                )
                img = qrcode.make(wa_url)
                buf = BytesIO()
                img.save(buf, format="PNG")
                st.image(buf.getvalue(), width=130, caption="Scan with phone")

            # --- EDIT LISTING BUTTON & LOGIC ---
            if st.button(
                "✏️ Edit Listing", key=f"edit_btn_{index}", use_container_width=True
            ):
              current_edit_state = st.session_state.get(
                  f"show_edit_box_{index}", False
              )
              st.session_state[f"show_edit_box_{index}"] = not current_edit_state
              st.session_state[f"show_pin_box_{index}"] = False
              st.session_state[f"show_forgot_box_{index}"] = False
              st.session_state[f"authorized_edit_{index}"] = False
              st.rerun()

            if st.session_state.get(f"show_edit_box_{index}", False):
              edit_pin = st.text_input(
                  "Enter PIN to Edit:",
                  type="password",
                  max_chars=4,
                  key=f"edit_pin_input_{index}",
              )
              if st.button("Verify & Edit", key=f"verify_edit_{index}"):
                saved_pin = str(row.get("PIN", "")).strip()
                if saved_pin and str(edit_pin).strip() == saved_pin:
                  st.session_state[f"authorized_edit_{index}"] = True
                  st.rerun()
                else:
                  st.error("Incorrect PIN!")

              if st.button("🔄 Forgot PIN?", key=f"forgot_edit_btn_{index}"):
                st.session_state[f"show_forgot_box_{index}"] = (
                    not st.session_state.get(
                        f"show_forgot_box_{index}", False
                    )
                )
                st.rerun()

            # --- MARK AS SOLD BUTTON & LOGIC ---
            if st.button(
                "🏷️ Mark as Sold", key=f"sold_{index}", use_container_width=True
            ):
              current_sold_state = st.session_state.get(
                  f"show_pin_box_{index}", False
              )
              st.session_state[f"show_pin_box_{index}"] = not current_sold_state
              st.session_state[f"show_edit_box_{index}"] = False
              st.session_state[f"show_forgot_box_{index}"] = False
              st.session_state[f"authorized_edit_{index}"] = False
              st.rerun()

            if st.session_state.get(f"show_pin_box_{index}", False):
              entered_pin = st.text_input(
                  "Enter Seller PIN:",
                  type="password",
                  max_chars=4,
                  key=f"pin_input_{index}",
              )
              if st.button("Confirm Sold", key=f"confirm_sold_{index}"):
                saved_pin = str(row.get("PIN", "")).strip()
                if saved_pin and str(entered_pin).strip() == saved_pin:
                  try:
                    full_df = load_data()
                    full_df.at[index, "Status"] = "Sold"
                    full_df["Price (₹)"] = (
                        pd.to_numeric(full_df["Price (₹)"], errors="coerce")
                        .fillna(0)
                        .astype(int)
                    )
                    full_df["PIN"] = full_df["PIN"].astype(str)
                    full_df["Secret Word"] = full_df["Secret Word"].astype(str)
                    update_data(full_df)
                    st.session_state.books_db = full_df
                    st.session_state[f"show_pin_box_{index}"] = False
                    st.success("Book successfully marked as sold!")
                    st.rerun()
                  except Exception as e:
                    st.error(f"Error updating status: {e}")
                else:
                  st.error("Incorrect PIN! Action denied.")

              if st.button("🔄 Forgot PIN?", key=f"forgot_sold_btn_{index}"):
                st.session_state[f"show_forgot_box_{index}"] = (
                    not st.session_state.get(
                        f"show_forgot_box_{index}", False
                    )
                )
                st.rerun()

            # --- SHARED SECRET RECOVERY BOX ---
            if st.session_state.get(f"show_forgot_box_{index}", False):
              st.markdown("---")
              secret_input = st.text_input(
                  "Enter your Secret Recovery Word:",
                  type="password",
                  key=f"secret_input_{index}",
                  placeholder="Set when you listed the book",
              )
              if st.button("Regenerate New PIN", key=f"do_reset_{index}"):
                actual_secret = str(row.get("Secret Word", "")).strip().lower()
                if (
                    secret_input.strip()
                    and secret_input.strip().lower() == actual_secret
                ):
                  new_random_pin = f"{random.randint(1000, 9999)}"
                  try:
                    full_df = load_data()
                    full_df.at[index, "PIN"] = str(new_random_pin)
                    full_df["Price (₹)"] = (
                        pd.to_numeric(full_df["Price (₹)"], errors="coerce")
                        .fillna(0)
                        .astype(int)
                    )
                    full_df["PIN"] = full_df["PIN"].astype(str)
                    full_df["Secret Word"] = full_df["Secret Word"].astype(str)
                    update_data(full_df)
                    st.session_state.books_db = full_df
                    st.success(
                        f"✅ Verified! Your new 4-digit PIN is:"
                        f" **{new_random_pin}**. Please save it securely!"
                    )
                    st.session_state[f"show_forgot_box_{index}"] = False
                  except Exception as e:
                    st.error(f"Error resetting PIN: {e}")
                else:
                  st.error("❌ Incorrect Secret Recovery Word! Access denied.")

          # --- FULL-WIDTH EDIT FORM ---
          if st.session_state.get(f"authorized_edit_{index}", False):
            st.markdown("---")
            with st.form(key=f"update_form_{index}"):
              st.markdown("### 📝 Edit Listing Details")
              form_col1, form_col2 = st.columns(2)

              with form_col1:
                new_title = st.text_input("Book Title", value=row["Title"])
                new_author = st.text_input(
                    "Author / Publisher", value=row["Author"]
                )

                curr_dept = (
                    row["Department"]
                    if row["Department"] in departments_list
                    else departments_list[0]
                )
                new_dept = st.selectbox(
                    "Department / Stream",
                    departments_list,
                    index=departments_list.index(curr_dept),
                )

                curr_sem = (
                    row["Semester"]
                    if row["Semester"] in semesters_list
                    else semesters_list[0]
                )
                new_sem = st.selectbox(
                    "Target Semester",
                    semesters_list,
                    index=semesters_list.index(curr_sem),
                )

                curr_dist = (
                    row["District"]
                    if "District" in row and row["District"] in wb_districts
                    else wb_districts[0]
                )
                new_dist = st.selectbox(
                    "District",
                    wb_districts,
                    index=wb_districts.index(curr_dist),
                )

              with form_col2:
                new_price = st.number_input(
                    "Expected Price (₹)",
                    min_value=0,
                    value=int(row["Price (₹)"])
                    if pd.notna(row["Price (₹)"])
                    else 100,
                )

                cond_options = ["Like New", "Good", "Fair / Heavily Used"]
                curr_cond = (
                    row["Condition"]
                    if row["Condition"] in cond_options
                    else cond_options[0]
                )
                new_cond = st.selectbox(
                    "Book Condition",
                    cond_options,
                    index=cond_options.index(curr_cond),
                )

                new_seller_name = st.text_input(
                    "Your Full Name", value=row["Seller Name"]
                )
                new_contact = st.text_input(
                    "Your WhatsApp Number or Email",
                    value=row["Contact (WhatsApp/Email)"],
                )
                new_inst = st.text_input(
                    "Institution / Other",
                    value=row.get("Institution", ""),
                )
                new_pin = st.text_input(
                    "Update 4-digit PIN",
                    value=str(row.get("PIN", "")),
                    type="password",
                    max_chars=4,
                )
                new_secret = st.text_input(
                    "Update Secret Recovery Word",
                    value=str(row.get("Secret Word", "")),
                    type="password",
                )

              update_submitted = st.form_submit_button(
                  "💾 Save All Changes", use_container_width=True
              )
              if update_submitted:
                try:
                  full_df = load_data()
                  full_df.at[index, "Title"] = new_title
                  full_df.at[index, "Author"] = new_author
                  full_df.at[index, "Department"] = new_dept
                  full_df.at[index, "Semester"] = new_sem
                  full_df.at[index, "District"] = new_dist
                  full_df.at[index, "Institution"] = new_inst
                  full_df.at[index, "Price (₹)"] = int(new_price)
                  full_df.at[index, "Condition"] = new_cond
                  full_df.at[index, "Seller Name"] = new_seller_name
                  full_df.at[index, "Contact (WhatsApp/Email)"] = new_contact

                  if new_pin.strip():
                    full_df.at[index, "PIN"] = str(new_pin).strip()
                  if new_secret.strip():
                    full_df.at[index, "Secret Word"] = (
                        str(new_secret).strip().lower()
                    )

                  full_df["Price (₹)"] = (
                      pd.to_numeric(full_df["Price (₹)"], errors="coerce")
                      .fillna(0)
                      .astype(int)
                  )
                  full_df["PIN"] = full_df["PIN"].astype(str)
                  full_df["Secret Word"] = full_df["Secret Word"].astype(str)

                  update_data(full_df)
                  st.session_state.books_db = full_df
                  st.success("Listing fully updated successfully!")
                  st.session_state[f"authorized_edit_{index}"] = False
                  st.session_state[f"show_edit_box_{index}"] = False
                  st.rerun()
                except Exception as e:
                  st.error(f"Error updating listing: {e}")

          st.divider()

# ==========================================
# 2. LIST A BOOK SECTION
# ==========================================
elif menu == "List a book for sale":
  st.header("📝 Sell Your Old Textbooks")

  with st.form("book_list_form"):
    col1, col2 = st.columns(2)

    with col1:
      title = st.text_input("Book Title*")
      author = st.text_input("Author / Publisher*")
      department = st.selectbox("Department / Stream*", departments_list)
      semester = st.selectbox("Target Semester*", semesters_list)
      district = st.selectbox("Select District*", options=wb_districts)
      seller_pin = st.text_input(
          "Set a 4-digit PIN to close/edit this listing*",
          type="password",
          max_chars=4,
          placeholder="e.g. 1234",
      )

    with col2:
      price = st.number_input(
          "Expected Price (₹)*", min_value=0, step=10, value=100
      )
      condition = st.selectbox(
          "Book Condition*", ["Like New", "Good", "Fair / Heavily Used"]
      )
      seller_name = st.text_input("Your Full Name*")
      contact = st.text_input(
          "Your WhatsApp Number or Email*",
          placeholder="e.g., 9876543210 or email@domain.com",
      )
      institution = st.text_input(
          "Institution / Other*",
          placeholder="e.g., Prabhu Jagatbandhu College",
      )
      secret_word = st.text_input(
          "Set a Secret Recovery Word (for password reset)*",
          type="password",
          placeholder="e.g., your pet's name or secret phrase",
      )

    submitted = st.form_submit_button("Post Listing")
    st.caption(
        "⚠️ Note: All listings are monitored. Uploading abusive, plagiarized,"
        " or inappropriate material will result in a permanent ban and reporting"
        " to college authorities."
    )

    if submitted:
      if (
          not title
          or not author
          or not seller_name
          or not contact
          or not institution
          or not seller_pin
          or not secret_word
      ):
        st.error(
            "Please fill in all required fields, including the PIN and Secret"
            " Recovery Word."
        )
      elif contains_profanity(title) or contains_profanity(author):
        st.error(
            "⚠️ Your submission contains prohibited or inappropriate language."
            " Please review and try again."
        )
      else:
        try:
          current_df = load_data()
          new_entry = pd.DataFrame([
              {
                  "Status": "Available",
                  "Title": title,
                  "Author": author,
                  "Department": department,
                  "Semester": semester,
                  "District": district,
                  "Institution": institution,
                  "Price (₹)": int(price),
                  "Condition": condition,
                  "Seller Name": seller_name,
                  "Contact (WhatsApp/Email)": contact,
                  "Date Posted": datetime.now(ZoneInfo("Asia/Kolkata")).strftime(
                      "%Y-%m-%d"
                  ),
                  "PIN": str(seller_pin).strip(),
                  "Secret Word": str(secret_word).strip().lower(),
              }
          ])

          updated_df = pd.concat([current_df, new_entry], ignore_index=True)
          updated_df["Price (₹)"] = (
              pd.to_numeric(updated_df["Price (₹)"], errors="coerce")
              .fillna(0)
              .astype(int)
          )
          updated_df["PIN"] = updated_df["PIN"].astype(str)
          updated_df["Secret Word"] = updated_df["Secret Word"].astype(str)

          update_data(updated_df)
          st.session_state.books_db = updated_df

          st.success(
              "🎉 Success! Your book has been listed securely with your PIN and"
              " Secret Recovery Word."
          )
          st.balloons()
        except Exception as e:
          st.error(f"Failed to save listing: {e}")

# ==========================================
# 3. REVIEWS & FEEDBACK SECTION
# ==========================================
elif menu == "App reviews and suggestions":
  st.header("💬 App Reviews & Modification Suggestions")
  st.write(
      "We'd love to hear your thoughts! Let us know how your experience has"
      " been or suggest new features you'd like to see added to this platform."
  )

  col_form, col_list = st.columns([1, 1.2], gap="large")

  with col_form:
    st.subheader("📝 Leave Your Feedback")
    with st.form("review_form"):
      rev_name = st.text_input("Your Name / Student ID*")
      rev_dept = st.selectbox("Your Department*", departments_list)
      rev_rating = st.selectbox(
          "Rating*",
          [
              "⭐⭐⭐⭐⭐ (5/5 - Excellent)",
              "⭐⭐⭐⭐ (4/5 - Very Good)",
              "⭐⭐⭐ (3/5 - Average)",
              "⭐⭐ (2/5 - Needs Improvement)",
              "⭐ (1/5 - Poor)",
          ],
      )
      rev_text = st.text_area(
          "Your Review or Suggested Modifications*",
          placeholder="Share what works well or what features should be added...",
      )

      review_submitted = st.form_submit_button("Submit Review")

      if review_submitted:
        if not rev_name.strip() or not rev_text.strip():
          st.error("Please fill in your name and review details.")
        elif contains_profanity(rev_text):
          st.error(
              "⚠️ Your feedback contains prohibited language. Please revise it."
          )
        else:
          try:
            ist_time = datetime.now(ZoneInfo("Asia/Kolkata")).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            new_review_df = pd.DataFrame([
                {
                    "Timestamp": ist_time,
                    "Name": rev_name.strip(),
                    "Department": rev_dept,
                    "Rating": rev_rating,
                    "Review / Suggestion": rev_text.strip(),
                }
            ])
            append_review_data(new_review_df)
            st.success(
                "🎉 Thank you! Your review and suggestions have been recorded."
            )
            st.balloons()
          except Exception as e:
            st.error(f"Failed to submit review: {e}")

  with col_list:
    st.subheader("⭐ Community Feedback & Suggestions")
    reviews_df = load_reviews_data()

    if reviews_df.empty:
      st.info("No reviews yet. Be the first to share your feedback!")
    else:
      for idx, r_row in reviews_df.iloc[::-1].iterrows():
        with st.container():
          st.markdown(
              f"**{r_row.get('Name', 'Anonymous')}** "
              f"({r_row.get('Department', 'General')}) —"
              f" *{r_row.get('Timestamp', '')}*"
          )
          st.markdown(f"**Rating:** {r_row.get('Rating', '')}")
          st.write(f"💭 {r_row.get('Review / Suggestion', '')}")
          st.divider()

# ==========================================
# 4. FAQ CHATBOT SECTION
# ==========================================
elif menu == "FAQ Chatbot":
  st.header("🤖 PJC Textbook Exchange Assistant")
  st.write(
      "Have questions about how to use the platform? Ask our assistant below!"
  )

  if "chatbot_messages" not in st.session_state:
    st.session_state.chatbot_messages = [
        {
            "role": "assistant",
            "content": (
                "Hello! I am your PJC Textbook Exchange guide. How can I help"
                " you today? You can ask me about listing books, finding"
                " textbooks, resetting PINs, or contacting sellers."
            ),
        }
    ]

  for message in st.session_state.chatbot_messages:
    with st.chat_message(message["role"]):
      st.markdown(message["content"])

  if user_query := st.chat_input(
      "Ask a question (e.g., 'How do I reset my PIN?')"
  ):
    st.session_state.chatbot_messages.append(
        {"role": "user", "content": user_query}
    )
    with st.chat_message("user"):
      st.markdown(user_query)

    query_lower = user_query.lower()
    bot_response = ""

    if any(
        kw in query_lower
        for kw in [
            "purpose",
            "what is",
            "about",
            "app do",
            "platform",
            "exchange",
        ]
    ):
      bot_response = (
          "The **PJC Textbook Exchange Platform** is a student welfare"
          " initiative maintained by Prabhu Jagatbandhu College. It helps"
          " students pass down their old textbooks to juniors at affordable"
          " prices or buy what they need directly from seniors sustainably!"
      )
    elif any(
        kw in query_lower for kw in ["list", "sell", "upload", "add book"]
    ):
      bot_response = (
          "To list a book for sale, go to the **'List a book for sale'** section"
          " from the sidebar. Fill out your book details, price, upload your"
          " WhatsApp number/email, and set a 4-digit PIN along with a Secret"
          " Recovery Word."
      )
    elif any(
        kw in query_lower for kw in ["pin", "forgot", "password", "recover"]
    ):
      bot_response = (
          "If you forgot your 4-digit PIN to mark a book as sold or edit it,"
          " go to **'Browse available books'**, click on your book's"
          " **'Mark as Sold'** or **'Edit Listing'** button, and click on"
          " **'🔄 Forgot PIN?'**. Enter your Secret Recovery Word to"
          " automatically generate a new PIN!"
      )
    elif any(
        kw in query_lower for kw in ["whatsapp", "chat", "contact", "qr"]
    ):
      bot_response = (
          "When browsing books, you can click the **'📱 WhatsApp QR'** button"
          " next to any listing. It will generate a custom QR code containing a"
          " pre-filled message that you can scan with your phone camera to"
          " chat directly with the seller on WhatsApp."
      )
    elif any(
        kw in query_lower for kw in ["sold", "remove", "status", "delete"]
    ):
      bot_response = (
          "To mark a book as sold, navigate to **'Browse available"
          " books'**, click **'Mark as Sold'** on your listing, and enter your"
          " 4-digit seller PIN to securely update its status."
      )
    elif any(kw in query_lower for kw in ["college", "prabhu", "pjc", "where"]):
      bot_response = (
          "This platform is maintained by **Prabhu Jagatbandhu College**"
          " (Andul-Mouri, Howrah, Pin-711302) as a student welfare initiative"
          " managed by Dr. Kisor Mukhopadhyay to help students pass down books"
          " sustainably."
      )
    else:
      bot_response = (
          "I'm not quite sure about that specific query. You can ask me"
          " questions about **what this app is**, **listing books**,"
          " **recovering your PIN**, **using WhatsApp QR codes**, or **marking"
          " books as sold**!"
      )

    st.session_state.chatbot_messages.append(
        {"role": "assistant", "content": bot_response}
    )
    with st.chat_message("assistant"):
      st.markdown(bot_response)

# ==========================================
# 5. ABOUT SECTION
# ==========================================
else:
  st.header("ℹ️ About PJC Textbook Exchange")
  st.write(
      "The Campus Textbook Exchange Programme helps PJC students save money by"
      " reusing books sustainably."
  )

# --- Footer ---
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: gray;'>Prabhu Jagatbandhu College •"
    " Student Welfare Initiative</p>",
    unsafe_allow_html=True,
)
