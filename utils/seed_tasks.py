from pymongo import MongoClient
import certifi

# MongoDB connection
uri = "mongodb+srv://amruthjakku:jS7fK5f2QwMZANut@cluster0.hc4q6ax.mongodb.net/progress_tracker?retryWrites=true&w=majority"

# Example tasks
TASKS = [
    {
        "title": "Create GitLab Account",
        "description": "Register and set up profile at code.swecha.org",
        "resources": [
            {"title": "GitLab", "url": "https://code.swecha.org"}
        ],
        "assigned_to": "intern@example.com"
    },
    {
        "title": "Setup Tech Stack",
        "description": "Install all tools as per onboarding doc",
        "resources": [
            {"title": "Onboarding Doc", "url": "https://code.swecha.org/soai2025/onboarding/-/blob/main/InitialDeveloperSetup.md"}
        ],
        "assigned_to": "intern@example.com"
    },
    {
        "title": "LMS Access – Python Advanced",
        "description": "Login to courses.viswam.ai and start the Python course",
        "resources": [
            {"title": "Python Advanced Course", "url": "https://courses.viswam.ai/course/python_advanced/"}
        ],
        "assigned_to": "intern@example.com"
    },
    {
        "title": "LMS Access – Intro to AI",
        "description": "Login and access the AI Introduction course",
        "resources": [
            {"title": "AI Introduction Course", "url": "https://courses.viswam.ai/course/ai/introduction"}
        ],
        "assigned_to": "intern@example.com"
    },
    {
        "title": "Submit Issues to Platform Repo",
        "description": "File issues in the bug tracker repo on GitLab",
        "resources": [
            {"title": "Platform Repo", "url": "https://code.swecha.org/soai2025/techleads/soai-platforms"}
        ],
        "assigned_to": "intern@example.com"
    }
]

def seed_tasks():
    try:
        # Connect to MongoDB
        client = MongoClient(uri, tlsCAFile=certifi.where())
        db = client.progress_tracker
        
        print("Connected to MongoDB successfully!")

        # Clear existing demo tasks
        result = db.tasks.delete_many({"assigned_to": "intern@example.com"})
        print(f"Cleared {result.deleted_count} existing demo tasks")
        
        # Insert new tasks
        result = db.tasks.insert_many(TASKS)
        print(f"Successfully inserted {len(result.inserted_ids)} tasks!")
        
        # Verify tasks were inserted
        count = db.tasks.count_documents({"assigned_to": "intern@example.com"})
        print(f"Total tasks for intern@example.com: {count}")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        raise e

if __name__ == "__main__":
    seed_tasks()
