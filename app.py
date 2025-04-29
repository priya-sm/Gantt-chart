import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Set page config
st.set_page_config(layout="wide")
st.title("📊 Consultant Effort Gantt Chart Generator")

# Upload Excel
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx", "xls"])

if uploaded_file:
    dataset = pd.read_excel(uploaded_file)

    # Rename columns
    df = dataset.copy()
    df = df.drop_duplicates()
    df.rename(columns={
        "ConsultantName": "Name",
        "ProjectName": "Projects",
        "Efforts_Percentage": "Effort",
        "StartDate": "Start",
        "EndDate": "End"
    }, inplace=True)

    # Convert to correct types
    df['Start'] = pd.to_datetime(df['Start'])
    df['End'] = pd.to_datetime(df['End'])
    df['Effort'] = pd.to_numeric(df['Effort'], errors='coerce')
    df = df.dropna(subset=['Start', 'End', 'Effort'])

    # EXPAND into weeks but KEEP real Start and End
    rows = []
    for _, row in df.iterrows():
        start = row['Start']
        end = row['End']
        effort = row['Effort']
        project = row['Projects']
        name = row['Name']

        # Create weekly periods but don't move start to Monday
        current_start = start
        while current_start <= end:
            # Current week's Monday
            week_start = current_start - pd.to_timedelta(current_start.weekday(), unit='d')
            week_end = week_start + pd.Timedelta(days=6)

            # This period's actual start and end
            period_start = max(current_start, week_start)
            period_end = min(end, week_end)

            rows.append({
                "Name": name,
                "Projects": project,
                "week_start": week_start,
                "Start": period_start,
                "End": period_end,
                "Effort": effort
            })

            current_start = week_end + pd.Timedelta(days=1)

    expanded_df = pd.DataFrame(rows)

    # Group and combine project names if multiple
    weekly_sum = (
        expanded_df.groupby(['Name', 'week_start', 'Start', 'End'])
        .agg({
            'Effort': 'sum',
            'Projects': lambda x: ', '.join(sorted(x.unique()))
        })
        .reset_index()
        .rename(columns={'Effort': 'Effort%'})
    )

    expanded_df = weekly_sum.copy()

    # Filters
    start_date = st.date_input("Start Date", expanded_df['Start'].min())
    end_date = st.date_input("End Date", expanded_df['End'].max())

    consultant_names = st.multiselect("Select Consultant(s)", options=expanded_df['Name'].unique(), default=expanded_df['Name'].unique())

    filtered_df = expanded_df[
        (expanded_df['Start'] >= pd.to_datetime(start_date)) &
        (expanded_df['End'] <= pd.to_datetime(end_date)) &
        (expanded_df['Name'].isin(consultant_names))
    ]

    # Plot Gantt chart
    fig = px.timeline(
        filtered_df,
        x_start="Start",
        x_end="End",
        y="Name",
        color="Projects",
        hover_data={
            "Name": True,
            "Effort%": ':.2f',
            "Projects": True,
            "Start": True,
            "End": True
        },
        title="Gantt Chart: Weekly Effort per Consultant"
    )

    fig.update_yaxes(autorange="reversed")

    # Add vertical week lines
    min_date = filtered_df['Start'].min().normalize()
    max_date = filtered_df['End'].max().normalize()
    week_dates = pd.date_range(start=min_date, end=max_date, freq='W-MON')

    for week in week_dates:
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
        bgcolor="White"
    )

    fig.update_layout(
        height=600,
        xaxis=dict(
            tickformat="%b %d",
            tickangle=-45
        ),
        hoverlabel=dict(
            bgcolor="Black",
            font_size=12
        ),
        margin=dict(b=100)
    )

    st.plotly_chart(fig, use_container_width=True)

    
# python -m streamlit run app.py
