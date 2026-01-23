import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import re
import zlib
import json
import random
from datetime import datetime, timedelta, date
from difflib import SequenceMatcher
import time

# --------------------------------------------------
# 1. PAGE CONFIGURATION & STATE INITIALIZATION
# --------------------------------------------------
st.set_page_config(page_title="Student Timetable", page_icon="✨", layout="wide")

# Initialize Theme State
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'

# Initialize Bridge State for JS Communication
if 'venue_bridge' not in st.session_state:
    st.session_state.venue_bridge = ""
if 'last_processed_bridge' not in st.session_state:
    st.session_state.last_processed_bridge = ""
if 'active_slot_data' not in st.session_state:
    st.session_state.active_slot_data = None

def toggle_theme():
    st.session_state.theme = 'dark' if st.session_state.theme == 'light' else 'light'

# --------------------------------------------------
# 2. CONSTANTS & DATES
# --------------------------------------------------
DATA_FOLDER = "data"
TIMETABLE_FILE = "timetable_schedule.xlsx"
SEMESTER_START = date(2026, 1, 12)
SEMESTER_END = date(2026, 5, 7)

# --------------------------------------------------
# 3. DYNAMIC THEME STYLING
# --------------------------------------------------
light_theme = {
    "bg_color": "#f1f0f6",
    "text_color": "#2c3e50",
    "card_bg": "#ffffff",
    "card_shadow": "rgba(0,0,0,0.05)",
    "table_row_hover": "#f8f9fa",
    "secondary_btn_bg": "#ffffff",
    "secondary_btn_text": "#6a11cb",
    "game_bg": "#fcfcf4",
    "game_grid": "#e0dacc",
    "modal_bg": "#ffffff",
    "venue_card_bg": "#ffffff",
    "venue_border": "#e0e0e0"
}

dark_theme = {
    "bg_color": "#0e1117",
    "text_color": "#e0e0e0",
    "card_bg": "#1e1e1e",
    "card_shadow": "rgba(0,0,0,0.5)",
    "table_row_hover": "#2d2d2d",
    "secondary_btn_bg": "#1e1e1e",
    "secondary_btn_text": "#a18cd1",
    "game_bg": "#1a1a1a",
    "game_grid": "#333333",
    "modal_bg": "#262730",
    "venue_card_bg": "#2d2d2d",
    "venue_border": "#444"
}

current_theme = light_theme if st.session_state.theme == 'light' else dark_theme

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');

/* --- CSS VARIABLES --- */
:root {{
    --bg-color: {current_theme['bg_color']};
    --text-color: {current_theme['text_color']};
    --card-bg: {current_theme['card_bg']};
    --card-shadow: {current_theme['card_shadow']};
    --table-row-hover: {current_theme['table_row_hover']};
    --sec-btn-bg: {current_theme['secondary_btn_bg']};
    --sec-btn-text: {current_theme['secondary_btn_text']};
    --modal-bg: {current_theme['modal_bg']};
    --venue-card-bg: {current_theme['venue_card_bg']};
    --venue-border: {current_theme['venue_border']};
}}

/* BACKGROUND & GLOBAL FONT */
.stApp {{ background-color: var(--bg-color); }}

html, body, [class*="css"], .stMarkdown, div, span, p, h1, h2, h3, h4, h5, h6 {{
    font-family: 'Poppins', sans-serif;
    color: var(--text-color);
}}

/* --- SIDEBAR TOGGLE BUTTON --- */
.theme-btn {{
    border: 1px solid var(--text-color);
    background: transparent;
    color: var(--text-color);
    padding: 5px 10px;
    border-radius: 15px;
    cursor: pointer;
    font-size: 12px;
    margin-bottom: 10px;
}}

/* --- FIX 1: SIDEBAR TEXT VISIBILITY --- */
[data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] div, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
    color: var(--text-color) !important;
}}

/* --- FIX 2: TOOLTIP VISIBILITY --- */
div[data-baseweb="popover"], div[data-baseweb="tooltip"] {{
    background-color: var(--card-bg) !important;
    color: var(--text-color) !important;
    border: 1px solid rgba(128, 128, 128, 0.2) !important;
    box-shadow: 0 4px 15px var(--card-shadow) !important;
}}
div[data-baseweb="popover"] > div, div[data-baseweb="tooltip"] > div {{
    background-color: transparent !important;
    color: var(--text-color) !important;
}}

/* --- FIX: SIDEBAR DOWNLOAD BUTTON VISIBILITY --- */
[data-testid="stSidebar"] .stDownloadButton button {{
    border: 1px solid rgba(255,255,255,0.3) !important;
    background: transparent !important;
}}
[data-testid="stSidebar"] .stDownloadButton button * {{
    background: linear-gradient(90deg, #E0C3FC 0%, #8EC5FC 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    font-weight: 700 !important;
    font-size: 15px !important;
}}
[data-testid="stSidebar"] .stDownloadButton button:hover {{
    border-color: #8EC5FC !important;
    transform: translateY(-2px);
}}

/* --- INPUT BOXES --- */
div[data-baseweb="input"] {{
    border: none;
    border-radius: 50px !important;
    background-color: #262730; 
    padding: 8px 20px;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);
    color: white !important;
}}
div[data-baseweb="input"] input {{ color: white !important; caret-color: white; }}
div[data-testid="stDateInput"] input {{ color: #ffffff !important; font-weight: 600; }}

/* --- BUTTONS --- */
div.stButton > button {{
    width: 100% !important;
    height: 80px !important;        
    min-height: 80px !important;
    white-space: normal !important; 
    line-height: 1.2 !important;
    padding: 8px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    border-radius: 15px !important;
    font-size: 13px !important;       
    text-align: center !important;
}}

div.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%) !important;
    border: none !important; 
    font-weight: 700 !important;
    box-shadow: 0 4px 10px rgba(106, 17, 203, 0.2); 
    transition: transform 0.2s;
}}
div.stButton > button[kind="primary"] * {{ color: #ffffff !important; }}
div.stButton > button[kind="primary"]:hover {{ transform: translateY(-2px); box-shadow: 0 6px 15px rgba(106, 17, 203, 0.3); }}

div.stButton > button[kind="secondary"] {{
    background-color: var(--sec-btn-bg) !important; 
    color: var(--sec-btn-text) !important; 
    border: 2px solid #6a11cb !important; 
    font-weight: 600 !important;
}}
div.stButton > button[kind="secondary"]:hover {{ background-color: var(--table-row-hover) !important; }}

/* --- TIMETABLE GRID --- */
.timetable-wrapper {{ overflow-x: auto; padding: 20px 5px 40px 5px; }}
table.custom-grid {{ width: 100%; min-width: 1000px; border-collapse: separate; border-spacing: 10px; }}

.custom-grid th {{
    background: linear-gradient(90deg, #8EC5FC 0%, #E0C3FC 100%);
    color: #2c3e50; font-weight: 800; padding: 15px; border-radius: 15px;
    text-align: center; font-size: 18px; box-shadow: 0 4px 10px rgba(142, 197, 252, 0.4); border: none;
    text-transform: uppercase; letter-spacing: 1px;
}}
.custom-grid th:first-child {{ background: transparent; box-shadow: none; width: 140px; color: var(--text-color); }}

.custom-grid td:first-child {{
    background: linear-gradient(90deg, #8EC5FC 0%, #E0C3FC 100%);
    border-radius: 15px; font-size: 14px; font-weight: 800; color: #2c3e50;
    text-align: center; vertical-align: middle; box-shadow: 0 4px 10px rgba(142, 197, 252, 0.4);
    min-width: 140px; white-space: nowrap;
}}
.custom-grid td {{ vertical-align: top; height: 110px; padding: 0; border: none; }}
.time-label {{ color: #2c3e50 !important; }}

/* CARD & HOVER EFFECTS */
.class-card {{
    height: 100%; width: 100%; padding: 12px; box-sizing: border-box;
    display: flex; flex-direction: column; justify-content: center;
    border-radius: 18px; transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
    position: relative; cursor: default;
}}
.class-card.filled {{
    border: 1px solid rgba(255,255,255,0.4) !important;
    box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
    color: #2c3e50 !important;
}}
.class-card.filled div, .class-card.filled span, .class-card.filled p {{
    color: #2c3e50 !important; border: none !important; box-shadow: none !important;
}}
.class-card.filled:hover {{ transform: translateY(-5px) scale(1.03); box-shadow: 0 15px 30px rgba(0,0,0,0.15) !important; z-index: 100; }}

/* --- NEW EMPTY SLOT / BUTTON STYLE --- */
.type-empty {{ 
    background: var(--card-bg); 
    border: 2px dashed rgba(160, 160, 200, 0.3); 
    border-radius: 18px; 
    cursor: pointer; 
    display: flex; 
    flex-direction: column; 
    align-items: center; 
    justify-content: center;
    text-align: center;
    transition: all 0.2s;
    /* Prevent text selection so double click works properly */
    -webkit-user-select: none;
    -moz-user-select: none;
    -ms-user-select: none;
    user-select: none;
}}
.type-empty:hover {{
    border-color: #8EC5FC;
    background: var(--table-row-hover);
    transform: scale(0.98);
}}
.type-empty:active {{
    transform: scale(0.95);
    background-color: rgba(142, 197, 252, 0.1);
}}
.empty-title {{
    color: var(--text-color); opacity: 0.6; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-top: 5px;
}}
.empty-icon {{
    font-size: 28px; color: #8EC5FC; font-weight: 300; line-height: 1;
}}

.sub-title {{ font-weight: 700; font-size: 13px; margin-bottom: 4px; }}
.sub-meta {{ font-size: 11px; opacity: 0.9; }}
.batch-badge {{
    background: rgba(255,255,255,0.6); padding: 3px 8px; border-radius: 10px;
    font-size: 10px; font-weight: 700; text-transform: uppercase; display: inline-block;
    margin-bottom: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); color: #2c3e50 !important;
}}

/* 1.5 HOUR OFFSET STYLES */
.offset-wrapper {{ height: 100%; display: flex; flex-direction: column; }}
.offset-spacer {{ flex: 0 0 25%; min-height: 25%; }}
.offset-card-container {{ flex: 1; height: 100%; position: relative; }}
.class-card.offset-style {{ border-radius: 18px; height: 100% !important; }}

/* ATTENDANCE CARDS */
.metric-card {{
    background: var(--card-bg); border-radius: 20px; padding: 20px;
    box-shadow: 0 4px 15px var(--card-shadow); text-align: center;
    border: 1px solid rgba(128, 128, 128, 0.1); height: 100%; transition: transform 0.2s;
}}
.metric-card:hover {{ transform: translateY(-5px); }}
.metric-value {{
    font-size: 32px; font-weight: 800;
    background: -webkit-linear-gradient(45deg, #6a11cb, #2575fc);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}}
.metric-title {{ color: var(--text-color); font-weight: 600; }}
.metric-sub {{ color: var(--text-color); opacity: 0.7; font-size: 12px; }}

.daily-card {{
    background: var(--card-bg); border-radius: 18px; padding: 20px; margin-bottom: 15px;
    box-shadow: 0 4px 10px var(--card-shadow); display: flex; justify-content: space-between;
    align-items: center; border-left: 6px solid #6a11cb;
}}
.daily-info h4 {{ color: var(--text-color); margin: 0; font-weight: 700; }}
.daily-info p {{ color: var(--text-color); opacity: 0.8; margin: 0; font-size: 14px; }}

.student-card {{ 
    background: var(--card-bg); border-radius: 24px; padding: 30px; text-align: center; 
    margin-bottom: 30px; box-shadow: 0 10px 25px rgba(106, 17, 203, 0.1); 
}}
.student-name {{ 
    font-size: 28px; font-weight: 700; 
    background: -webkit-linear-gradient(45deg, #6a11cb, #2575fc); 
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 5px; 
}}
.student-meta {{ font-size: 15px; color: var(--text-color); opacity: 0.7; font-weight: 500; }}

/* --- EXPANDER HEADER --- */
[data-testid="stExpander"] summary p {{
    background: -webkit-linear-gradient(45deg, #ff9a44, #fc6076);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 18px !important;
    font-weight: 800 !important;
}}
[data-testid="stExpander"] summary svg {{ fill: var(--text-color) !important; color: var(--text-color) !important; }}

/* --- MODAL & VENUE CARDS --- */
div[data-testid="stDialog"] {{
    background-color: var(--modal-bg) !important;
    color: var(--text-color) !important;
}}

.venue-card-row {{ display: flex; flex-direction: column; gap: 12px; margin-top: 15px; }}
.venue-card {{
    background-color: var(--venue-card-bg); border: 1px solid var(--venue-border);
    border-radius: 16px; padding: 16px; display: flex; align-items: center; justify-content: space-between;
    box-shadow: 0 2px 8px rgba(0,0,0,0.03); transition: transform 0.2s;
}}
.venue-card:hover {{ transform: translateX(5px); border-color: #6a11cb; }}
.venue-left {{ display: flex; align-items: center; gap: 15px; }}
.venue-icon-box {{
    width: 45px; height: 45px; background: linear-gradient(135deg, #6a11cb 0%, #a18cd1 100%);
    border-radius: 12px; display: flex; align-items: center; justify-content: center;
    font-size: 20px; color: white;
}}
.venue-details {{ display: flex; flex-direction: column; }}
.venue-name {{ font-size: 18px; font-weight: 700; color: var(--text-color); }}
.venue-type {{ font-size: 11px; text-transform: uppercase; color: var(--text-color); opacity: 0.6; letter-spacing: 0.5px; font-weight: 600; }}
.venue-extras {{ font-size: 12px; color: var(--text-color); opacity: 0.8; margin-top: 4px; display: flex; gap: 10px; align-items: center; }}
.venue-capacity-badge {{
    background-color: #f0f2f6; color: #2c3e50; font-size: 12px; font-weight: 600;
    padding: 4px 10px; border-radius: 20px; display: flex; align-items: center; gap: 5px;
}}
[data-theme="dark"] .venue-capacity-badge {{ background-color: #333; color: #fff; }}

/* --- HIDDEN INPUT CSS --- */
div[data-testid="stTextInput"]:has(input[aria-label="venue_bridge_input"]) {{
    opacity: 0; height: 0px; width: 0px; overflow: hidden; margin: 0; padding: 0; position: absolute; z-index: -1;
}}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# 4. HELPERS
# --------------------------------------------------
SUBJECT_GRADIENTS = [
    "linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)", "linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%)",
    "linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%)", "linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%)",
    "linear-gradient(135deg, #fccb90 0%, #d57eeb 100%)", "linear-gradient(135deg, #fa709a 0%, #fee140 100%)",
    "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)", "linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)"
]

def get_subject_gradient(subject_name):
    if not subject_name: return SUBJECT_GRADIENTS[0]
    idx = zlib.adler32(subject_name.encode('utf-8')) % len(SUBJECT_GRADIENTS)
    return SUBJECT_GRADIENTS[idx]

def correct_subject_name(text):
    if pd.isna(text): return ""
    return str(text).replace("Quantun Physics", "Quantum Physics")

def clean_text(text): 
    if pd.isna(text): return ""
    return re.sub(r'[^a-z0-9]', '', str(text).lower())

def clean_mis(text):
    if pd.isna(text): return ""
    s = str(text).strip()
    return clean_text(s[:-2] if s.endswith(".0") else s)

def normalize_division(text):
    if pd.isna(text): return ""
    clean = str(text).lower()
    nums = re.findall(r'\d+', clean)
    return nums[0] if nums else clean.replace("division", "").replace("div", "").strip()

def normalize_batch(text):
    if pd.isna(text): return "all"
    clean = str(text).lower().replace(" ", "")
    if clean in ["-", "nan", "", "_"]: return "all"
    nums = re.findall(r'\d+', clean)
    return f"b{nums[0]}" if nums else "all"

def is_fuzzy_match(str1, str2):
    if str1 in str2 or str2 in str1: return True
    return SequenceMatcher(None, str1, str2).ratio() > 0.85

def parse_time(time_str):
    if pd.isna(time_str): return None, 1.0
    raw = str(time_str).upper().replace('.', ':').replace('-', ' ').replace('TO', ' ')
    times = re.findall(r'(\d{1,2}:\d{2})', raw)
    if not times: return None, 1.0
    start_str = times[0].lstrip("0")
    duration = 1.0 
    if len(times) >= 2:
        try:
            t1 = datetime.strptime(start_str, "%H:%M")
            t2 = datetime.strptime(times[1], "%H:%M")
            if t2 < t1: t2 += timedelta(hours=12)
            diff_mins = (t2 - t1).total_seconds() / 60
            if diff_mins > 20: duration = diff_mins / 60.0
        except: pass
    return start_str, duration

def map_to_slot(time_str, slots):
    try:
        t = datetime.strptime(time_str, "%H:%M")
        best, min_diff = None, 999
        for s in slots:
            slot_time = datetime.strptime(s, "%H:%M")
            diff = (t - slot_time).total_seconds() / 60
            if 0 <= diff <= 30:
                if diff < min_diff: min_diff, best = diff, s
        return best
    except: pass
    return None

# --- VENUE HELPER FUNCTIONS ---
@st.cache_data
def get_all_venues(sched_df):
    if sched_df is None: return set()
    cols = sched_df.columns
    t_venue_col = next((c for c in cols if "Venue" in c), None)
    if not t_venue_col: return set()
    venues = set()
    for _, row in sched_df.iterrows():
        v = str(row[t_venue_col]).strip()
        if v and v.lower() not in ['nan', '-', '', 'online']: venues.add(v)
    return venues

def get_free_venues_at_slot(day, slot_time_str, sched_df, all_venues):
    if sched_df is None or not all_venues: return []
    cols = sched_df.columns
    t_day_col = next((c for c in cols if "Day" in c), None)
    t_time_col = next((c for c in cols if "Time" in c), None)
    t_venue_col = next((c for c in cols if "Venue" in c), None)
    if not (t_day_col and t_time_col and t_venue_col): return []

    day_schedule = sched_df[sched_df[t_day_col].astype(str).str.title().str.strip() == day]
    occupied_venues = set()
    target_dt = datetime.strptime(slot_time_str, "%H:%M")
    target_end_dt = target_dt + timedelta(minutes=59) 

    for _, row in day_schedule.iterrows():
        start_str, dur_hours = parse_time(row[t_time_col])
        venue = str(row[t_venue_col]).strip()
        if start_str and venue and venue.lower() not in ['nan', '-', '']:
            try:
                class_start_dt = datetime.strptime(start_str, "%H:%M")
                if class_start_dt.hour < 8: class_start_dt += timedelta(hours=12)
                class_end_dt = class_start_dt + timedelta(minutes=int(dur_hours * 60))
                if class_start_dt < target_end_dt and class_end_dt > target_dt:
                    occupied_venues.add(venue)
            except: continue
    free_venues = list(all_venues - occupied_venues)
    free_venues.sort()
    return free_venues

# --- GOOGLE SHEETS & DATA ---
def get_google_client():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds)

def get_google_sheet(index=0):
    client = get_google_client()
    sheet_url = st.secrets["private_sheet_url"] 
    try:
        sh = client.open_by_url(sheet_url)
        if index >= len(sh.worksheets()): return sh.add_worksheet(title="Leaderboard", rows="1000", cols="4")
        return sh.get_worksheet(index)
    except Exception as e: return None

def load_attendance():
    try:
        sheet = get_google_sheet(0) 
        data = sheet.col_values(1)
        return {cls_id: True for cls_id in data if cls_id}
    except Exception as e: return {}

def update_attendance_in_sheet(cls_id, action):
    try:
        sheet = get_google_sheet(0) 
        if action == "add": sheet.append_row([cls_id])
        elif action == "remove":
            cell = sheet.find(cls_id)
            if cell: sheet.delete_rows(cell.row)
    except Exception as e: pass

def generate_master_ics(weekly_schedule, semester_end_date):
    day_map = { "Monday": "MO", "Tuesday": "TU", "Wednesday": "WE", "Thursday": "TH", "Friday": "FR", "Saturday": "SA", "Sunday": "SU" }
    ics_lines = [ "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//StudentPortal//MasterTimetable//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH" ]
    today = date.today()
    days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for cls in weekly_schedule:
        try:
            target_day_name = cls['Day'] 
            if target_day_name not in days_list: continue
            target_idx = days_list.index(target_day_name)
            current_idx = today.weekday()
            days_ahead = target_idx - current_idx if target_idx >= current_idx else 7 - (current_idx - target_idx)
            start_date = today + timedelta(days=days_ahead)
            start_h, start_m = map(int, cls['StartTime'].split(':'))
            if start_h < 8: start_h += 12
            dt_start = datetime.combine(start_date, datetime.min.time()).replace(hour=start_h, minute=start_m)
            dt_end = dt_start + timedelta(hours=cls.get('Duration', 1)) 
            fmt = "%Y%m%dT%H%M%S"
            until_str = semester_end_date.strftime("%Y%m%dT235959")
            rrule_day = day_map.get(target_day_name, "MO")
            event_block = [
                "BEGIN:VEVENT", f"SUMMARY:{cls['Subject']} ({cls['Type']})", f"DTSTART:{dt_start.strftime(fmt)}", f"DTEND:{dt_end.strftime(fmt)}",
                f"RRULE:FREQ=WEEKLY;BYDAY={rrule_day};UNTIL={until_str}", f"LOCATION:{cls['Venue']}", f"DESCRIPTION:Weekly {cls['Type']} session.",
                "BEGIN:VALARM", "TRIGGER:-PT15M", "ACTION:DISPLAY", "DESCRIPTION:Reminder", "END:VALARM", "END:VEVENT"
            ]
            ics_lines.extend(event_block)
        except: continue
    ics_lines.append("END:VCALENDAR")
    return "\n".join(ics_lines)

@st.cache_data(ttl=60)
def load_data():
    if not os.path.exists(DATA_FOLDER): return [], None, {}
    sub_dfs = []
    sched_df = None
    link_map = {} 
    for f in os.listdir(DATA_FOLDER):
        if not f.endswith(".xlsx"): continue
        path = os.path.join(DATA_FOLDER, f)
        try:
            df = pd.read_excel(path)
            df.columns = df.columns.astype(str).str.strip()
            if f.lower() == TIMETABLE_FILE.lower(): sched_df = df
            elif "link" in f.lower():
                for _, row in df.iterrows():
                    if len(row) >= 2: link_map[clean_text(correct_subject_name(row.iloc[0]))] = str(row.iloc[1]).strip()
            else: sub_dfs.append(df)
        except: continue
    return sub_dfs, sched_df, link_map

def get_schedule(mis, sub_dfs, sched_df):
    found_subs = []
    name, branch = "Unknown", "General"
    target_mis = clean_mis(mis)
    for df in sub_dfs:
        mis_col = next((c for c in df.columns if "MIS" in c.upper()), None)
        if not mis_col: continue
        df["_KEY"] = df[mis_col].apply(clean_mis)
        match = df[df["_KEY"] == target_mis]
        if not match.empty:
            row = match.iloc[0]
            if name == "Unknown":
                name = row.get(next((c for c in df.columns if "Name" in c), ""), "Student")
                branch = row.get(next((c for c in df.columns if "Branch" in c), ""), "General")
            sub_col = next((c for c in df.columns if "Subject" in c or "Title" in c), None)
            div_col = next((c for c in df.columns if "Division" in c), None)
            batch_col = next((c for c in df.columns if "Batch" in c or "BATCH" in c.upper()), None)
            if sub_col:
                found_subs.append({
                    "Subject": correct_subject_name(str(row[sub_col]).strip()),
                    "Division": str(row[div_col]).strip() if div_col else "",
                    "Batch": str(row[batch_col]) if batch_col else ""
                })
    timetable = []
    if sched_df is not None and found_subs:
        cols = sched_df.columns
        t_sub_col = next((c for c in cols if "Subject" in c or "Title" in c), None)
        t_div_col = next((c for c in cols if "Division" in c), None)
        t_batch_col = next((c for c in cols if "Batch" in c), None)
        t_type_col = next((c for c in cols if "Type" in c), None)
        t_time_col = next((c for c in cols if "Time" in c), None)
        t_day_col = next((c for c in cols if "Day" in c), None)
        t_venue_col = next((c for c in cols if "Venue" in c), None)
        for sub in found_subs:
            s_sub_clean = clean_text(sub['Subject'])
            s_div = normalize_division(sub['Division'])
            s_batch = normalize_batch(sub['Batch'])
            for _, row in sched_df.iterrows():
                if not is_fuzzy_match(s_sub_clean, clean_text(row[t_sub_col])): continue
                if normalize_division(row[t_div_col]) != s_div: continue
                t_batch = normalize_batch(row[t_batch_col]) if t_batch_col else "all"
                type_str = str(row[t_type_col]).lower() if t_type_col else ""
                is_lab = "lab" in type_str
                is_tutorial = "tutorial" in type_str
                is_batch_specific = is_lab or is_tutorial
                if (not is_batch_specific) or (t_batch == "all" or t_batch == s_batch):
                    start, dur_hours = parse_time(row[t_time_col])
                    if start:
                        row_span = int(dur_hours)
                        if dur_hours > 1.2 and dur_hours <= 2.2: row_span = 2
                        elif dur_hours > 2.2: row_span = 3 
                        is_offset = False
                        if ":00" in start or (dur_hours == 1.5): is_offset = True
                        display_type = "LAB" if is_lab else "TUTORIAL" if is_tutorial else "THEORY"
                        timetable.append({
                            "Day": str(row[t_day_col]).title().strip(), 
                            "StartTime": start, "Duration": row_span, "DurationFloat": dur_hours, "IsOffset": is_offset,
                            "Subject": sub['Subject'], "Type": display_type, "Venue": str(row[t_venue_col]) if t_venue_col else "-"
                        })
    return found_subs, timetable, name, branch

def render_grid(entries):
    slots = ["8:30", "9:30", "10:30", "11:30", "12:30", "1:30", "2:30", "3:30", "4:30", "5:30"]
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    grid = {s: {d: None for d in days} for s in slots}
    for e in entries:
        if e['Day'] in days:
            slot = map_to_slot(e['StartTime'], slots)
            if slot:
                grid[slot][e['Day']] = e
                if e['Duration'] > 1:
                    idx = slots.index(slot)
                    for i in range(1, e['Duration']):
                        if idx + i < len(slots): grid[slots[idx+i]][e['Day']] = "MERGED"
    html = '<div class="timetable-wrapper"><table class="custom-grid"><thead><tr><th>Time</th>' + ''.join([f'<th>{d}</th>' for d in days]) + '</tr></thead><tbody>'
    for s in slots:
        label = f"{s} - {str(int(s.split(':')[0])+1)}:{s.split(':')[1]}"
        html += f'<tr><td class="time-label">{label}</td>'
        for d in days:
            cell = grid[s][d]
            if cell == "MERGED": continue
            if cell:
                span = f'rowspan="{cell["Duration"]}"' if cell['Duration'] > 1 else ''
                grad = get_subject_gradient(cell['Subject'])
                if cell.get('IsOffset', False) and cell.get('DurationFloat', 1) == 1.5:
                     html += f'''<td {span} style="padding:0; vertical-align: top;"><div class="offset-wrapper"><div class="offset-spacer"></div><div class="offset-card-container"><div class="class-card filled offset-style" style="background:{grad}"><div class="batch-badge">{cell["Type"]} (1.5h)</div><div class="sub-title">{cell["Subject"]}</div><div class="sub-meta">📍 {cell["Venue"]} <br> ⏰ {cell["StartTime"]}</div></div></div></div></td>'''
                else:
                    html += f'<td {span}><div class="class-card filled" style="background:{grad}"><div class="batch-badge">{cell["Type"]}</div><div class="sub-title">{cell["Subject"]}</div><div class="sub-meta">📍 {cell["Venue"]}</div></div></td>'
            else:
                # NEW EMPTY SLOT DESIGN (BUTTON LIKE)
                html += f'''<td>
                    <div class="type-empty js-free-slot-trigger" data-day="{d}" data-time="{s}" title="Double click to find free classrooms">
                        <div class="empty-icon">+</div>
                        <div class="empty-title">Find Empty<br>Classrooms</div>
                    </div>
                </td>'''
        html += '</tr>'
    return html + '</tbody></table></div>'

def render_subject_html(subjects, link_map):
    # RESTORED SUBJECT UI (EXACT COPY FROM SOURCE)
    html_parts = ["""
    <div class="sub-alloc-wrapper"><table class="sub-alloc-table"><thead><tr><th style="width:40%">Subject Name</th><th style="width:20%">Batch</th><th style="width:20%">Division</th><th style="width:20%">Material</th></tr></thead><tbody>
    """]
    for sub in subjects:
        link = link_map.get(clean_text(sub.get('Subject')), "#")
        link_html = f'<a href="{link}" target="_blank" class="drive-btn">📂 Open Drive</a>' if link != "#" else "<span style='color:#aaa'>No Link</span>"
        html_parts.append(f"<tr><td>{sub.get('Subject')}</td><td>{sub.get('Batch')}</td><td>{sub.get('Division')}</td><td>{link_html}</td></tr>")
    html_parts.append("</tbody></table></div>")
    return "".join(html_parts)

def calculate_semester_totals(timetable_entries):
    totals = {}
    weekly_map = {}
    for entry in timetable_entries:
        d = entry['Day']
        if d not in weekly_map: weekly_map[d] = []
        weekly_map[d].append(entry)
        key = f"{entry['Subject']}|{entry['Type']}"
        totals[key] = 0
    curr_date = SEMESTER_START
    while curr_date <= SEMESTER_END:
        day_name = curr_date.strftime("%A")
        if day_name in weekly_map:
            for cls in weekly_map[day_name]:
                totals[f"{cls['Subject']}|{cls['Type']}"] += 1
        curr_date += timedelta(days=1)
    return totals

def render_game_html():
    bg_color = current_theme['game_grid'] 
    game_bg = "#fcfcf4"
    grid_line = "#e0dacc"
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <link href="https://fonts.googleapis.com/css2?family=Patrick+Hand&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; -webkit-touch-callout: none; -webkit-user-select: none; user-select: none; }}
        body {{ margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; height: 100vh; background-color: transparent; font-family: 'Patrick Hand', cursive; overflow: hidden; }}
        #game-container {{ position: relative; width: 100%; max-width: 400px; aspect-ratio: 2/3; max-height: 90vh; background-color: {game_bg}; background-image: linear-gradient({grid_line} 1px, transparent 1px), linear-gradient(90deg, {grid_line} 1px, transparent 1px); background-size: 15px 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); border-radius: 12px; overflow: hidden; touch-action: none; }}
        canvas {{ display: block; width: 100%; height: 100%; position: absolute; top: 0; left: 0; z-index: 20; pointer-events: none; touch-action: none; }}
        #ui-layer {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 10; pointer-events: none; }}
        .menu-screen {{ pointer-events: auto; }}
        #score-display {{ position: absolute; top: 10px; left: 20px; font-size: 32px; color: #888; font-weight: bold; transition: opacity 0.3s; }}
        .menu-screen {{ position: absolute; width: 100%; height: 100%; background: rgba(255,255,255, 0.95); display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }}
        #start-screen {{ top: 0; left: 0; transition: opacity 0.3s; }}
        #game-over-screen {{ left: 0; top: 100%; transition: top 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275); }}
        #game-over-screen.slide-up {{ top: 0% !important; }}
        .hidden {{ display: none !important; opacity: 0; }}
        .fade-out {{ opacity: 0; }}
        h1 {{ font-size: 42px; color: #d32f2f; margin: 0 0 10px 0; transform: rotate(-3deg); }}
        p {{ font-size: 20px; color: #444; margin: 5px 0; }}
        .btn {{ background: #fff; border: 2px solid #333; border-radius: 8px; padding: 12px 35px; font-family: 'Patrick Hand', cursive; font-size: 24px; color: #333; cursor: pointer; margin-top: 25px; box-shadow: 4px 4px 0px rgba(0,0,0,0.1); -webkit-tap-highlight-color: transparent; }}
        .btn:active {{ transform: scale(0.96); box-shadow: 2px 2px 0px rgba(0,0,0,0.1); background: #f4f4f4; }}
    </style>
</head>
<body>
<div id="game-container"><canvas id="gameCanvas" width="400" height="600"></canvas><div id="ui-layer"><div id="score-display">0</div><div id="start-screen" class="menu-screen"><h1>Doodle Jump</h1><p>Tap <b>Left</b> or <b>Right</b> side</p><button class="btn" onclick="startGame()">Play Now</button></div><div id="game-over-screen" class="menu-screen"><h1>Game Over!</h1><p>Score: <span id="final-score">0</span></p><p>Best: <span id="high-score">0</span></p><button class="btn" onclick="startGame()" style="margin-top:25px;">Play Again</button></div></div></div>
<script>
    const canvas = document.getElementById('gameCanvas'); const ctx = canvas.getContext('2d');
    const GRAVITY = 0.375; const JUMP_FORCE = -13.81; const MOVE_SPEED = 8.12; const GAME_W = 400; const GAME_H = 600;
    let lastTime = 0; const targetFPS = 60; const frameInterval = 1000 / targetFPS; 
    let platforms = [], brokenParts = [], score = 0; let highScore = localStorage.getItem('doodleHighScore') || 0; let gameRunning = false, isGameOverAnimating = false;
    const doodler = {{ x: GAME_W / 2 - 20, y: GAME_H - 150, w: 60, h: 60, vx: 0, vy: 0, dir: 1 }};
    const keys = {{ left: false, right: false }};
    window.addEventListener('keydown', e => {{ if(e.key==="ArrowLeft") keys.left=true; if(e.key==="ArrowRight") keys.right=true; }});
    window.addEventListener('keyup', e => {{ if(e.key==="ArrowLeft") keys.left=false; if(e.key==="ArrowRight") keys.right=false; }});
    canvas.addEventListener('touchmove', function(e) {{ e.preventDefault(); }}, {{ passive: false }});
    canvas.addEventListener('touchstart', function(e) {{ e.preventDefault(); }}, {{ passive: false }});
    const handleTouch = (e) => {{ if(e.touches.length === 0) return; const touch = e.touches[0]; const rect = canvas.getBoundingClientRect(); const touchX = touch.clientX - rect.left; const middle = rect.width / 2; if (touchX < middle) {{ keys.left = true; keys.right = false; }} else {{ keys.left = false; keys.right = true; }} }};
    canvas.addEventListener('touchstart', handleTouch, {{ passive: false }}); canvas.addEventListener('touchmove', handleTouch, {{ passive: false }}); canvas.addEventListener('touchend', e => {{ e.preventDefault(); keys.left = false; keys.right = false; }});
    function init() {{ platforms = []; brokenParts = []; score = 0; doodler.x = GAME_W / 2 - 30; doodler.y = GAME_H - 150; doodler.vy = 0; doodler.dir = 1; let startY = GAME_H - 50; platforms.push(createPlatform(GAME_W/2 - 30, startY, 'standard')); let currentY = startY; while (currentY > 0) {{ currentY -= 50; generatePlatform(currentY, true); }} }}
    function createPlatform(x, y, type) {{ return {{ x, y, w: 60, h: 15, type: type, hasSpring: (type==='standard' && Math.random()<0.05), springAnim: 0 }}; }}
    function generatePlatform(y, forceSafe=false) {{ let type = 'standard'; if (platforms.length > 0 && platforms[platforms.length-1].type==='breakable') forceSafe=true; if (!forceSafe && Math.random()<0.15) type='breakable'; platforms.push(createPlatform(Math.random()*(GAME_W-60), y, type)); }}
    function update() {{
        if (isGameOverAnimating) {{ doodler.vy += 0.0575; if (doodler.vy > 4.6) doodler.vy = 4.6; doodler.y += doodler.vy; doodler.x += Math.sin(doodler.y * 0.02) * 1.5; if (doodler.y > GAME_H + 200) gameRunning = false; return; }}
        if (keys.left) {{ doodler.x -= MOVE_SPEED; doodler.dir = -1; }} if (keys.right) {{ doodler.x += MOVE_SPEED; doodler.dir = 1; }}
        if (doodler.x < -doodler.w/2) doodler.x = GAME_W - doodler.w/2; else if (doodler.x > GAME_W - doodler.w/2) doodler.x = -doodler.w/2;
        doodler.vy += GRAVITY; doodler.y += doodler.vy;
        let centerX = doodler.x + doodler.w/2; let feetY = doodler.y + doodler.h;
        if (doodler.vy > 0) {{ platforms.forEach((p, index) => {{ if(p.broken) return; if (feetY >= p.y && feetY <= p.y + p.h + 10 && centerX >= p.x && centerX <= p.x + p.w) {{ if (p.type === 'breakable') {{ createBrokenPlatform(p); platforms.splice(index, 1); }} else {{ if (p.hasSpring) {{ doodler.vy = -20; p.springAnim = 10; }} else {{ doodler.vy = JUMP_FORCE; }} }} }} }}); }}
        if (doodler.y < GAME_H * 0.45) {{ let diff = (GAME_H * 0.45) - doodler.y; doodler.y = GAME_H * 0.45; score += Math.floor(diff); platforms.forEach(p => p.y += diff); brokenParts.forEach(bp => bp.y += diff); platforms = platforms.filter(p => p.y < GAME_H); brokenParts = brokenParts.filter(bp => bp.y < GAME_H); let topPlat = platforms[platforms.length - 1]; if (topPlat && topPlat.y > 60) generatePlatform(topPlat.y - (30 + Math.random() * 30), false); }}
        brokenParts.forEach(bp => {{ bp.vy += GRAVITY; bp.y += bp.vy; bp.rot += 0.15; }}); if (doodler.y > GAME_H) triggerGameOverSequence();
    }}
    function createBrokenPlatform(p) {{ brokenParts.push({{ x: p.x, y: p.y, w: p.w/2, h: p.h, vy: -2, rot: 0, type: 'left' }}); brokenParts.push({{ x: p.x + p.w/2, y: p.y, w: p.w/2, h: p.h, vy: -1, rot: 0, type: 'right' }}); }}
    function triggerGameOverSequence() {{ if (isGameOverAnimating) return; isGameOverAnimating = true; if(score > highScore) {{ highScore = score; localStorage.setItem('doodleHighScore', highScore); }} document.getElementById('final-score').innerText = score; document.getElementById('high-score').innerText = highScore; canvas.style.pointerEvents = 'none'; platforms = []; brokenParts = []; doodler.y = -70; doodler.vy = 0; const goScreen = document.getElementById('game-over-screen'); goScreen.classList.remove('hidden'); void goScreen.offsetWidth; goScreen.classList.add('slide-up'); document.getElementById('score-display').classList.add('fade-out'); }}
    function drawScribbleFill(x, y, w, h, color) {{ ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.beginPath(); for (let i = y + 4; i < y + h - 2; i += 3) {{ ctx.moveTo(x + 5, i); ctx.bezierCurveTo(x + w/3, i - 2, x + 2*w/3, i + 2, x + w - 5, i); }} ctx.stroke(); }}
    function drawFlattenedRoughOval(x, y, w, h, outlineColor, fillColor) {{ drawScribbleFill(x, y, w, h, fillColor); ctx.strokeStyle = outlineColor; ctx.lineWidth = 2; for(let i=0; i<2; i++) {{ let offset = i === 0 ? 0 : 1.5; ctx.beginPath(); ctx.moveTo(x + 5, y + offset); ctx.quadraticCurveTo(x + w/2, y - 2 + offset, x + w - 5, y + offset); ctx.quadraticCurveTo(x + w + 2, y + h/2 + offset, x + w - 5, y + h + offset); ctx.quadraticCurveTo(x + w/2, y + h + 2 + offset, x + 5, y + h + offset); ctx.quadraticCurveTo(x - 2, y + h/2 + offset, x + 5, y + offset); ctx.stroke(); }} }}
    function draw() {{ ctx.clearRect(0, 0, GAME_W, GAME_H); ctx.lineCap = 'round'; ctx.lineJoin = 'round'; platforms.forEach(p => {{ const greenOutline = '#3e611f'; const greenFill = '#67c22e'; const brownOutline = '#5c3a1f'; const brownFill = '#a5681c'; if (p.type === 'standard') {{ drawFlattenedRoughOval(p.x, p.y, p.w, p.h, greenOutline, greenFill); if (p.hasSpring) {{ drawSpring(p.x + p.w - 25, p.y - 10, p.springAnim > 0); if(p.springAnim > 0) p.springAnim--; }} }} else if (p.type === 'breakable') {{ drawFlattenedRoughOval(p.x, p.y, p.w, p.h, brownOutline, brownFill); ctx.strokeStyle = brownOutline; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(p.x + p.w/2, p.y); ctx.lineTo(p.x + p.w/2, p.y + p.h); ctx.stroke(); }} }}); brokenParts.forEach(bp => {{ ctx.save(); ctx.translate(bp.x + bp.w/2, bp.y + bp.h/2); ctx.rotate(bp.type === 'left' ? -bp.rot : bp.rot); drawFlattenedRoughOval(-bp.w/2, -bp.h/2, bp.w, bp.h, '#5c3a1f', '#a5681c'); ctx.restore(); }}); drawDoodler(); if(!isGameOverAnimating) document.getElementById('score-display').innerText = score; }}
    function drawSpring(x, y, compressed) {{ ctx.fillStyle = '#ccc'; ctx.strokeStyle = '#000'; ctx.lineWidth = 1; let h = compressed ? 5 : 10; let yOff = compressed ? 5 : 0; ctx.beginPath(); ctx.rect(x, y + yOff, 14, h); ctx.fill(); ctx.stroke(); ctx.beginPath(); ctx.moveTo(x, y+yOff+3); ctx.lineTo(x+14, y+yOff+3); ctx.stroke(); }}
    function drawDoodler() {{ ctx.save(); let cx = doodler.x + doodler.w/2; let cy = doodler.y + doodler.h/2; ctx.translate(cx, cy); if (doodler.dir === -1) ctx.scale(-1, 1); const bodyColor = '#d0e148'; const stripeColor = '#5e8c31'; const outlineColor = '#000'; ctx.lineWidth = 3; ctx.fillStyle = bodyColor; ctx.strokeStyle = outlineColor; ctx.beginPath(); ctx.moveTo(-10, 15); ctx.lineTo(-10, 22); ctx.moveTo(0, 15); ctx.lineTo(0, 22); ctx.moveTo(10, 15); ctx.lineTo(10, 22); ctx.stroke(); ctx.beginPath(); ctx.moveTo(-18, 15); ctx.bezierCurveTo(-18, -15, -10, -25, 5, -20); ctx.bezierCurveTo(15, -20, 18, -10, 18, 15); ctx.lineTo(-18, 15); ctx.fill(); ctx.save(); ctx.clip(); ctx.fillStyle = stripeColor; ctx.fillRect(-20, 10, 40, 3); ctx.fillRect(-20, 5, 40, 3); ctx.fillRect(-20, 0, 40, 3); ctx.restore(); ctx.stroke(); ctx.fillStyle = bodyColor; ctx.beginPath(); ctx.moveTo(15, -12); ctx.lineTo(28, -15); ctx.bezierCurveTo(32, -14, 32, -6, 28, -5); ctx.lineTo(15, -5); ctx.fill(); ctx.stroke(); ctx.fillStyle = outlineColor; ctx.beginPath(); ctx.ellipse(28, -10, 2, 4, 0, 0, Math.PI*2); ctx.fill(); ctx.fillStyle = outlineColor; ctx.beginPath(); ctx.arc(0, -12, 2, 0, Math.PI*2); ctx.arc(8, -12, 2, 0, Math.PI*2); ctx.fill(); ctx.restore(); }}
    function startGame() {{ document.getElementById('start-screen').classList.add('hidden'); const goScreen = document.getElementById('game-over-screen'); goScreen.classList.remove('slide-up'); document.getElementById('score-display').classList.remove('fade-out'); canvas.style.pointerEvents = 'auto'; isGameOverAnimating = false; init(); if (!gameRunning) {{ gameRunning = true; lastTime = performance.now(); requestAnimationFrame(loop); }} }}
    function loop(currentTime) {{ if (!gameRunning) return; requestAnimationFrame(loop); const elapsed = currentTime - lastTime; if (elapsed > frameInterval) {{ lastTime = currentTime - (elapsed % frameInterval); update(); draw(); }} }}
</script>
</body>
</html>
"""

# --------------------------------------------------
# 7. MAIN APPLICATION
# --------------------------------------------------

# Ensure score processing happens FIRST
if 'mis_no' not in st.session_state:
    st.session_state.mis_no = ""
if 'attendance' not in st.session_state:
    st.session_state.attendance = load_attendance()

sub_dfs, sched_df, link_map = load_data()

# Load all venues once
all_venues_set = get_all_venues(sched_df)

# HEADER with Theme Toggle
h1_col, toggle_col = st.columns([8, 1])
with h1_col:
    header_html = """
    <h1 style='text-align: left; background: linear-gradient(to right, #6a11cb, #2575fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 3em; font-weight: 800; padding-top:10px;'>
    ✨ Smart Semester Timetable
    </h1>
    """
    st.markdown(header_html, unsafe_allow_html=True)

with toggle_col:
    st.write("") 
    st.write("") 
    icon = "🌙" if st.session_state.theme == "light" else "☀️"
    if st.button(icon, on_click=toggle_theme, key="theme_toggle", help="Toggle Dark Mode"): pass

# --- BRIDGE LOGIC (PERSISTENT MODAL STATE) ---
if st.session_state.venue_bridge and st.session_state.venue_bridge != st.session_state.last_processed_bridge:
    try:
        st.session_state.last_processed_bridge = st.session_state.venue_bridge
        parts = st.session_state.venue_bridge.split('|')
        clicked_day = parts[0]
        clicked_time = parts[1]
        
        # Calculate and STORE venues in session state
        free_venues_list = get_free_venues_at_slot(clicked_day, clicked_time, sched_df, all_venues_set)
        
        st.session_state.active_slot_data = {
            "day": clicked_day,
            "time": clicked_time,
            "venues": free_venues_list
        }
    except: pass

# --- RENDER MODAL IF STATE EXISTS ---
if st.session_state.active_slot_data:
    data = st.session_state.active_slot_data
    start_dt = datetime.strptime(data['time'], "%H:%M")
    end_dt = start_dt + timedelta(hours=1)
    time_range = f"{data['time']} - {end_dt.strftime('%H:%M')}"

    @st.dialog("Available Classrooms")
    def show_venue_modal():
        st.markdown(f"""
        <div style='margin-bottom: 20px;'>
            <p style='font-size: 16px; opacity: 0.8;'>
                Free slots on <span style="color:#6a11cb; font-weight:700">{data['day']}</span> from <span style="background:#f0f2f6; padding:2px 6px; border-radius:4px; font-weight:600; color:#333">{time_range}</span>
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        if data['venues']:
            cards_html = '<div class="venue-card-row">'
            for v in data['venues']:
                v_type = "LECTURE HALL" if "L" in v or "A" in v else "LAB" if "LAB" in v.upper() else "TUTORIAL ROOM"
                capacity = "60" if v_type == "LECTURE HALL" else "30"
                amenity = "📽️ Projector" if v_type == "LECTURE HALL" else "💻 Computers" if v_type == "LAB" else "📝 Whiteboard"
                
                cards_html += f"""
                <div class="venue-card">
                   <div class="venue-left">
                       <div class="venue-icon-box">📍</div>
                       <div class="venue-details">
                          <div class="venue-name">{v}</div>
                          <div class="venue-type">{v_type}</div>
                          <div class="venue-extras">{amenity}</div>
                       </div>
                   </div>
                   <div class="venue-capacity-badge">👥 {capacity}</div>
                </div>
                """
            cards_html += '</div>'
            st.markdown(cards_html, unsafe_allow_html=True)
        else:
            st.warning("No free classrooms found for this slot.")
            
        if st.button("Close", key="close_venue_modal", type="primary", use_container_width=True):
            st.session_state.active_slot_data = None
            st.rerun()

    show_venue_modal()


if not sub_dfs or sched_df is None:
    st.error(f"Missing files in '{DATA_FOLDER}'.")
else:
    # INPUT SECTION
    if not st.session_state.mis_no:
        mis_input = st.text_input("Enter MIS No:", placeholder="e.g. 612572034")
        if mis_input:
            st.session_state.mis_no = mis_input
            st.rerun()
    else:
        mis = st.session_state.mis_no
        c1, c2 = st.columns([9, 1])
        with c2: 
            if st.button("Change User", type="secondary"):
                st.session_state.mis_no = ""
                st.rerun()

        subs, table, name, branch = get_schedule(mis, sub_dfs, sched_df)

        if subs:
            # --- PROFILE ---
            st.markdown(f"""<div class="student-card"><div class="student-name">{name}</div><div class="student-meta">{branch} • MIS: {mis}</div></div>""", unsafe_allow_html=True)

            # --- 1. WEEKLY SCHEDULE ---
            st.markdown("""<h3 style="font-size: 28px; font-weight: 700; margin: 20px 0; background: linear-gradient(to right, #6a11cb, #fbc2eb); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">🗓️ Weekly Schedule</h3>""", unsafe_allow_html=True)
            
            if table:
                st.sidebar.markdown("---")
                st.sidebar.markdown(f"""
                <h3 style='background: linear-gradient(45deg, #a18cd1, #fbc2eb); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700; margin-bottom: 5px;'>📲 Calendar Sync</h3>
                <p style='font-size: 11px; margin-bottom: 10px; background: linear-gradient(90deg, #E0C3FC, #8EC5FC); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 600;'>One click to add your entire semester schedule to your phone.</p>
                """, unsafe_allow_html=True)
                
                master_ics_data = generate_master_ics(table, SEMESTER_END)
                st.sidebar.download_button(label="📥 Sync Full Semester", data=master_ics_data, file_name=f"My_Semester_Timetable_{mis}.ics", mime="text/calendar")
                
                if st.sidebar.button("Refresh Data / Clear Cache"):
                    st.cache_data.clear()
                    st.rerun()
                
                # Render the grid with JS hooks
                st.markdown(render_grid(table), unsafe_allow_html=True)
            else:
                st.warning("No schedule found.")

            # --- ALLOCATED SUBJECTS ---
            with st.expander("Subject Allocation List", expanded=False):
                st.markdown(render_subject_html(subs, link_map), unsafe_allow_html=True)
            
            # --- 2. ATTENDANCE TRACKER ---
            st.markdown("""<hr style="border:1px solid rgba(128,128,128,0.2); margin: 40px 0;">""", unsafe_allow_html=True)
            st.markdown("""<h3 style="font-size: 28px; font-weight: 700; margin-bottom: 20px; background: linear-gradient(to right, #6a11cb, #fbc2eb); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">✅ Attendance Tracker</h3>""", unsafe_allow_html=True)

            col_date, col_daily_list = st.columns([1, 3])
            with col_date:
                st.markdown("##### Select Date")
                selected_date = st.date_input("Pick a day", value=date.today(), min_value=SEMESTER_START, max_value=SEMESTER_END)
                day_name = selected_date.strftime("%A")
                st.caption(f"Schedule for **{day_name}**")

            with col_daily_list:
                st.markdown(f"##### Schedule for {selected_date.strftime('%d %B, %Y')}")
                daily_classes = [t for t in table if t['Day'] == day_name]
                
                if not daily_classes:
                    st.info("😴 No classes scheduled for this day.")
                else:
                    daily_classes.sort(key=lambda x: datetime.strptime(x['StartTime'], "%H:%M"))
                    for i, cls in enumerate(daily_classes):
                        cls_id = f"{mis}_{selected_date}_{cls['Subject']}_{cls['Type']}_{cls['StartTime']}"
                        is_present = st.session_state.attendance.get(cls_id, False)
                        border_color = "#6a11cb" if is_present else "rgba(128,128,128,0.2)"
                        c_info, c_action = st.columns([4, 1])
                        with c_info:
                            st.markdown(f"""<div class="daily-card" style="border-left: 5px solid {border_color};"><div class="daily-info"><h4>{cls['Subject']}</h4><p>⏰ {cls['StartTime']} • {cls['Type']} • 📍 {cls['Venue']}</p></div></div>""", unsafe_allow_html=True)
                        with c_action:
                            btn_label = "Mark ✓" if not is_present else "Undo ✕"
                            btn_type = "primary" if not is_present else "secondary"
                            if st.button(btn_label, key=cls_id, type=btn_type, use_container_width=True):
                                if is_present:
                                    del st.session_state.attendance[cls_id]
                                    update_attendance_in_sheet(cls_id, "remove")
                                else:
                                    st.session_state.attendance[cls_id] = True
                                    update_attendance_in_sheet(cls_id, "add")
                                st.rerun()

            # --- 3. CALCULATOR ---
            st.markdown("""<hr style="border:1px solid rgba(128,128,128,0.2); margin: 40px 0;">""", unsafe_allow_html=True)
            st.markdown("""<h3 style="font-size: 28px; font-weight: 700; margin-bottom: 20px; background: linear-gradient(to right, #6a11cb, #fbc2eb); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">📊 Attendance Calculator</h3>""", unsafe_allow_html=True)
            
            total_possible = calculate_semester_totals(table)
            row_cols = st.columns(3)
            col_idx = 0
            
            for sub_key, total_count in total_possible.items():
                subject_name, subject_type = sub_key.split('|')
                attended = 0
                for att_id in st.session_state.attendance:
                    parts = att_id.split('_')
                    if len(parts) >= 5 and parts[0] == mis and parts[2] == subject_name and parts[3] == subject_type:
                        attended += 1
                
                percentage = (attended / total_count * 100) if total_count > 0 else 0
                req_for_75 = (0.75 * total_count)
                needed = req_for_75 - attended
                border_grad = "linear-gradient(135deg, #6a11cb, #2575fc)"
                is_dark = st.session_state.theme == 'dark'
                bg_color = "rgba(106, 17, 203, 0.05)" if is_dark else "#f0f0f0"
                msg_color = "#2ecc71"

                if percentage < 60:
                    border_grad = "linear-gradient(135deg, #ff9a9e, #fecfef)" 
                    bg_color = "rgba(255, 0, 0, 0.05)" if is_dark else "#fff5f5"
                    msg_color = "#e74c3c"
                elif percentage < 75:
                    border_grad = "linear-gradient(135deg, #f6d365, #fda085)"
                    bg_color = "rgba(255, 165, 0, 0.05)" if is_dark else "#fffdf5"
                    msg_color = "#e67e22"

                with row_cols[col_idx % 3]:
                    st.markdown(f"""<div class="metric-card" style="border-top: 5px solid transparent; border-image: {border_grad} 1; background-color: {bg_color};"><div class="metric-title">{subject_name} <br> <span style="font-size:10px; opacity:0.7">({subject_type})</span></div><div class="metric-value">{percentage:.1f}%</div><div class="metric-sub">{attended} / {total_count} Sessions</div></div>""", unsafe_allow_html=True)
                    if needed > 0: st.markdown(f"<div style='text-align:center; margin-top:10px; color:{msg_color}; font-weight:600; font-size:14px;'>Attend {int(needed) + 1} more</div>", unsafe_allow_html=True)
                    else: st.markdown(f"<div style='text-align:center; margin-top:10px; color:{msg_color}; font-weight:600; font-size:14px;'>Safe!</div>", unsafe_allow_html=True)
                    st.write("") 
                col_idx += 1

            # --- 4. GAME SECTION ---
            st.markdown("""<hr style="border:1px solid rgba(128,128,128,0.2); margin: 40px 0;">""", unsafe_allow_html=True)
            st.markdown("""<h3 style="font-size: 28px; font-weight: 700; margin-bottom: 20px; background: linear-gradient(to right, #6a11cb, #fbc2eb); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">🎮 Stress Buster Game</h3>""", unsafe_allow_html=True)

            c_game_main, c_game_info = st.columns([3, 1])
            with c_game_main:
                game_html = render_game_html()
                components.html(game_html, height=650, scrolling=False)
            
            with c_game_info:
                st.info(f"**Playing as:**\n\n{name}\n\n({branch})")
                st.caption("Just relax and jump! No high scores are saved to the server.")

        else:
            st.error("MIS not found.")
            if st.button("Try Again"):
                st.session_state.mis_no = ""
                st.rerun()

# FOOTER
footer_color = "var(--footer-color)"
st.markdown(f"""
<div style="text-align: center; margin-top: 50px; font-size: 13px; color: {footer_color};">
    Student Portal © 2026 • Built by <span style="color:#6a11cb; font-weight:700">IRONDEM2921 [AIML]</span>
</div>
""", unsafe_allow_html=True)

# --- BRIDGE INPUT (Rendered Last to Avoid Crash) ---
# This input receives the JS data but is kept invisible via CSS
st.text_input("venue_bridge_input", key="venue_bridge", label_visibility="collapsed")

# --- JS INJECTION ---
components.html("""
<script>
    // Access the PARENT document where the Streamlit app lives
    var parentDoc = window.parent.document;

    function attachListeners() {
        // Find the empty slots in the PARENT document
        const emptySlots = parentDoc.querySelectorAll('.js-free-slot-trigger');
        
        emptySlots.forEach(slot => {
            // Prevent duplicate listeners
            if (slot.dataset.listenerAttached === 'true') return;
            slot.dataset.listenerAttached = 'true';

            // --- DESKTOP DOUBLE-CLICK ---
            slot.addEventListener('dblclick', function() {
                triggerStreamlitUpdate(this.dataset.day, this.dataset.time);
            });

            // --- MOBILE LONG-PRESS ---
            let pressTimer;
            slot.addEventListener('touchstart', function(e) {
                // Prevent interfering with multi-touch gestures
                if (e.touches.length === 1) { 
                    pressTimer = setTimeout(() => { 
                        triggerStreamlitUpdate(this.dataset.day, this.dataset.time); 
                    }, 800); 
                }
            });
            slot.addEventListener('touchend', function() { clearTimeout(pressTimer); });
            slot.addEventListener('touchmove', function() { clearTimeout(pressTimer); });
        });
    }

    function triggerStreamlitUpdate(day, time) {
        // Find the specific hidden input in the PARENT document
        const bridgeInput = parentDoc.querySelector('input[aria-label="venue_bridge_input"]');
        
        if (bridgeInput) {
            // Use random number to force state change every click
            const newValue = `${day}|${time}|${Math.random()}`;
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
            nativeInputValueSetter.call(bridgeInput, newValue);
            bridgeInput.dispatchEvent(new Event('input', { bubbles: true }));
            bridgeInput.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }

    // Continuously check for new grid elements (since Streamlit re-renders frequently)
    setInterval(attachListeners, 1000);
</script>
""", height=0, width=0)
