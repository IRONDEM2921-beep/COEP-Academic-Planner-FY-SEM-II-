import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import re
import zlib
import json
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

# Define Color Palettes
light_theme = {
    "bg_color": "#f1f0f6",
    "text_color": "#2c3e50",
    "card_bg": "#ffffff",
    "card_shadow": "rgba(0,0,0,0.05)",
    "table_row_hover": "#f8f9fa",
    "secondary_btn_bg": "#ffffff",
    "secondary_btn_text": "#6a11cb",
    "game_bg": "#fcfcf4",
    "game_grid": "#e0dacc"
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
    "game_grid": "#333333"
}

# Select current palette
current_theme = light_theme if st.session_state.theme == 'light' else dark_theme

# Generate CSS
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
div.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%) !important;
    border: none !important; border-radius: 50px !important; font-weight: 600;
    box-shadow: 0 4px 10px rgba(106, 17, 203, 0.2); transition: transform 0.2s;
}}
div.stButton > button[kind="primary"] * {{ color: #ffffff !important; }}
div.stButton > button[kind="primary"]:hover {{ transform: translateY(-2px); box-shadow: 0 6px 15px rgba(106, 17, 203, 0.3); }}

div.stButton > button[kind="secondary"] {{
    background-color: var(--sec-btn-bg) !important; color: var(--sec-btn-text) !important; 
    border: 2px solid #6a11cb !important; border-radius: 50px !important; font-weight: 600;
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
.type-empty {{ background: var(--card-bg); border: 2px dashed rgba(160, 160, 200, 0.2); border-radius: 18px; }}
.sub-title {{ font-weight: 700; font-size: 13px; margin-bottom: 4px; }}
.sub-meta {{ font-size: 11px; opacity: 0.9; }}
.batch-badge {{
    background: rgba(255,255,255,0.6); padding: 3px 8px; border-radius: 10px;
    font-size: 10px; font-weight: 700; text-transform: uppercase; display: inline-block;
    margin-bottom: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); color: #2c3e50 !important;
}}

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

/* --- DROPDOWN (SELECTBOX) FIXED & RESPONSIVE --- */

/* 1. The Container - Use Theme Variables */
div[data-baseweb="select"] > div {{
    background-color: var(--card-bg) !important;
    border: 1px solid rgba(128, 128, 128, 0.2);
    color: var(--text-color) !important;
    border-radius: 12px !important;
}}

/* 2. The Text inside the box (Selected Value) */
div[data-baseweb="select"] div {{
    color: var(--text-color) !important;
    font-weight: 600;
}}

/* 3. The SVG Arrow Icon - Ensure it is visible */
div[data-baseweb="select"] svg {{
    fill: var(--text-color) !important;
}}

/* 4. The Dropdown Menu List (Popover) */
ul[data-baseweb="menu"] {{
    background-color: var(--card-bg) !important;
    border: 1px solid rgba(128, 128, 128, 0.2) !important;
    box-shadow: 0 4px 20px var(--card-shadow) !important;
    padding: 5px !important;
    border-radius: 12px !important;
    /* Fix for mobile/laptop z-index layering */
    z-index: 9999 !important; 
}}

/* 5. List Items (Options) */
li[role="option"] {{
    background-color: transparent !important;
    color: var(--text-color) !important;
    border-bottom: 1px solid rgba(128,128,128,0.1);
    margin-bottom: 2px;
    border-radius: 8px;
}}

/* 6. Text inside List Items */
li[role="option"] div {{
    color: var(--text-color) !important;
    font-weight: 500 !important;
}}

/* 7. Hover & Selection State */
li[role="option"]:hover, li[role="option"][aria-selected="true"] {{
    background-color: var(--table-row-hover) !important;
    cursor: pointer;
}}

li[role="option"]:hover div, li[role="option"][aria-selected="true"] div {{
    color: #6a11cb !important;
    font-weight: 700 !important;
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
    if pd.isna(time_str): return None, 1
    raw = str(time_str).upper().replace('.', ':').replace('-', ' ').replace('TO', ' ')
    times = re.findall(r'(\d{1,2}:\d{2})', raw)
    if not times: return None, 1
    start_str = times[0].lstrip("0")
    duration = 1
    if len(times) >= 2:
        try:
            t1 = datetime.strptime(start_str, "%H:%M")
            t2 = datetime.strptime(times[1], "%H:%M")
            diff = (t2 - t1).total_seconds() / 60
            if diff > 80: duration = 2
        except: pass
    return start_str, duration

def map_to_slot(time_str, slots):
    try:
        t = datetime.strptime(time_str, "%H:%M")
        best, min_diff = None, 999
        for s in slots:
            diff = abs((t - datetime.strptime(s, "%H:%M")).total_seconds() / 60)
            if diff < min_diff: min_diff, best = diff, s
        if min_diff <= 45: return best
    except: pass
    return None

# --- GOOGLE SHEETS PERSISTENCE ---
def get_google_client():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds)

def get_google_sheet(index=0):
    client = get_google_client()
    sheet_url = st.secrets["private_sheet_url"] 
    try:
        sh = client.open_by_url(sheet_url)
        # Check if index exists, if not create
        if index >= len(sh.worksheets()):
            return sh.add_worksheet(title="Leaderboard", rows="1000", cols="4")
        return sh.get_worksheet(index)
    except Exception as e:
        return None

def load_attendance():
    try:
        sheet = get_google_sheet(0) # Sheet 1
        data = sheet.col_values(1)
        return {cls_id: True for cls_id in data if cls_id}
    except Exception as e:
        return {}

def update_attendance_in_sheet(cls_id, action):
    try:
        sheet = get_google_sheet(0) # Sheet 1
        if action == "add":
            sheet.append_row([cls_id])
        elif action == "remove":
            cell = sheet.find(cls_id)
            if cell:
                sheet.delete_rows(cell.row)
    except Exception as e:
        pass

# --- LEADERBOARD FUNCTIONS ---
def get_leaderboard_data():
    """Fetches entire leaderboard for edge case analysis"""
    try:
        sheet = get_google_sheet(1)
        data = sheet.get_all_records()
        if not data: return pd.DataFrame()
        df = pd.DataFrame(data)
        # Type enforcement
        if 'Score' in df.columns:
            df['Score'] = pd.to_numeric(df['Score'], errors='coerce').fillna(0).astype(int)
        return df
    except:
        return pd.DataFrame()

def get_overall_highest(df):
    if df.empty or 'Score' not in df.columns: return 0, "No Data", "General"
    max_idx = df['Score'].idxmax()
    row = df.loc[max_idx]
    return row['Score'], row['Name'], row['Branch']

def get_branch_highest(df, branch):
    if df.empty or 'Branch' not in df.columns: return 0, "No Data"
    filtered = df[df['Branch'] == branch]
    if filtered.empty: return 0, "No Data"
    max_idx = filtered['Score'].idxmax()
    row = filtered.loc[max_idx]
    return row['Score'], row['Name']

def update_leaderboard_score(name, branch, score):
    try:
        sheet = get_google_sheet(1)
        # Check if headers exist
        if not sheet.row_values(1):
            sheet.append_row(["Branch", "Name", "Score", "Date"])
            
        # Optimization: We append new high score. 
        # The logic fetches all and finds MAX, so we don't need to search/update rows.
        # This acts as a log of high scores.
        sheet.append_row([branch, name, score, str(date.today())])
        return True, "Success"
    except Exception as e:
        return False, str(e)

# --- MASTER ICS GENERATION ---
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

# --------------------------------------------------
# 5. DATA LOADING & LOGIC
# --------------------------------------------------
@st.cache_data
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
            if f.lower() == TIMETABLE_FILE.lower():
                sched_df = df
            elif "link" in f.lower():
                for _, row in df.iterrows():
                    if len(row) >= 2:
                        link_map[clean_text(correct_subject_name(row.iloc[0]))] = str(row.iloc[1]).strip()
            else:
                sub_dfs.append(df)
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
                is_lab = "lab" in (str(row[t_type_col]).lower() if t_type_col else "")
                if (not is_lab) or (t_batch == "all" or t_batch == s_batch):
                    start, dur = parse_time(row[t_time_col])
                    if start:
                        timetable.append({
                            "Day": str(row[t_day_col]).title().strip(), "StartTime": start, "Duration": dur,
                            "Subject": sub['Subject'], "Type": "LAB" if is_lab else "THEORY", "Venue": str(row[t_venue_col]) if t_venue_col else "-"
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
                html += f'<td {span}><div class="class-card filled" style="background:{grad}"><div class="batch-badge">{cell["Type"]}</div><div class="sub-title">{cell["Subject"]}</div><div class="sub-meta">📍 {cell["Venue"]}</div></div></td>'
            else:
                html += '<td><div class="class-card type-empty"></div></td>'
        html += '</tr>'
    return html + '</tbody></table></div>'

def render_subject_html(subjects, link_map):
    html_parts = ["""
    <style>
    .sub-alloc-wrapper { font-family: 'Poppins', sans-serif; margin-top: 10px; border-radius: 12px; overflow-x: auto; border: none; box-shadow: 0 4px 20px var(--card-shadow); background: var(--card-bg); }
    table.sub-alloc-table { width: 100%; min-width: 600px; border-collapse: collapse; background: var(--card-bg); }
    .sub-alloc-table thead th { background: linear-gradient(90deg, #a18cd1 0%, #fbc2eb 100%); color: white; padding: 18px; font-size: 17px; font-weight: 700; text-align: left; white-space: nowrap; }
    .sub-alloc-table tbody td { padding: 16px; font-size: 16px; color: var(--text-color); border-bottom: 1px solid rgba(128,128,128,0.1); background: var(--card-bg); vertical-align: middle; transition: all 0.2s; white-space: nowrap; }
    .sub-alloc-table tbody tr:hover td { background-color: var(--table-row-hover); transform: scale(1.005); color: #6a11cb; cursor: default; }
    .drive-btn { background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%); color: white !important; padding: 8px 16px; border-radius: 50px; text-decoration: none; font-size: 13px; font-weight: 600; display: inline-block; transition: 0.2s; }
    .drive-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 15px rgba(37, 117, 252, 0.3); }
    </style>
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

# --------------------------------------------------
# 6. GAME INTEGRATION (AUTOMATIC SCORE)
# --------------------------------------------------

def render_game_html(mis_user):
    # Detect theme colors for game CSS
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
        
        body {{ 
            margin: 0; padding: 0; 
            display: flex; justify-content: center; align-items: center; 
            height: 100vh;
            background-color: transparent; 
            font-family: 'Patrick Hand', cursive; 
            overflow: hidden;
        }}

        #game-container {{
            position: relative; 
            width: 100%; max-width: 400px;
            aspect-ratio: 2/3; max-height: 90vh;
            background-color: {game_bg};
            background-image: linear-gradient({grid_line} 1px, transparent 1px), linear-gradient(90deg, {grid_line} 1px, transparent 1px);
            background-size: 15px 15px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15); 
            border-radius: 12px;
            overflow: hidden;
            touch-action: none; 
        }}

        canvas {{ 
            display: block; 
            width: 100%; height: 100%; 
            position: absolute; top: 0; left: 0; 
            
            /* FIX 1: Canvas is now ABOVE the UI layer */
            z-index: 20; 
            
            /* FIX 2: Initially let clicks pass through to the 'Play' button */
            pointer-events: none; 
            
            touch-action: none;
        }}

        #ui-layer {{ 
            position: absolute; top: 0; left: 0; width: 100%; height: 100%; 
            
            /* FIX 1: UI is now BELOW the canvas */
            z-index: 10; 
            
            pointer-events: none; 
        }}

        /* Make sure interactive elements inside UI are clickable */
        .menu-screen {{ pointer-events: auto; }}
        
        #score-display {{ position: absolute; top: 10px; left: 20px; font-size: 32px; color: #888; font-weight: bold; transition: opacity 0.3s; }}
        
        .menu-screen {{ 
            position: absolute; width: 100%; height: 100%; 
            background: rgba(255,255,255, 0.95); 
            display: flex; flex-direction: column; justify-content: center; align-items: center; 
            text-align: center; 
        }}
        
        #start-screen {{ top: 0; left: 0; transition: opacity 0.3s; }}
        #game-over-screen {{ left: 0; top: 100%; transition: top 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275); }}
        #game-over-screen.slide-up {{ top: 0% !important; }}
        
        .hidden {{ display: none !important; opacity: 0; }}
        .fade-out {{ opacity: 0; }}
        
        h1 {{ font-size: 42px; color: #d32f2f; margin: 0 0 10px 0; transform: rotate(-3deg); }}
        p {{ font-size: 20px; color: #444; margin: 5px 0; }}
        
        .btn {{ 
            background: #fff; border: 2px solid #333; border-radius: 8px; 
            padding: 12px 35px; font-family: 'Patrick Hand', cursive; font-size: 24px; 
            color: #333; cursor: pointer; margin-top: 25px; 
            box-shadow: 4px 4px 0px rgba(0,0,0,0.1); 
            -webkit-tap-highlight-color: transparent;
        }}
        .btn:active {{ transform: scale(0.96); box-shadow: 2px 2px 0px rgba(0,0,0,0.1); background: #f4f4f4; }}

        .auto-save-msg {{ font-size:16px; color:#6a11cb; margin-top:15px; font-weight:bold; }}
        #save-link {{ display:none; color: #6a11cb; font-size: 18px; margin-top: 15px; font-weight: bold; text-decoration: underline; cursor: pointer; }}
    </style>
</head>
<body>
<div id="game-container">
    <canvas id="gameCanvas" width="400" height="600"></canvas>
    <div id="ui-layer">
        <div id="score-display">0</div>
        
        <div id="start-screen" class="menu-screen">
            <h1>Doodle Jump</h1>
            <p>Tap <b>Left</b> or <b>Right</b> side</p>
            <button class="btn" onclick="startGame()">Play Now</button>
        </div>
        
        <div id="game-over-screen" class="menu-screen">
            <h1>Game Over!</h1>
            <p>Score: <span id="final-score">0</span></p>
            <p>Best: <span id="high-score">0</span></p>
            <div id="auto-msg" class="auto-save-msg">Saving score...</div>
            <a id="save-link" href="#" target="_top">CLICK TO SAVE SCORE</a>
            <button class="btn" onclick="startGame()" style="margin-top:25px;">Play Again</button>
        </div>
    </div>
</div>
<script>
    const canvas = document.getElementById('gameCanvas');
    const ctx = canvas.getContext('2d');
    
    const GRAVITY = 0.375; const JUMP_FORCE = -13.81; const MOVE_SPEED = 8.12;
    const GAME_W = 400; const GAME_H = 600;
    const USER_MIS = "{mis_user}";
    
    let platforms = [], brokenParts = [], score = 0;
    let highScore = localStorage.getItem('doodleHighScore') || 0;
    let gameRunning = false, isGameOverAnimating = false;
    const doodler = {{ x: GAME_W / 2 - 20, y: GAME_H - 150, w: 60, h: 60, vx: 0, vy: 0, dir: 1 }};
    const keys = {{ left: false, right: false }};
    
    // --- CONTROLS ---
    window.addEventListener('keydown', e => {{ if(e.key==="ArrowLeft") keys.left=true; if(e.key==="ArrowRight") keys.right=true; }});
    window.addEventListener('keyup', e => {{ if(e.key==="ArrowLeft") keys.left=false; if(e.key==="ArrowRight") keys.right=false; }});

    canvas.addEventListener('touchmove', function(e) {{ e.preventDefault(); }}, {{ passive: false }});
    canvas.addEventListener('touchstart', function(e) {{ e.preventDefault(); }}, {{ passive: false }});

    const handleTouch = (e) => {{
        if(e.touches.length === 0) return;
        const touch = e.touches[0];
        const rect = canvas.getBoundingClientRect();
        const touchX = touch.clientX - rect.left;
        const middle = rect.width / 2;
        if (touchX < middle) {{ keys.left = true; keys.right = false; }} 
        else {{ keys.left = false; keys.right = true; }}
    }};

    canvas.addEventListener('touchstart', handleTouch, {{ passive: false }});
    canvas.addEventListener('touchmove', handleTouch, {{ passive: false }});
    canvas.addEventListener('touchend', e => {{ e.preventDefault(); keys.left = false; keys.right = false; }});

    function init() {{
        platforms = []; brokenParts = []; score = 0;
        doodler.x = GAME_W / 2 - 30; doodler.y = GAME_H - 150; doodler.vy = 0; doodler.dir = 1;
        let startY = GAME_H - 50; platforms.push(createPlatform(GAME_W/2 - 30, startY, 'standard'));
        let currentY = startY;
        while (currentY > 0) {{ currentY -= 50; generatePlatform(currentY, true); }}
    }}
    function createPlatform(x, y, type) {{
        return {{ x, y, w: 60, h: 15, type: type, hasSpring: (type==='standard' && Math.random()<0.05), springAnim: 0 }};
    }}
    function generatePlatform(y, forceSafe=false) {{
        let type = 'standard';
        if (platforms.length > 0 && platforms[platforms.length-1].type==='breakable') forceSafe=true;
        if (!forceSafe && Math.random()<0.15) type='breakable';
        platforms.push(createPlatform(Math.random()*(GAME_W-60), y, type));
    }}
    function update() {{
        if (!gameRunning) return;
        if (isGameOverAnimating) {{
            doodler.vy += 0.0575; if (doodler.vy > 4.6) doodler.vy = 4.6;
            doodler.y += doodler.vy; doodler.x += Math.sin(doodler.y * 0.02) * 1.5;
            if (doodler.y > GAME_H + 200) gameRunning = false; return;
        }}
        if (keys.left) {{ doodler.x -= MOVE_SPEED; doodler.dir = -1; }}
        if (keys.right) {{ doodler.x += MOVE_SPEED; doodler.dir = 1; }}
        if (doodler.x < -doodler.w/2) doodler.x = GAME_W - doodler.w/2;
        else if (doodler.x > GAME_W - doodler.w/2) doodler.x = -doodler.w/2;
        doodler.vy += GRAVITY; doodler.y += doodler.vy;
        
        let centerX = doodler.x + doodler.w/2; let feetY = doodler.y + doodler.h;
        if (doodler.vy > 0) {{
            platforms.forEach((p, index) => {{
                if(p.broken) return;
                if (feetY >= p.y && feetY <= p.y + p.h + 10 && centerX >= p.x && centerX <= p.x + p.w) {{
                    if (p.type === 'breakable') {{ createBrokenPlatform(p); platforms.splice(index, 1); }}
                    else {{ if (p.hasSpring) {{ doodler.vy = -20; p.springAnim = 10; }} else {{ doodler.vy = JUMP_FORCE; }} }}
                }}
            }});
        }}
        if (doodler.y < GAME_H * 0.45) {{
            let diff = (GAME_H * 0.45) - doodler.y; doodler.y = GAME_H * 0.45;
            score += Math.floor(diff); platforms.forEach(p => p.y += diff); brokenParts.forEach(bp => bp.y += diff);
            platforms = platforms.filter(p => p.y < GAME_H); brokenParts = brokenParts.filter(bp => bp.y < GAME_H);
            let topPlat = platforms[platforms.length - 1];
            if (topPlat && topPlat.y > 60) generatePlatform(topPlat.y - (30 + Math.random() * 30), false);
        }}
        brokenParts.forEach(bp => {{ bp.vy += GRAVITY; bp.y += bp.vy; bp.rot += 0.15; }});
        if (doodler.y > GAME_H) triggerGameOverSequence();
    }}
    function createBrokenPlatform(p) {{
        brokenParts.push({{ x: p.x, y: p.y, w: p.w/2, h: p.h, vy: -2, rot: 0, type: 'left' }});
        brokenParts.push({{ x: p.x + p.w/2, y: p.y, w: p.w/2, h: p.h, vy: -1, rot: 0, type: 'right' }});
    }}
    
    function triggerGameOverSequence() {{
        if (isGameOverAnimating) return; isGameOverAnimating = true;
        if(score > highScore) {{ highScore = score; localStorage.setItem('doodleHighScore', highScore); }}
        
        document.getElementById('final-score').innerText = score;
        document.getElementById('high-score').innerText = highScore;
        
        // FIX 3: Disable pointer events on canvas so user can click 'Play Again' behind it
        canvas.style.pointerEvents = 'none';

        platforms = []; brokenParts = []; doodler.y = -70; doodler.vy = 0;
        const goScreen = document.getElementById('game-over-screen');
        goScreen.classList.remove('hidden'); void goScreen.offsetWidth; goScreen.classList.add('slide-up');
        document.getElementById('score-display').classList.add('fade-out');

        let baseUrl = "";
        try {{ baseUrl = document.referrer || window.parent.location.href; }} catch(e) {{ }}
        
        if (baseUrl) {{
            try {{
                const url = new URL(baseUrl);
                url.searchParams.set('score', score);
                url.searchParams.set('user', USER_MIS);
                const saveUrl = url.toString();
                const fallbackLink = document.getElementById('save-link');
                fallbackLink.href = saveUrl;
                fallbackLink.style.display = 'block';
                setTimeout(() => {{ window.top.location.href = saveUrl; }}, 1200);
            }} catch(e) {{ }}
        }}
    }}

    function drawScribbleFill(x, y, w, h, color) {{
        ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.beginPath();
        for (let i = y + 4; i < y + h - 2; i += 3) {{ ctx.moveTo(x + 5, i); ctx.bezierCurveTo(x + w/3, i - 2, x + 2*w/3, i + 2, x + w - 5, i); }}
        ctx.stroke();
    }}
    function drawFlattenedRoughOval(x, y, w, h, outlineColor, fillColor) {{
        drawScribbleFill(x, y, w, h, fillColor); ctx.strokeStyle = outlineColor; ctx.lineWidth = 2;
        for(let i=0; i<2; i++) {{
            let offset = i === 0 ? 0 : 1.5; ctx.beginPath();
            ctx.moveTo(x + 5, y + offset); ctx.quadraticCurveTo(x + w/2, y - 2 + offset, x + w - 5, y + offset);
            ctx.quadraticCurveTo(x + w + 2, y + h/2 + offset, x + w - 5, y + h + offset);
            ctx.quadraticCurveTo(x + w/2, y + h + 2 + offset, x + 5, y + h + offset);
            ctx.quadraticCurveTo(x - 2, y + h/2 + offset, x + 5, y + offset); ctx.stroke();
        }}
    }}
    function draw() {{
        ctx.clearRect(0, 0, GAME_W, GAME_H); ctx.lineCap = 'round'; ctx.lineJoin = 'round';
        platforms.forEach(p => {{
            const greenOutline = '#3e611f'; const greenFill = '#67c22e'; const brownOutline = '#5c3a1f'; const brownFill = '#a5681c';
            if (p.type === 'standard') {{
                drawFlattenedRoughOval(p.x, p.y, p.w, p.h, greenOutline, greenFill);
                if (p.hasSpring) {{ drawSpring(p.x + p.w - 25, p.y - 10, p.springAnim > 0); if(p.springAnim > 0) p.springAnim--; }}
            }} else if (p.type === 'breakable') {{
                drawFlattenedRoughOval(p.x, p.y, p.w, p.h, brownOutline, brownFill);
                ctx.strokeStyle = brownOutline; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(p.x + p.w/2, p.y); ctx.lineTo(p.x + p.w/2, p.y + p.h); ctx.stroke();
            }}
        }});
        brokenParts.forEach(bp => {{ ctx.save(); ctx.translate(bp.x + bp.w/2, bp.y + bp.h/2); ctx.rotate(bp.type === 'left' ? -bp.rot : bp.rot); drawFlattenedRoughOval(-bp.w/2, -bp.h/2, bp.w, bp.h, '#5c3a1f', '#a5681c'); ctx.restore(); }});
        drawDoodler(); if(!isGameOverAnimating) document.getElementById('score-display').innerText = score;
    }}
    function drawSpring(x, y, compressed) {{
        ctx.fillStyle = '#ccc'; ctx.strokeStyle = '#000'; ctx.lineWidth = 1; let h = compressed ? 5 : 10; let yOff = compressed ? 5 : 0;
        ctx.beginPath(); ctx.rect(x, y + yOff, 14, h); ctx.fill(); ctx.stroke(); ctx.beginPath(); ctx.moveTo(x, y+yOff+3); ctx.lineTo(x+14, y+yOff+3); ctx.stroke();
    }}
    function drawDoodler() {{
        ctx.save(); let cx = doodler.x + doodler.w/2; let cy = doodler.y + doodler.h/2;
        ctx.translate(cx, cy); if (doodler.dir === -1) ctx.scale(-1, 1);
        const bodyColor = '#d0e148'; const stripeColor = '#5e8c31'; const outlineColor = '#000';
        ctx.lineWidth = 3; ctx.fillStyle = bodyColor; ctx.strokeStyle = outlineColor;
        ctx.beginPath(); ctx.moveTo(-10, 15); ctx.lineTo(-10, 22); ctx.moveTo(0, 15); ctx.lineTo(0, 22); ctx.moveTo(10, 15); ctx.lineTo(10, 22); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(-18, 15); ctx.bezierCurveTo(-18, -15, -10, -25, 5, -20); ctx.bezierCurveTo(15, -20, 18, -10, 18, 15); ctx.lineTo(-18, 15); ctx.fill();
        ctx.save(); ctx.clip(); ctx.fillStyle = stripeColor; ctx.fillRect(-20, 10, 40, 3); ctx.fillRect(-20, 5, 40, 3); ctx.fillRect(-20, 0, 40, 3); ctx.restore(); ctx.stroke();
        ctx.fillStyle = bodyColor; ctx.beginPath(); ctx.moveTo(15, -12); ctx.lineTo(28, -15); ctx.bezierCurveTo(32, -14, 32, -6, 28, -5); ctx.lineTo(15, -5); ctx.fill(); ctx.stroke();
        ctx.fillStyle = outlineColor; ctx.beginPath(); ctx.ellipse(28, -10, 2, 4, 0, 0, Math.PI*2); ctx.fill();
        ctx.fillStyle = outlineColor; ctx.beginPath(); ctx.arc(0, -12, 2, 0, Math.PI*2); ctx.arc(8, -12, 2, 0, Math.PI*2); ctx.fill();
        ctx.restore();
    }}
    function startGame() {{
        document.getElementById('start-screen').classList.add('hidden');
        const goScreen = document.getElementById('game-over-screen'); goScreen.classList.remove('slide-up');
        document.getElementById('score-display').classList.remove('fade-out');
        document.getElementById('save-link').style.display = 'none';
        document.getElementById('auto-msg').style.display = 'block';
        
        // FIX 4: Enable canvas pointer events so user can tap to move
        canvas.style.pointerEvents = 'auto';
        
        isGameOverAnimating = false; init();
        if (!gameRunning) {{ gameRunning = true; requestAnimationFrame(loop); }}
    }}
    function loop() {{ if(gameRunning) {{ update(); draw(); requestAnimationFrame(loop); }} }}
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

# -------------------------------------------------------
# AUTO-SAVE SCORE HANDLER
# -------------------------------------------------------
try:
    # Retrieve Params (Streamlit > 1.30 syntax)
    qp = st.query_params
    new_score = qp.get("score")
    user_check = qp.get("user")
    
    if new_score and user_check:
        # Check against session state MIS
        if str(user_check).strip() == str(st.session_state.mis_no).strip():
            score_val = int(new_score)
            
            # Fetch branch info
            sub_dfs, sched_df, link_map = load_data()
            _, _, name, branch = get_schedule(st.session_state.mis_no, sub_dfs, sched_df)
            
            # Find previous high score
            full_df_temp = get_leaderboard_data()
            prev_high, _ = get_branch_highest(full_df_temp, branch)
            
            success, msg = update_leaderboard_score(name, branch, score_val)
            
            # Wait for API
            time.sleep(2.0)
            
            if score_val > prev_high:
                st.toast(f"🎉 New Personal Record: {score_val}!", icon="🏆")
            else:
                st.toast(f"Score saved: {score_val}", icon="✅")
        else:
            st.error(f"Security Warning: Score mismatch. User in Link: '{user_check}' vs Logged In: '{st.session_state.mis_no}'")
        
        # Clear params and rerun
        st.query_params.clear()
        st.rerun()
except Exception as e:
    pass

sub_dfs, sched_df, link_map = load_data()

# HEADER with Theme Toggle
h1_col, toggle_col = st.columns([8, 1])
with h1_col:
    # Defined as a variable to prevent SyntaxError with emojis
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
                st.sidebar.markdown(f"""<h3 style='background: linear-gradient(45deg, #a18cd1, #fbc2eb); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700; margin-bottom: 5px;'>📲 Calendar Sync</h3><p style='font-size: 11px; color: var(--text-color); margin-bottom: 10px;'>One click to add your entire semester schedule to your phone.</p>""", unsafe_allow_html=True)
                master_ics_data = generate_master_ics(table, SEMESTER_END)
                st.sidebar.download_button(label="📥 Sync Full Semester", data=master_ics_data, file_name=f"My_Semester_Timetable_{mis}.ics", mime="text/calendar")
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
            st.markdown("""<h3 style="font-size: 28px; font-weight: 700; margin-bottom: 20px; background: linear-gradient(to right, #6a11cb, #fbc2eb); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">🎮 Stress Buster Leaderboard</h3>""", unsafe_allow_html=True)

            with st.expander("Play & View High Scores", expanded=False):
                full_leaderboard_df = get_leaderboard_data()
                
                col_ctrl, col_stats = st.columns([1, 2])
                with col_ctrl:
                    view_mode = st.radio("View High Score:", ["Overall College", "By Branch"], horizontal=True)
                    
                    selected_branch_filter = "All"
                    if view_mode == "By Branch":
                        existing_branches = full_leaderboard_df['Branch'].unique().tolist() if not full_leaderboard_df.empty else []
                        defaults = ["AIML", "CSE", "IT", "ENTC", "MECH", "CIVIL", "INSTR"]
                        all_branches = sorted(list(set(existing_branches + defaults)))
                        selected_branch_filter = st.selectbox("Select Branch", all_branches, index=all_branches.index(branch) if branch in all_branches else 0)

                overall_score, overall_name, overall_branch = get_overall_highest(full_leaderboard_df)
                
                display_score = 0
                display_name = "-"
                display_label = ""
                
                if view_mode == "Overall College":
                    display_score = overall_score
                    display_name = f"{overall_name} ({overall_branch})"
                    display_label = "🏆 College Record"
                else:
                    s_score, s_name = get_branch_highest(full_leaderboard_df, selected_branch_filter)
                    display_score = s_score
                    display_name = s_name
                    display_label = f"🥇 {selected_branch_filter} Topper"

                with col_stats:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #FFD700 0%, #FDB931 100%); padding: 15px; border-radius: 12px; text-align: center; color: #5c3a1f; box-shadow: 0 4px 15px rgba(253, 185, 49, 0.4); display:flex; align-items:center; justify-content:space-around;">
                        <div style="text-align:left;">
                            <div style="font-size: 14px; font-weight: 700; text-transform:uppercase;">{display_label}</div>
                            <div style="font-size: 24px; font-weight: 800;">{display_score}</div>
                            <div style="font-size: 14px; opacity:0.9;">Held by: {display_name}</div>
                        </div>
                        <div style="font-size:40px;">👑</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("---")
                
                c_game_main, c_game_info = st.columns([3, 1])
                with c_game_main:
                    game_html = render_game_html(mis)
                    components.html(game_html, height=650, scrolling=False)
                
                with c_game_info:
                    st.info(f"**Playing as:**\n\n{name}\n\n({branch})")
                    st.warning("⚠️ **Note:**\nWhen the game ends, the page will reload automatically to save your score.")

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
