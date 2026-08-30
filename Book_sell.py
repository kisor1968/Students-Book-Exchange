import base64
from datetime import datetime
from io import BytesIO
import random
import re
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
  # Safely overwrite without clearing the entire sheet first to prevent data loss on error
  sheet.update([df.columns.values.tolist()] + df.values.tolist(), "A1")


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

# --- Sidebar Navigation ---
menu = st.sidebar.selectbox(
    "Navigation",
    ["Browse Available Books", "List a Book for Sale", "About the Programme"],
)

# ==========================================
# 1. BROWSE, EDIT & MARK AS SOLD SECTION
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

            # Display book image if available
            img_data = row.get("Book Image", "")
            if pd.notna(img_data) and str(img_data).strip():
              try:
                image_bytes = base64.b64decode(str(img_data))
                st.image(
                    image_bytes, width=150, caption="Book Condition Image"
                )
              except Exception:
                pass

          with col_b:
            st.markdown(f"**Seller:** {row['Seller Name']}")
            st.info(f"📱 Contact:\n`{row['Contact (WhatsApp/Email)']}`")

          with col_c:
            st.markdown("### ")
            contact_info = str(row["Contact (WhatsApp/Email)"]).strip()

            # Smart parsing to handle comma-separated contacts (e.g. email, phone)
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

              # --- FORGOT PIN FOR EDIT ---
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

              # --- FORGOT PIN FOR SOLD ---
              if st.button("🔄 Forgot PIN?", key=f"forgot_sold_btn_{index}"):
                st.session_state[f"show_forgot_box_{index}"] = (
                    not st.session_state.get(
                        f"show_forgot_box_{index}", False
                    )
                )
                st.rerun()

            # --- SHARED SECRET RECOVERY BOX (WORKS FOR BOTH) ---
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

              new_book_image = st.file_uploader(
                  "Upload New Book Condition Image (Optional - leaves current"
                  " image if empty)",
                  type=["png", "jpg", "jpeg"],
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

                  if new_book_image is not None:
                    img_bytes = new_book_image.getvalue()
                    if len(img_bytes) > 35000:
                      st.warning(
                          "⚠️ Image file is too large for Google Sheets storage"
                          " (limit ~35KB). Please upload a smaller or"
                          " compressed image."
                      )
                    else:
                      encoded_img = base64.b64encode(img_bytes).decode("utf-8")
                      full_df.at[index, "Book Image"] = encoded_img

                  if new_pin.strip():
                    full_df.at[index, "PIN"] = str(new_pin).strip()
                  if new_secret.strip():
                    full_df.at[index, "Secret Word"] = (
                        str(new_secret).strip().lower()
                    )

                  # Explicit dtype assignment to prevent type coercion mismatch
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
elif menu == "List a Book for Sale":
  st.header("📝 Sell Your Old Textbooks")

  with st.form("book_list_form"):
    col1, col2 = st.columns(2)

    with col1:
      title = st.text_input("Book Title*")
      author = st.text_input("Author / Publisher*")
      department = st.selectbox("Department / Stream*", departments_list)
      semester = st.selectbox("Target Semester*", semesters_list)
      district = st.selectbox("Select District*", options=wb_districts)

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
      seller_pin = st.text_input(
          "Set a 4-digit PIN to close/edit this listing*",
          type="password",
          max_chars=4,
          placeholder="e.g. 1234",
      )
      secret_word = st.text_input(
          "Set a Secret Recovery Word (for password reset)*",
          type="password",
          placeholder="e.g., your pet's name or secret phrase",
      )

    book_image = st.file_uploader(
        "Upload Book Condition Image (Optional)", type=["png", "jpg", "jpeg"]
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
          image_base64 = ""
          if book_image is not None:
            img_bytes = book_image.getvalue()
            if len(img_bytes) > 35000:
              st.error(
                  "❌ Image file is too large for Google Sheets storage (limit"
                  " ~35KB). Please upload a smaller image file."
              )
              st.stop()
            else:
              image_base64 = base64.b64encode(img_bytes).decode("utf-8")

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
                  "Date Posted": datetime.now().strftime("%Y-%m-%d"),
                  "PIN": str(seller_pin).strip(),
                  "Secret Word": str(secret_word).strip().lower(),
                  "Book Image": image_base64,
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
# 3. ABOUT SECTION
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
