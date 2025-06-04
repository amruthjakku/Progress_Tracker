from pymongo import MongoClient
import certifi

uri = "mongodb+srv://amruthjakku:jS7fK5f2QwMZANut@cluster0.hc4q6ax.mongodb.net/progress_tracker?retryWrites=true&w=majority"

try:
    # Create a new client and connect to the server
    client = MongoClient(uri, tlsCAFile=certifi.where())
    
    # Send a ping to confirm a successful connection
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")
    
    # Try to insert a test document
    db = client.progress_tracker
    result = db.test.insert_one({"test": "connection"})
    print("Successfully inserted test document!")
    
    # Clean up test document
    db.test.delete_one({"test": "connection"})
    print("Test document cleaned up!")
    
except Exception as e:
    print(f"Connection error: {e}")
