import streamlit as st
import pandas as pd
from datetime import datetime
import io

st.title('דוח תשלומים לפי משחק')
st.subheader('אנא להעלות את דוח המשחק המלא')

uploaded_file = st.file_uploader('Choose a CSV2 file', type="csv")

if uploaded_file is not None:
    st.write('File uploaded...')
    detailed_report = pd.read_csv(uploaded_file)

    st.subheader('Data Preview')
    detailed_report['Date.1'] = pd.to_datetime(detailed_report['Date.1'])

    detailed_report = detailed_report[detailed_report['Status'] == 'Active']
    

    # Payment method selection
    payment_methods = detailed_report['Payment method'].unique()
    st.subheader('בחרי את שיטת התשלום הרצויה')
    selected_payment_method = st.selectbox('Select Payment Method', payment_methods)


    # Date selection
    st.subheader('בחרי את התאריך אותם את רוצה שהדוח הסופי יציג')
    min_date = detailed_report['Date.1'].min()
    max_date = detailed_report['Date.1'].max()
    start_date, end_date = st.date_input(
        'Select Date Range',
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    detailed_report = detailed_report[(detailed_report['Date.1'] >= start_date) & (detailed_report['Date.1'] <= end_date)]
    detailed_report = detailed_report[detailed_report['Payment method'] == selected_payment_method]

    agg_file = (
        detailed_report[['User Id', 'Price']]
        .groupby('User Id', dropna=False)
        .agg(
            Price=('Price', 'sum'),
            Total_Tickets=('Price', 'count')  # Counts the number of transactions
        )
        .reset_index()
    )


    agg_file = agg_file.merge(
        detailed_report[['User Id', 'Fan / Company']].drop_duplicates(subset='User Id'),
        on='User Id',
        how='left'
    )

    agg_file = agg_file[['Fan / Company', 'User Id', 'Price','Total_Tickets']]

    # show the data
    st.dataframe(agg_file, height=600)

    total_price = agg_file['Price'].sum()
    st.subheader(f'סך התשלומים שהתקבלו הוא: {total_price:,.2f}')

    # Option to download the output as an Excel file
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        agg_file.to_excel(writer, sheet_name='Filtered_Data', index=False)
        writer.close()

    st.download_button(
        label="להורדת הקובץ הסופי, אנא לחץ כאן",
        data=output.getvalue(),
        file_name="filtered_output.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


    st.subheader(""":ולסיום
     הלכתי
    אחוז בשיגעון
    אלך איתך הפועל עד יומי האחרון
    וכל השבוע על זה אני חושב
    מחכה לצעוק לך שאותך אני אוהב""")
