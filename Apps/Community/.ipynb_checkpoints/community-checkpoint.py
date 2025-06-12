import streamlit as st
import pandas as pd
from datetime import datetime
import io
import requests
from simple_salesforce import Salesforce
import os
from dotenv import load_dotenv

def process_attendance_data(csv_file):
    auth = pd.read_csv(csv_file)

    auth['Fan/Company'] = auth['First name'] + ' ' + auth['Last name']

    auth = auth[['Fan/Company', 'assign using  ID number', 'User Id', 'CloseLink reservation name', 'Attendance']]
    auth = auth.dropna(subset=['CloseLink reservation name'])

    auth['User Id'] = auth['User Id'].fillna(0).astype(int)

    distributed = auth.groupby('CloseLink reservation name').size().reset_index(name='Count')
    distributed = distributed.rename(columns={'CloseLink reservation name': 'שם העמותה'})
    distributed = distributed.rename(columns={'Count': 'כמות כרטיסים שנמשכו'})

    attendance = auth.groupby('CloseLink reservation name')['Attendance'].apply(lambda x: (x == 'Yes').sum()).reset_index()
    attendance.columns = ['CloseLink reservation name', 'count']
    attendance = attendance.rename(columns={'CloseLink reservation name': 'שם העמותה'})
    attendance = attendance.rename(columns={'count': 'כמות אנשים שהגיעו מכל עמותה'})

    final_table = pd.merge(distributed, attendance, on='שם העמותה', how='left')
    final_table[['כמות כרטיסים שנמשכו', 'כמות אנשים שהגיעו מכל עמותה']] = final_table[['כמות כרטיסים שנמשכו', 'כמות אנשים שהגיעו מכל עמותה']].astype(int)

    return auth, attendance, distributed, final_table

# Function to fetch marketing allowed data from Salesforce
def fetch_marketing_allowed_from_salesforce(auth_df):
    load_dotenv()

    sf_username = st.secrets["SF_USERNAME"]
    sf_password = st.secrets["SF_PASSWORD"]
    sf_security_token = st.secrets["SF_SECURITY_TOKEN"]

    sf = Salesforce(
    username=sf_username,
    password=sf_password,
    security_token=sf_security_token,
    )

    instance_url = sf.base_url.split('/services/data')[0]

    headers = {
        'Authorization': f'Bearer {sf.session_id}',
        'Content-Type': 'application/json'
    }

    user_ids = auth_df['User Id'].dropna().unique()
    results = []

    for user_id in user_ids:
        soql_query = f"""
                SELECT Id, Name, Account.Name, marketing_allowed__c, 
                    Phone, Email, Birthdate
                FROM Contact 
                WHERE HJBC_ID__c = '{user_id}'
            """
        query_url = f"{instance_url}/services/data/v57.0/query?q={soql_query}"

        response = requests.get(query_url, headers=headers)

        if response.status_code == 200:
            contacts = response.json().get("records", [])
            for record in contacts:
                try:
                    account_name = record["Account"]["Name"]
                except (TypeError, KeyError):
                    account_name = "N/A"

                results.append({
                    "User Id": user_id,
                    "Contact Name": record.get("Name", "N/A"),
                    "Account Name": record.get("Account", {}).get("Name", "N/A") if record.get("Account") else "N/A",
                    "Marketing Allowed": record.get("marketing_allowed__c", "N/A"),  # Fix casing if needed
                    "Phone": record.get("Phone", "N/A"),
                    "Email": record.get("Email", "N/A"),
                    "Birthdate": record.get("Birthdate", "N/A")
                })

        else:
            st.error(f"Error fetching data for User ID {user_id}: {response.text}")

    salesforce_data = pd.DataFrame(results)
    filtered_data = salesforce_data.dropna(subset=['Marketing Allowed'])
    filtered_data = filtered_data[filtered_data['User Id'] != 0]

    return filtered_data

# UI

# Initialize session state for file handling
if "uploaded_file" not in st.session_state:
    st.session_state.uploaded_file = None

# **Page Styling**
st.markdown(
    """
    <style>
    .stApp {
        background-image: url("https://raw.githubusercontent.com/gil-hapoel/social-icons/main/HAP08989.JPG");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        color: white;
        text-shadow: 2px 2px 4px black;
    }

    h1, h2, h3, h4, h5, h6 {
        color: white !important;
        text-shadow: 2px 2px 4px black !important;
    }

    a {
        color: cyan !important;
        font-weight: bold;
    }

    /* Make radio button labels white */
    div[data-baseweb="radio"] label {
        color: white !important;
        font-weight: bold !important;
        text-shadow: 1px 1px 2px black !important;
    }

    /* Ensure radio button text is readable */
    div[data-baseweb="radio"] div {
        color: white !important;
        font-weight: bold !important;
        text-shadow: 1px 1px 2px black !important;
    }

    /* Make radio button title (the question) white */
    div[data-testid="stRadio"] > label {
        color: white !important;
        font-weight: bold !important;
        text-shadow: 1px 1px 2px black !important;
    }

    /* Make radio button options white */
    div[data-baseweb="radio"] label {
        color: white !important;
        font-weight: bold !important;
        text-shadow: 1px 1px 2px black !important;
    }

    /* Ensure selected option text stays white */
    div[role="radiogroup"] > div {
        color: white !important;
    }

    /* Apply white color to all radio text */
    div[role="radiogroup"] * {
        color: white !important;
    }
    
    /* Fix issue where selected option text stays dark */
    div[role="radiogroup"] > div {
        color: white !important;
    }

    /* Ensure contrast and visibility */
    div[role="radiogroup"] * {
        color: white !important;
    }

/* Align text input label to the right */
    div[data-testid="stTextInput"] label {
        color: white !important;
        font-weight: bold !important;
        text-shadow: 1px 1px 2px black !important;
        text-align: right !important;
        display: block !important;
    }

    /* Align input text inside the box to the right */
    div[data-testid="stTextInput"] input {
        text-align: right !important;
        direction: rtl !important;
    }

    /* Center file uploader */
    div[data-testid="stFileUploader"] {
        display: flex;
        justify-content: center !important;
        align-items: center !important;
    }

    div[data-testid="stFileUploader"] label {
        color: white !important;
        text-shadow: 2px 2px 4px black !important;
        font-weight: bold;
        font-size: 24px !important;
        text-align: center !important;
        display: block;
    }

    div[data-testid="stFileUploader"] section {
        padding: 12px !important;
        border: 2px solid white !important;
        border-radius: 25px !important;
        background-color: rgba(255, 255, 255, 0.2) !important;
        width: 400px !important;
        height: 50px !important;
        text-align: center !important;
        justify-content: center !important;
        align-items: center !important;
        display: flex !important;
        margin: auto !important;
    }

    div[data-testid="stFileUploader"] section div {
        color: white !important; 
        font-weight: bold !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# **Page Title**
st.markdown("<h1 style='text-align: center;'> דוח קהילה</h1>", unsafe_allow_html=True)

# st.markdown("<h2 style='text-align: right;'>הוראות כיצד להוריד את הדוח הרצוי ממערכת רובוטיקט</h2>", unsafe_allow_html=True)

# st.markdown("<br>", unsafe_allow_html=True)

# # Step 1: Login
# st.markdown("<h4 style='text-align: right;'>בעזרת הלינק Roboticket התחבר/י למערכת</h4>", unsafe_allow_html=True)
# st.markdown(
#     "<h4 style='text-align: right;'><a href='https://tickets.hapoel.co.il/Boxoffice' target='_blank'>https://tickets.hapoel.co.il/Boxoffice</a></h4>", 
#     unsafe_allow_html=True
# )
# # st.image("https://raw.githubusercontent.com/gil-hapoel/social-icons/main/Screenshot%202025-02-26%20at%2017.19.22.png", use_container_width=True)
# st.image("https://raw.githubusercontent.com/gil-hapoel/social-icons/main/Screenshot%202025-02-26%20at%2017.19.22.png")


# # Step 2: Reports section
# st.markdown("<h4 style='text-align: right;'>לחצ/י על האייקון של הדוחות</h4>", unsafe_allow_html=True)
# st.image("https://raw.githubusercontent.com/gil-hapoel/social-icons/main/Screenshot%202025-02-26%20at%2017.26.51.png", use_container_width=True)

# #  Step 3: Games Authorization Report
# st.markdown("<h4 style='text-align: right;'>Games authorization report לחצ/י על</h4>", unsafe_allow_html=True)
# st.image("https://raw.githubusercontent.com/gil-hapoel/social-icons/main/Screenshot%202025-02-26%20at%2017.29.20.png", use_container_width=True)

# # Step 4: Select the game
# st.markdown("<h4 style='text-align: right;'>בחר/י את המשחק הרצוי</h4>", unsafe_allow_html=True)
# st.markdown("<h4 style='text-align: right;'>GETEVENTS אם אינך רואה את המשחק, לחצ/י על כפתור</h4>", unsafe_allow_html=True)
# st.image("https://raw.githubusercontent.com/gil-hapoel/social-icons/main/Screenshot%202025-02-26%20at%2017.30.33.png", use_container_width=True)

# # Step 5: Download the report
# st.markdown("<h4 style='text-align: right;'>לאחר מציאת המשחק הרצוי, לחצ/י על הכפתור האמצעי כדי להוריד את הדוח</h4>", unsafe_allow_html=True)
# st.image("https://raw.githubusercontent.com/gil-hapoel/social-icons/main/Screenshot%202025-02-26%20at%2017.32.40.png", use_container_width=True)

st.markdown("<h4 style='text-align: right;'>אנא העלה/י את דוח המשחק המלא</h4>", unsafe_allow_html=True)
uploaded_file = st.file_uploader("", type="csv")

if uploaded_file is not None:
    st.markdown("<h4 style='text-align: right;'>!הקובץ הועלה בהצלחה</h4>", unsafe_allow_html=True)

    # Process uploaded CSV file
    auth, attendance_data, distributed_data, final_data = process_attendance_data(uploaded_file)

    st.markdown("<h4 style='text-align: right;'>:כרטיסי הקהילה שחולקו לעמותות</h4>", unsafe_allow_html=True)
    st.write(final_data)

    if attendance_data.empty:
        st.markdown(
            "<div style='text-align: right; color: #856404; background-color: #fff3cd; padding: 10px; border-radius: 5px; border: 1px solid #ffeeba;'>⚠️ לא נמצאו כרטיסים שחולקו לעמותות</div>",
            unsafe_allow_html=True
        )
        st.stop()

    # **Check if 'כמות אנשים שהגיעו מכל עמותה' exists and its values are all 0**
    if 'כמות אנשים שהגיעו מכל עמותה' in final_data.columns and final_data['כמות אנשים שהגיעו מכל עמותה'].sum() == 0:
        st.markdown(
            "<div style='text-align: right; color: #856404; background-color: #fff3cd; padding: 10px; border-radius: 5px; border: 1px solid #ffeeba;'>⚠️ לא נמצאו נתוני הגעה</div>",
            unsafe_allow_html=True
        )
        st.stop()
 

    if "delete_done" not in st.session_state:
        st.session_state.delete_done = False

    # **Store attendance_data in session state initially**
    if "final_data" not in st.session_state:
        st.session_state.final_data = final_data  # Store initial data

    st.markdown("<h4 style='text-align: right;'>?האם ברצונך למחוק שורות מהטבלה</h4>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([2, 1, 1])  # Adjust column widths
    with col1:
        st.write("")  # Empty space
    with col2:
        st.write("")  # Empty space
    with col3:
        delete_mode = st.radio(":בחר באחת מהאפשרויות", ["לא למחוק", "למחוק שורות מסוימות"])

     # **Ensure final_data is stored in session state**
    if "final_data" not in st.session_state:
        st.session_state.final_data = final_data  # Store initial data

    # **If user chooses to delete rows**
    if delete_mode == "למחוק שורות מסוימות":
        delete_indices = st.text_input("הכנס מספרי שורות למחיקה (מופרדים בפסיק)", "")

        if delete_indices:
            try:
                # Convert input into a list of integers
                indices_to_delete = [int(i.strip()) for i in delete_indices.split(",")]

                # Check if indices exist in DataFrame
                if all(i in final_data.index for i in indices_to_delete):
                    # Remove rows based on index
                    final_data = final_data.drop(indices_to_delete).reset_index(drop=True)

                    st.markdown("<h4 style='text-align: right;'>!השורות שנבחרו נמחקו בהצלחה</h4>", unsafe_allow_html=True)
                    st.write(final_data)  # Show updated table
                else:
                    st.error("אחת או יותר מהשורות שסיפקת אינה קיימת. נסה שוב.")
            except ValueError:
                st.error("יש להכניס מספרים מופרדים בפסיק בלבד.")

    # **Group by and process the updated final_data**
    temp = final_data.merge(auth, left_on='שם העמותה', right_on='CloseLink reservation name', how='left')
    tempp = temp.copy()
    tempp = tempp[tempp['Attendance'] == 'Yes']
    final_data = tempp.copy()

    # **Rename columns for clarity**
    # final_data = [['שם העמותה', 'Fan/Company', 'User Id']]

    # **Filter out rows where count is 0**
    # final_data = final_data[final_data['count'] > 0]

    # **Now, store the processed DataFrame into session state**
    st.session_state.final_data = final_data

    st.markdown("<h2 style='text-align: right;'>SF מתחבר למערכת</h2>", unsafe_allow_html=True)
    with st.spinner('Fetching marketing allowed data...'):
        filtered_data = fetch_marketing_allowed_from_salesforce(st.session_state.final_data)

    if not filtered_data.empty:
        col1, col2, col3 = st.columns([1, 1, 2])  # Create 3 columns
        with col1:
            st.write("")  # Empty space for alignment
        with col2:
            st.write("")  # Another empty space
        with col3:
            st.markdown("<h4 style='text-align: right;'>התבצע בהצלחה SF החיבור מול </h4>", unsafe_allow_html=True)


        # Merge attendance with Salesforce data
        merged = final_data.merge(filtered_data, on='User Id', how='inner')

        # Select relevant columns, including new ones
        merged = merged[['Fan/Company', 'User Id', 'שם העמותה', 
                        'Marketing Allowed', 'Phone', 'Email', 'Birthdate']]
        
        # Calculate age from Birthdate
        current_year = datetime.today().year

        # Convert Birthdate to datetime and extract the year
        merged['Birthdate'] = pd.to_datetime(merged['Birthdate'], errors='coerce')
        merged['Age'] = current_year - merged['Birthdate'].dt.year

        # Replace NaN values in Age with 'Unknown' if Birthdate is missing
        merged['Age'] = merged['Age'].fillna(0).astype(int)

        # Drop the original Birthdate column
        merged = merged.drop(columns=['Birthdate'])
        
        # Rename columns for better readability (Hebrew-friendly)
        merged = merged.rename(columns={
            'Fan/Company': 'שם מלא',
            # 'CloseLink reservation name': 'שם העמותה',
            'Marketing Allowed': 'אישור דיוור',
            'Phone': 'טלפון נייד',
            'Email': 'כתובת אימייל',
            'Age': 'גיל'
        })

        st.markdown("<h4 style='text-align: right;'>אנשים שהגיעו למשחק</h4>", unsafe_allow_html=True)
        st.write(merged)
    else:
        st.warning("SF לא נמצאו נתונים תואמים במערכת")



    # ========== אנשים שלא הגיעו למשחק ==========
    # Step 1: Filter from auth where attendance is NO / False
    non_attendees_df = auth[auth['Attendance'].astype(str).str.strip().str.lower().isin(['no', 'false'])]

    # Optional: store in session state
    st.session_state.non_attendees_df = non_attendees_df

    # Step 2: Fetch Salesforce data for these non-attendees
    with st.spinner('Fetching marketing allowed data for non-attendees...'):
        filtered_data_na = fetch_marketing_allowed_from_salesforce(non_attendees_df)

    # Step 3: Merge auth (non-attendees) with SF
    if not filtered_data_na.empty:
        merged_na = non_attendees_df.merge(filtered_data_na, on='User Id', how='inner')
        # Filter only those with Marketing Allowed = True
        merged_na = merged_na[merged_na['Marketing Allowed'] == True]

        # Step 4: Pick relevant columns (if they exist)
        cols_to_keep = ['Fan/Company', 'User Id', 'CloseLink reservation name', 
                        'Marketing Allowed', 'Phone', 'Email', 'Birthdate']
        cols_to_keep = [col for col in cols_to_keep if col in merged_na.columns]
        merged_na = merged_na[cols_to_keep]

        # Step 5: Age calculation
        if 'Birthdate' in merged_na.columns:
            merged_na['Birthdate'] = pd.to_datetime(merged_na['Birthdate'], errors='coerce')
            merged_na['Age'] = datetime.today().year - merged_na['Birthdate'].dt.year
            merged_na['Age'] = merged_na['Age'].fillna(0).astype(int)
            merged_na = merged_na.drop(columns=['Birthdate'])
        else:
            merged_na['Age'] = 'לא ידוע'

        # Step 6: Rename for display
        merged_na = merged_na.rename(columns={
            'Fan/Company': 'שם מלא',
            'CloseLink reservation name': 'שם העמותה',
            'Marketing Allowed': 'אישור דיוור',
            'Phone': 'טלפון נייד',
            'Email': 'כתובת אימייל',
            'Age': 'גיל'
        })

        # Step 7: Show final clean table
        final_cols = ['שם מלא', 'User Id', 'שם העמותה', 'אישור דיוור', 'טלפון נייד', 'כתובת אימייל', 'גיל']
        final_cols = [col for col in final_cols if col in merged_na.columns]
        merged_na = merged_na.loc[:, ~merged_na.columns.duplicated()]
        merged_na = merged_na[final_cols]

        st.markdown("<h4 style='text-align: right;'>רשימת אנשים שלא הגיעו למשחק אך משכו כרטיס ואישרו דיוור</h4>", unsafe_allow_html=True)
        st.write(merged_na)

    else:
        st.warning("SF לא נמצאו נתונים תואמים במערכת")
