import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Insert a test event
test_event = {
    "title": "Test Pub Quiz",
    "organizer": "Tierney's Irish Pub",
    "date": "2025-07-10",
    "start_time": "20:00",
    "category": "pub_quiz",
    "language": "english",
    "source_platform": "manual"
}

result = supabase.table("events").insert(test_event).execute()
print("Inserted:", result.data)

# Read it back
events = supabase.table("events").select("*").execute()
print("All events:", events.data)

# Clean up — delete the test row
if result.data:
    event_id = result.data[0]["id"]
    supabase.table("events").delete().eq("id", event_id).execute()
    print("Cleaned up test event")