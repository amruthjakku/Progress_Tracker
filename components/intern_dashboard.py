import streamlit as st
from supabase_client import get_supabase_client

supabase = get_supabase_client()

def render_intern_dashboard(user_id, user_email):
    st.subheader("Your Tasks")
    # Fetch all tasks with progress
    tasks = supabase.table("tasks").select("*", "progress(user_id,status,submission_link)").execute().data or []
    # Only show tasks assigned to this user
    user_tasks = []
    for t in tasks:
        progress_list = t.get('progress', [])
        user_progress = next((p for p in progress_list if p.get('user_id') == user_id), None)
        if user_progress:
            t['user_progress'] = user_progress
            user_tasks.append(t)
    done_count = sum(1 for t in user_tasks if t['user_progress'].get('status') == 'done')
    total = len(user_tasks)
    progress = (done_count / total) * 100 if total else 0
    st.progress(progress / 100, text=f"{done_count}/{total} tasks completed")
    for task in user_tasks:
        st.markdown(f"### {task['title']}")
        st.write(task.get('description', ''))
        st.write("**Resources:**")
        for res in task.get('resources', []) or []:
            st.markdown(f"- [{res['title']}]({res['url']})")
        user_progress = task['user_progress']
        # Mark as done
        if user_progress.get('status') != 'done':
            if st.button(f"Mark '{task['title']}' as Done", key=task['id']):
                # TODO: Update progress in Supabase
                st.success("Marked as done!")
        else:
            st.success("Done!")
        # Submission link
        st.text_input(f"Submission Link for '{task['title']}'", value=user_progress.get('submission_link', ''), key=f"link_{task['id']}")
        st.divider() 