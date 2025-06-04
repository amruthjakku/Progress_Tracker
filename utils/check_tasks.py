from pymongo import MongoClient
import certifi

uri = "mongodb+srv://amruthjakku:jS7fK5f2QwMZANut@cluster0.hc4q6ax.mongodb.net/progress_tracker?retryWrites=true&w=majority"
client = MongoClient(uri, tlsCAFile=certifi.where())
db = client.progress_tracker

# Check tasks
tasks = list(db.tasks.find({"assigned_to": "intern@example.com"}))
print(f"\nFound {len(tasks)} tasks:")
for task in tasks:
    print(f"- {task['title']}")
