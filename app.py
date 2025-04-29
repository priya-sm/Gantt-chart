import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Set page configuration
st.set_page_config(layout="wide")
st.title("📊 Consultant Effort Gantt Chart Generator")

# Ask user to upload an Excel file
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx", "xls"])

if uploaded_file:
    # Read the uploaded Excel file
    dataset = pd.read_excel(uploaded_file)

    # Rename columns for consistency
    df_weekly = dataset.copy()
    df_weekly.rename(columns={
        "ConsultantName": "name",
        "ProjectName": "project",
        "Efforts_Percentage": "effort",
        "StartDate": "start",
        "EndDate": "end"
    }, inplace=True)

    # Convert date columns to datetime and effort to numeric
    df_weekly['start'] = pd.to_datetime(df_weekly['start'])
    df_weekly['end'] = pd.to_datetime(df_weekly['end'])
    df_weekly['effort'] = pd.to_numeric(df_weekly['effort'], errors='coerce')

    # Expand data to weekly rows
    rows = []
    for _, row in df_weekly.iterrows():
        if pd.isnull(row['start']) or pd.isnull(row['end']) or pd.isnull(row['effort']):
            continue

        week_start = row['start'] - pd.to_timedelta(row['start'].weekday(), unit='D')
        last_week = row['end'] - pd.to_timedelta(row['end'].weekday(), unit='D')

        while week_start <= last_week:
            rows.append({
                "name": row['name'],
                "project": row['project'],
                "week_start": week_start,
                "effort": row['effort']
            })
            week_start += pd.Timedelta(weeks=1)

    expanded_df = pd.DataFrame(rows)

    # Sum efforts
    weekly_sum = (
        expanded_df.groupby(['name', 'week_start'])['effort']
        .sum()
        .reset_index()
        .rename(columns={'effort': 'Effort%'})
    )

    expanded_df = expanded_df.merge(weekly_sum, on=['name', 'week_start'], how='left')
    expanded_df['week_end'] = expanded_df['week_start'] + pd.Timedelta(days=6)

    # Filters
    # Date filter
    start_date = st.date_input("Start Date", expanded_df['week_start'].min())
    end_date = st.date_input("End Date", expanded_df['week_start'].max())

    # Consultant Name filter
    consultant_names = st.multiselect("Select Consultant(s)", options=expanded_df['name'].unique(), default=expanded_df['name'].unique())

    # Apply filters
    filtered_df = expanded_df[(expanded_df['week_start'] >= pd.to_datetime(start_date)) & 
                              (expanded_df['week_start'] <= pd.to_datetime(end_date)) & 
                              (expanded_df['name'].isin(consultant_names))]

    # Plot
    fig = px.timeline(
        filtered_df,
        x_start="week_start",
        x_end="week_end",
        y="name",
        color="project",
        hover_data={
            "name": True,
            "Effort%": ':.2f',
            "project": True,
            "week_start": False,
            "week_end": False
        },
        title="Gantt Chart: Total Effort per Person"
    )

    fig.update_yaxes(autorange="reversed")

    # Vertical week lines
    weeks = sorted(filtered_df['week_start'].unique())
    for week in weeks:
        fig.add_shape(
            type="line",
            x0=week,
            y0=0,
            x1=week,
            y1=1,
            xref='x',
            yref='paper',
            line=dict(color="lightgrey", width=1)
        )

    # Today marker
    today = pd.to_datetime("today").normalize()
    fig.add_shape(
        type="line",
        x0=today,
        y0=0,
        x1=today,
        y1=1,
        xref='x',
        yref='paper',
        line=dict(color="red", width=2, dash="dot")
    )
    fig.add_annotation(
        x=today,
        y=1.02,
        xref='x',
        yref='paper',
        text="Today",
        showarrow=False,
        font=dict(color="red"),
        bgcolor="white"
    )

    fig.update_layout(
        height=600,
        xaxis=dict(
            tickvals=weeks,
            ticktext=[w.strftime('%b %d') for w in weeks],
            tickangle=-45
        ),
        hoverlabel=dict(
            bgcolor="Black",
            font_size=12
        ),
        margin=dict(b=100)
    )

    # Display the plot
    st.plotly_chart(fig, use_container_width=True)  
    
# python -m streamlit run app.py