from pyrogram import Client

API_ID = 38777418
API_HASH = "51c587bfe043c480e7456eb661945034"


with Client(
    "news_session_export",
    api_id=API_ID,
    api_hash=API_HASH,
    in_memory=True,
) as app:
    print("SESSION_STRING:\n")
    print(app.export_session_string())
