#!/bin/bash

# Set environment variables to bypass Streamlit onboarding
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
export STREAMLIT_SERVER_HEADLESS=false
export STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false
export STREAMLIT_SERVER_ENABLE_CORS=false

# Run the Streamlit app
echo -e "\n=================================================="
echo "STREAMLIT APP RUNNING AT: http://localhost:8501"
echo -e "==================================================\n"

python3 -m streamlit run app.py