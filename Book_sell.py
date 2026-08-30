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
  combined_df = pd.concat([existing_data, new_row_df], ignore
