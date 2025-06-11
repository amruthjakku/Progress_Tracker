import streamlit as st
import pandas as pd
import plotly.express as px
from models.database import DatabaseManager

def render_college_management():
    """Render the college management tab for mentors"""
    db_manager = DatabaseManager()
    
    st.header("🏫 College Management")
    
    # Create tabs for different college management sections
    college_tab1, college_tab2, college_tab3 = st.tabs(["📊 Leaderboard", "➕ Add College", "📁 Import"])
    
    with college_tab1:
        st.subheader("College Leaderboard")
        
        # Get college leaderboard data
        college_leaderboard = db_manager.get_college_leaderboard()
        
        if college_leaderboard:
            # Convert to DataFrame for display
            college_df = pd.DataFrame([
                {
                    "College": college["name"],
                    "Interns": college["interns_count"],
                    "Avg. Completion %": round(college["avg_completion"], 1)
                }
                for college in college_leaderboard
            ])
            
            # Show top 3 colleges with medals
            if len(college_df) >= 3:
                st.subheader("🏆 Top Performing Colleges")
                col1, col2, col3 = st.columns(3)
                
                with col2:  # First place (center)
                    st.markdown(f"### 🥇 First Place")
                    st.markdown(f"**{college_df.iloc[0]['College']}**")
                    st.markdown(f"Avg. Completion: **{college_df.iloc[0]['Avg. Completion %']}%**")
                    st.markdown(f"Interns: **{college_df.iloc[0]['Interns']}**")
                
                with col1:  # Second place (left)
                    st.markdown(f"### 🥈 Second Place")
                    st.markdown(f"**{college_df.iloc[1]['College']}**")
                    st.markdown(f"Avg. Completion: **{college_df.iloc[1]['Avg. Completion %']}%**")
                    st.markdown(f"Interns: **{college_df.iloc[1]['Interns']}**")
                
                with col3:  # Third place (right)
                    st.markdown(f"### 🥉 Third Place")
                    st.markdown(f"**{college_df.iloc[2]['College']}**")
                    st.markdown(f"Avg. Completion: **{college_df.iloc[2]['Avg. Completion %']}%**")
                    st.markdown(f"Interns: **{college_df.iloc[2]['Interns']}**")
            
            # Show full college leaderboard
            st.subheader("All Colleges")
            st.dataframe(
                college_df,
                hide_index=True,
                use_container_width=True
            )
            
            # Visualize college performance
            st.subheader("College Performance Comparison")
            fig = px.bar(
                college_df,
                x="College",
                y="Avg. Completion %",
                color="Avg. Completion %",
                color_continuous_scale=["#EF553B", "#636EFA", "#00CC96"],
                text="Interns",
                title="Average Completion Percentage by College"
            )
            fig.update_layout(xaxis_title="College", yaxis_title="Average Completion %")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No colleges found. Add colleges using the 'Add College' tab.")
    
    with college_tab2:
        st.subheader("Add New College")
        
        with st.form("add_college_form"):
            college_name = st.text_input("College Name", placeholder="Enter college name")
            college_description = st.text_area("Description (Optional)", placeholder="Enter college description")
            
            submitted = st.form_submit_button("Add College")
            
            if submitted:
                if college_name:
                    result = db_manager.add_college(
                        name=college_name,
                        description=college_description
                    )
                    
                    if result:
                        st.success(f"College '{college_name}' added successfully!")
                    else:
                        st.error("Error adding college. It may already exist.")
                else:
                    st.error("Please provide a college name.")
    
    with college_tab3:
        st.subheader("Import Colleges")
        
        # College import section
        st.write("#### Import Colleges from CSV")
        st.write("Upload a CSV file with college information.")
        
        # Sample CSV template
        st.write("##### CSV Format")
        sample_data = pd.DataFrame([
            {"name": "Example College 1", "description": "Description for college 1"},
            {"name": "Example College 2", "description": "Description for college 2"}
        ])
        st.dataframe(sample_data)
        
        # Download sample template
        csv = sample_data.to_csv(index=False)
        st.download_button(
            label="📥 Download Sample Template",
            data=csv,
            file_name="college_template.csv",
            mime="text/csv"
        )
        
        # Upload CSV
        uploaded_file = st.file_uploader("Upload Colleges CSV", type=["csv"])
        
        if uploaded_file is not None:
            if st.button("Import Colleges"):
                result = db_manager.import_colleges_from_csv(uploaded_file)
                
                if result["success"] > 0:
                    st.success(result["message"])
                else:
                    st.error(result["message"])
        
        # Intern import section
        st.write("---")
        st.write("#### Import Interns from CSV")
        st.write("Upload a CSV file with intern information including college assignment.")
        
        # Sample CSV template for interns
        st.write("##### CSV Format")
        sample_intern_data = pd.DataFrame([
            {"email": "intern1@example.com", "name": "Intern One", "college": "Example College 1", "skills": "Python,SQL,HTML"},
            {"email": "intern2@example.com", "name": "Intern Two", "college": "Example College 2", "skills": "JavaScript,React"}
        ])
        st.dataframe(sample_intern_data)
        
        # Download sample template
        intern_csv = sample_intern_data.to_csv(index=False)
        st.download_button(
            label="📥 Download Sample Template",
            data=intern_csv,
            file_name="intern_template.csv",
            mime="text/csv",
            key="download_intern_template"
        )
        
        # Upload CSV
        uploaded_intern_file = st.file_uploader("Upload Interns CSV", type=["csv"], key="intern_upload")
        
        if uploaded_intern_file is not None:
            if st.button("Import Interns"):
                result = db_manager.import_interns_from_csv(uploaded_intern_file)
                
                if result["success"] > 0:
                    st.success(result["message"])
                else:
                    st.error(result["message"])