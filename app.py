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

    # Rename and clean columns
    df = dataset.copy()
    df = df.drop_duplicates()
    df.rename(columns={
        "ConsultantName": "Name",
        "ProjectName": "Projects",
        "Efforts_Percentage": "Effort",
        "StartDate": "Start",
        "EndDate": "End"
    }, inplace=True)

    def extract_skills(row):
        core = str(row["CoreSkill"]).split(",") if pd.notnull(row["CoreSkill"]) else []
        other = str(row["OtherSkills"]).split(",") if pd.notnull(row["OtherSkills"]) else []
        return [skill.strip() for skill in core + other if skill.strip()]

    df["Skill_List"] = df.apply(extract_skills, axis=1)
    df = df.explode("Skill_List").rename(columns={"Skill_List": "Skill"})

    # Convert to correct types
    df['Start'] = pd.to_datetime(df['Start'])
    df['End'] = pd.to_datetime(df['End'])
    df['Effort'] = pd.to_numeric(df['Effort'], errors='coerce')
    df = df.dropna(subset=['Start', 'End', 'Effort'])

    # Expand into weeks
    rows = []
    for _, row in df.iterrows():
        start = row['Start']
        end = row['End']
        effort = row['Effort']
        project = row['Projects']
        name = row['Name']
        skill = row['Skill']

        current_start = start
        while current_start <= end:
            week_start = current_start - pd.to_timedelta(current_start.weekday(), unit='d')
            week_end = week_start + pd.Timedelta(days=6)

            period_start = max(current_start, week_start)
            period_end = min(end, week_end)

            rows.append({
                "Name": name,
                "Projects": project,
                "week_start": week_start,
                "Start": period_start,
                "End": period_end,
                "Effort": effort,
                "Skill": skill
            })

            current_start = week_end + pd.Timedelta(days=1)

    expanded_df = pd.DataFrame(rows)

    # Group and summarize
    weekly_sum = (
        expanded_df.groupby(['Name', 'week_start', 'Start', 'End', 'Skill'])
        .agg({
            'Effort': 'sum',
            'Projects': lambda x: ', '.join(sorted(x.unique()))
        })
        .reset_index()
        .rename(columns={'Effort': 'Effort%'})
    )

    expanded_df = weekly_sum.copy()

    # Sidebar Filters
    st.sidebar.header("Filters")

    start_date = st.sidebar.date_input("Start Date", expanded_df['Start'].min())
    end_date = st.sidebar.date_input("End Date", expanded_df['End'].max())

#-Consultant name-------------------------------------------------------------------
# Sidebar: Consultant Filter with conditional multiselect
    consultant_list = sorted(expanded_df['Name'].unique())
    select_all = st.sidebar.checkbox("Select All Consultants", value=True)

    if select_all:
        consultant_names = consultant_list  # Use all consultants
    else:
        consultant_names = st.sidebar.multiselect(
            "Select Consultant(s)",
            options=consultant_list,
            default=consultant_list  # Default to select all consultants
        )
    if not consultant_names:
        st.warning("Please select at least one consultant.")

#-SKILL-------------------------------------------------------------------
# Sidebar: Skill Filter with conditional multiselect
    skills = sorted(expanded_df['Skill'].dropna().unique())
    select_all_skills = st.sidebar.checkbox("Select All Skills", value=True)

# Always show the multiselect for skills
    if select_all_skills:
        selected_skills = skills
    else:
        selected_skills = st.sidebar.multiselect(
            "Select Skill(s)",
            options=skills,
            default=skills  # No default selection if "Select All" is unchecked
        )

# Check if no skills are selected
    if not selected_skills:
        st.warning("Please select at least one skill.")
#--------------------------------------------------------------------


    # Apply filters
    filtered_df = expanded_df[
        (expanded_df['Start'] >= pd.to_datetime(start_date)) &
        (expanded_df['End'] <= pd.to_datetime(end_date)) &
        (expanded_df['Name'].isin(consultant_names)) &
        (expanded_df['Skill'].isin(selected_skills))
    ]

    # Plot Gantt Chart
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
            "End": True,
            "Skill": False
        },
        title="Gantt Chart: Weekly Effort per Consultant"
    )

    fig.update_yaxes(autorange="reversed")

    # Weekly grid lines
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

    # Today line
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


#run locally    
# python -m streamlit run app.py
