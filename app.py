import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import pandas as pd
import os
import re
import zlib
import json
from datetime import datetime, timedelta, date
from difflib import SequenceMatcher

# --------------------------------------------------
# 1. PAGE CONFIGURATION & CONSTANTS
# --------------------------------------------------
st.set_page_config(page_title="Student Timetable", page_icon="✨", layout="wide")

DATA_FOLDER = "data"
TIMETABLE_FILE = "timetable_schedule.xlsx"
ATTENDANCE_FILE = "attendance_data.json"

# SEMESTER DATES
SEMESTER_START = date(2026, 1, 12)
SEMESTER_END = date(2026, 5, 7)

# --------------------------------------------------
# 2. GLOBAL STYLES
# --------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');

/* BACKGROUND */
.stApp { background-color: #f1f0f6; }

/* GLOBAL FONT */
html, body, [class*="css"], .stMarkdown, div, span, p {
    font-family: 'Poppins', sans-serif;
    color: #2c3e50;
}

/* --- FIX 1: DARK ROUNDED INPUT BOX (For Text Input) --- */
/* Target the container */
div[data-baseweb="input"] {
    border: none; /* Remove default border */
    border-radius: 50px !important; /* Fully Rounded */
    background-color: #262730; /* Dark background color */
    padding: 8px 20px;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.5); /* Inner shadow for depth */
    color: white !important; /* White text */
}

/* Target the actual input field inside */
div[data-baseweb="input"] input {
    color: white !important;
    caret-color: white; /* White cursor */
}

/* Focus state - optional purple glow */
div[data-baseweb="input"]:focus-within {
    box-shadow: 0 0 0 2px #6a11cb, inset 0 2px 4px rgba(0,0,0,0.5) !important;
}


/* --- FIX: DATE PICKER VISIBILITY (WHITE TEXT) --- */
/* The container for the date picker often inherits the dark style, so we force white text */
div[data-testid="stDateInput"] input {
    color: #ffffff !important; /* Force White Text */
    font-weight: 600;
}

/* --- EXPANDER HEADER (ALLOCATED SUBJECTS) - LIGHT BLUE GRADIENT --- */
[data-testid="stExpander"] summary p {
    background: -webkit-linear-gradient(45deg, #4facfe, #00f2fe);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 18px !important;
    font-weight: 800 !important;
}

/* --- BUTTONS --- */

/* --- FIX 2: MARK BUTTON TEXT COLOR --- */
/* Primary Button (Mark) -> Purple Gradient Background, WHITE Text */
div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%) !important;
    border: none !important;
    border-radius: 50px !important;
    font-weight: 600;
    box-shadow: 0 4px 10px rgba(106, 17, 203, 0.2);
    transition: transform 0.2s;
}
/* FORCE WHITE TEXT on the button and any internal elements */
div.stButton > button[kind="primary"],
div.stButton > button[kind="primary"] * {
    color: #ffffff !important; 
}

div.stButton > button[kind="primary"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 15px rgba(106, 17, 203, 0.3);
}

/* Secondary Button (Change User / Undo) -> White BG, Purple Text */
div.stButton > button[kind="secondary"] {
    background-color: white !important;
    color: #6a11cb !important; 
    border: 2px solid #6a11cb !important;
    border-radius: 50px !important;
    font-weight: 600;
}
div.stButton > button[kind="secondary"]:hover {
    background-color: #f3e5f5 !important;
}

/* --- TIMETABLE GRID --- */
.timetable-wrapper { overflow-x: auto; padding: 20px 5px 40px 5px; }
table.custom-grid { width: 100%; min-width: 1000px; border-collapse: separate; border-spacing: 10px; }

.custom-grid th {
    background: linear-gradient(90deg, #8EC5FC 0%, #E0C3FC 100%);
    color: #2c3e50; font-weight: 800; padding: 15px; border-radius: 15px;
    text-align: center; font-size: 18px; box-shadow: 0 4px 10px rgba(142, 197, 252, 0.4); border: none;
    text-transform: uppercase; letter-spacing: 1px;
}
.custom-grid th:first-child { background: transparent; box-shadow: none; width: 140px; }

.custom-grid td:first-child {
    background: linear-gradient(90deg, #8EC5FC 0%, #E0C3FC 100%);
    border-radius: 15px; font-size: 14px; font-weight: 800; color: #2c3e50;
    text-align: center; vertical-align: middle; box-shadow: 0 4px 10px rgba(142, 197, 252, 0.4);
    min-width: 140px; white-space: nowrap;
}
.custom-grid td { vertical-align: top; height: 110px; padding: 0; border: none; }

/* CARD & HOVER EFFECTS */
.class-card {
    height: 100%; width: 100%; padding: 12px; box-sizing: border-box;
    display: flex; flex-direction: column; justify-content: center;
    border-radius: 18px; transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
    position: relative; cursor: default;
}
.class-card.filled {
    color: #2c3e50; border: 1px solid rgba(255,255,255,0.4);
    box-shadow: 0 4px 6px rgba(0,0,0,0.05);
}
.class-card.filled:hover {
    transform: translateY(-5px) scale(1.03);
    box-shadow: 0 15px 30px rgba(0,0,0,0.15);
    z-index: 100;
}
.type-empty {
    background: rgba(255, 255, 255, 0.5);
    border: 2px dashed rgba(160, 160, 200, 0.2); border-radius: 18px;
}
.sub-title { font-weight: 700; font-size: 13px; margin-bottom: 4px; }
.sub-meta { font-size: 11px; opacity: 0.9; }
.batch-badge {
    background: rgba(255,255,255,0.6); padding: 3px 8px; border-radius: 10px;
    font-size: 10px; font-weight: 700; text-transform: uppercase; display: inline-block;
    margin-bottom: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

/* ATTENDANCE CARDS */
.metric-card {
    background: white; border-radius: 20px; padding: 20px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.05); text-align: center;
    border: 1px solid #f0f0f0; height: 100%; transition: transform 0.2s;
}
.metric-card:hover { transform: translateY(-5px); }
.metric-value {
    font-size: 32px; font-weight: 800;
    background: -webkit-linear-gradient(45deg, #6a11cb, #2575fc);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.daily-card {
    background: white; border-radius: 18px; padding: 20px; margin-bottom: 15px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.05); display: flex; justify-content: space-between;
    align-items: center; border-left: 6px solid #6a11cb;
}
.student-card { background: #ffffff; border-radius: 24px; padding: 30px; text-align: center; margin-bottom: 30px; box-shadow: 0 10px 25px rgba(106, 17, 203, 0.1); }
.student-name { font-size: 28px; font-weight: 700; background: -webkit-linear-gradient(45deg, #6a11cb, #2575fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 5px; }
.student-meta { font-size: 15px; color: #7f8c8d; font-weight: 500; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# 3. HELPERS
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
def get_google_sheet():
    # Load credentials from Streamlit Secrets
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    
    # Open the sheet by URL (Paste your URL in secrets later, or hardcode it here if private)
    sheet_url = st.secrets["private_sheet_url"] 
    return client.open_by_url(sheet_url).sheet1

def load_attendance():
    try:
        sheet = get_google_sheet()
        # Get all IDs listed in Column 1 (A)
        # We assume Column A contains the 'cls_id' strings
        data = sheet.col_values(1)
        # Convert list to dictionary format expected by the app
        return {cls_id: True for cls_id in data if cls_id}
    except Exception as e:
        st.error(f"Database Connection Error: {e}")
        return {}

def update_attendance_in_sheet(cls_id, action):
    """
    Directly updates the sheet without rewriting everything.
    action: 'add' or 'remove'
    """
    try:
        sheet = get_google_sheet()
        if action == "add":
            # Append the ID to the next available row in Column A
            sheet.append_row([cls_id])
        elif action == "remove":
            # Find the cell with the ID and delete that row/cell
            cell = sheet.find(cls_id)
            if cell:
                sheet.delete_rows(cell.row)
    except Exception as e:
        st.warning(f"Could not sync with cloud: {e}")

# --------------------------------------------------
# 4. DATA LOADING & LOGIC
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
                        raw_sub = row.iloc[0]
                        fixed_sub = correct_subject_name(raw_sub)
                        clean_sub = clean_text(fixed_sub) 
                        link_url = str(row.iloc[1]).strip()
                        link_map[clean_sub] = link_url
            else:
                sub_dfs.append(df)
        except: continue
        
    return sub_dfs, sched_df, link_map

def get_schedule(mis, sub_dfs, sched_df):
    found_subs = []
    name, branch = "Unknown", "Unknown"
    target_mis = clean_mis(mis)
    
    # 1. FIND ALLOCATED SUBJECTS
    for df in sub_dfs:
        mis_col = next((c for c in df.columns if "MIS" in c.upper()), None)
        if not mis_col: continue
        
        df["_KEY"] = df[mis_col].apply(clean_mis)
        match = df[df["_KEY"] == target_mis]
        if not match.empty:
            row = match.iloc[0]
            if name == "Unknown":
                name = row.get(next((c for c in df.columns if "Name" in c), ""), "Student")
                branch = row.get(next((c for c in df.columns if "Branch" in c), ""), "-")
            
            sub_col = next((c for c in df.columns if "Subject" in c or "Title" in c), None)
            div_col = next((c for c in df.columns if "Division" in c), None)
            batch_col = next((c for c in df.columns if "Batch" in c or "BATCH" in c.upper()), None)
            
            if sub_col:
                raw_subject = str(row[sub_col]).strip()
                fixed_subject = correct_subject_name(raw_subject)
                
                found_subs.append({
                    "Subject": fixed_subject,
                    "Division": str(row[div_col]).strip() if div_col else "",
                    "Batch": str(row[batch_col]) if batch_col else ""
                })

    # 2. FILTER MASTER TIMETABLE
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
                            "Day": str(row[t_day_col]).title().strip(),
                            "StartTime": start, "Duration": dur,
                            "Subject": sub['Subject'],
                            "Type": "LAB" if is_lab else "THEORY",
                            "Venue": str(row[t_venue_col]) if t_venue_col else "-"
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

    html = '<div class="timetable-wrapper"><table class="custom-grid">'
    html += '<thead><tr><th>Time</th>' + ''.join([f'<th>{d}</th>' for d in days]) + '</tr></thead><tbody>'
    
    for s in slots:
        label = f"{s} - {str(int(s.split(':')[0])+1)}:{s.split(':')[1]}"
        html += f'<tr><td class="time-label">{label}</td>'
        for d in days:
            cell = grid[s][d]
            if cell == "MERGED": continue
            if cell:
                span = f'rowspan="{cell["Duration"]}"' if cell['Duration'] > 1 else ''
                grad = get_subject_gradient(cell['Subject'])
                html += f'<td {span}><div class="class-card filled" style="background:{grad}">'
                html += f'<div class="batch-badge">{cell["Type"]}</div>'
                html += f'<div class="sub-title">{cell["Subject"]}</div>'
                html += f'<div class="sub-meta">📍 {cell["Venue"]}</div></div></td>'
            else:
                html += '<td><div class="class-card type-empty"></div></td>'
        html += '</tr>'
    return html + '</tbody></table></div>'

def render_subject_html(subjects, link_map):
    html_parts = []
    html_parts.append("""
    <style>
    .sub-alloc-wrapper { font-family: 'Poppins', sans-serif; margin-top: 10px; border-radius: 12px; overflow: hidden; border: none; box-shadow: 0 4px 20px rgba(0,0,0,0.05); background: white; }
    table.sub-alloc-table { width: 100%; border-collapse: collapse; background: white; }
    .sub-alloc-table thead th { background: linear-gradient(90deg, #a18cd1 0%, #fbc2eb 100%); color: white; padding: 18px; font-size: 17px; font-weight: 700; text-align: left; }
    .sub-alloc-table tbody td { padding: 16px; font-size: 16px; color: #2c3e50; border-bottom: 1px solid #f0f0f0; background: #ffffff; vertical-align: middle; transition: all 0.2s; }
    
    .sub-alloc-table tbody tr:hover td { background-color: #f8f9fa; transform: scale(1.005); color: #6a11cb; cursor: default; }

    .drive-btn { background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%); color: white !important; padding: 8px 16px; border-radius: 50px; text-decoration: none; font-size: 13px; font-weight: 600; display: inline-block; transition: 0.2s; }
    .drive-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 15px rgba(37, 117, 252, 0.3); }
    </style>
    """)
    
    html_parts.append('<div class="sub-alloc-wrapper"><table class="sub-alloc-table"><thead><tr><th style="width:40%">Subject Name</th><th style="width:20%">Batch</th><th style="width:20%">Division</th><th style="width:20%">Material</th></tr></thead><tbody>')
    
    for sub in subjects:
        link = link_map.get(clean_text(sub.get('Subject')), "#")
        link_html = f'<a href="{link}" target="_blank" class="drive-btn">📂 Open Drive</a>' if link != "#" else "<span style='color:#ccc'>No Link</span>"
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
                key = f"{cls['Subject']}|{cls['Type']}"
                totals[key] += 1
        curr_date += timedelta(days=1)
    return totals

# --------------------------------------------------
# 5. MAIN APPLICATION
# --------------------------------------------------

if 'mis_no' not in st.session_state:
    st.session_state.mis_no = ""
if 'attendance' not in st.session_state:
    st.session_state.attendance = load_attendance()

sub_dfs, sched_df, link_map = load_data()

# HEADER
st.markdown("""
    <h1 style='text-align: left; background: linear-gradient(to right, #6a11cb, #2575fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 3em; font-weight: 800; padding-top:10px;'>
    ✨ Smart Semester Timetable
    </h1>
""", unsafe_allow_html=True)

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
        
        # LOGOUT
        c1, c2 = st.columns([9, 1])
        with c2: 
            if st.button("Change User", type="secondary"):
                st.session_state.mis_no = ""
                st.rerun()

        # GET DATA
        subs, table, name, branch = get_schedule(mis, sub_dfs, sched_df)

        if subs:
            # --- PROFILE ---
            st.markdown(f"""
            <div class="student-card">
                <div class="student-name">{name}</div>
                <div class="student-meta">{branch} • MIS: {mis}</div>
            </div>""", unsafe_allow_html=True)

            # --- 1. WEEKLY SCHEDULE ---
            st.markdown("""<h3 style="font-size: 28px; font-weight: 700; margin: 20px 0; background: linear-gradient(to right, #6a11cb, #fbc2eb); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">🗓️ Weekly Schedule</h3>""", unsafe_allow_html=True)
            
            if table:
                st.markdown(render_grid(table), unsafe_allow_html=True)
            else:
                st.warning("No schedule found.")

            # --- ALLOCATED SUBJECTS (Header Color: Light Blue) ---
            with st.expander("Subject Allocation List", expanded=False):
                st.markdown(render_subject_html(subs, link_map), unsafe_allow_html=True)
            
            # CSS to handle the expander title gradient (Light Blue)
            st.markdown("""
            <style>
            [data-testid="stExpander"] summary { color: transparent; }
            [data-testid="stExpander"] summary p {
                 background: -webkit-linear-gradient(45deg, #4facfe, #00f2fe); /* Light Blue */
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-weight: 800;
            }
            </style>
            """, unsafe_allow_html=True)


            # --- 2. ATTENDANCE TRACKER ---
            st.markdown("""<hr style="border:1px solid #e0e0e0; margin: 40px 0;">""", unsafe_allow_html=True)
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
                        
                        border_color = "#6a11cb" if is_present else "#e0e0e0"
                        
                        c_info, c_action = st.columns([4, 1])
                        with c_info:
                            st.markdown(f"""
                            <div class="daily-card" style="border-left: 5px solid {border_color};">
                                <div class="daily-info">
                                    <h4>{cls['Subject']}</h4>
                                    <p>⏰ {cls['StartTime']} • {cls['Type']} • 📍 {cls['Venue']}</p>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        with c_action:
                            # Primary button now has White Text by CSS force
                            btn_label = "Mark ✓" if not is_present else "Undo ✕"
                            btn_type = "primary" if not is_present else "secondary"
                            
                            if st.button(btn_label, key=cls_id, type=btn_type, use_container_width=True):
                                if is_present:
                                    # Optimistic UI update (update local state immediately)
                                    del st.session_state.attendance[cls_id]
                                    # Sync with Google Sheets
                                    update_attendance_in_sheet(cls_id, "remove")
                                else:
                                    # Optimistic UI update
                                    st.session_state.attendance[cls_id] = True
                                    # Sync with Google Sheets
                                    update_attendance_in_sheet(cls_id, "add")
    
                                st.rerun()
                            
                            

            # --- 3. CALCULATOR ---
            st.markdown("""<hr style="border:1px solid #e0e0e0; margin: 40px 0;">""", unsafe_allow_html=True)
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
                bg_color = "#f0f0f0"
                msg_color = "#27ae60"

                if percentage < 60:
                    border_grad = "linear-gradient(135deg, #ff9a9e, #fecfef)" 
                    bg_color = "#fff5f5"
                    msg_color = "#c0392b"
                elif percentage < 75:
                    border_grad = "linear-gradient(135deg, #f6d365, #fda085)"
                    bg_color = "#fffdf5"
                    msg_color = "#d35400"
                else:
                    border_grad = "linear-gradient(135deg, #a18cd1, #fbc2eb)"
                    bg_color = "#f5fff5"

                with row_cols[col_idx % 3]:
                    st.markdown(f"""
                    <div class="metric-card" style="border-top: 5px solid transparent; border-image: {border_grad} 1; background-color: {bg_color};">
                        <div class="metric-title">{subject_name} <br> <span style="font-size:10px; color:#aaa">({subject_type})</span></div>
                        <div class="metric-value">{percentage:.1f}%</div>
                        <div class="metric-sub">{attended} / {total_count} Sessions</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if needed > 0:
                        st.markdown(f"<div style='text-align:center; margin-top:10px; color:{msg_color}; font-weight:600; font-size:14px;'>Attend {int(needed) + 1} more to hit 75%</div>", unsafe_allow_html=True)
                    else:
                         st.markdown(f"<div style='text-align:center; margin-top:10px; color:{msg_color}; font-weight:600; font-size:14px;'>Safe!</div>", unsafe_allow_html=True)
                    
                    st.write("") 
                col_idx += 1

        else:
            st.error("MIS not found.")
            if st.button("Try Again"):
                st.session_state.mis_no = ""
                st.rerun()

# FOOTER (Text Color: Black)
st.markdown("""
<div style="text-align: center; margin-top: 50px; font-size: 13px; color: #000000;">
    Student Portal © 2026 • Built by <span style="color:#6a11cb; font-weight:700">IRONDEM2921 [AIML]</span>
</div>
""", unsafe_allow_html=True)
