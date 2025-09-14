from datetime import datetime
import configparser
import sys, os
from DB.Database import DatabaseFunctions

config = configparser.ConfigParser()
config.read("config.properties")
db_path = config["DatabaseSection"]["database"]


def create_ticket_db(ticket_info: dict=None):
    #print("ticket info", ticket_info)

    # Step 1: Initialize DB connection
    db = DatabaseFunctions(db_path)

    # Step 2: Prepare insert data
    if ticket_info is not None:
        routed = ticket_info["routed_response"]
        data = {
        "ticket_id": routed["ticket_id"],
        "user_id": routed["user_id"],
        "short_description": routed.get("short_description", ""),
        "description": routed.get("description", ""),
        "creation_time": routed["ticket_creation_time"] }

         # Step 3: Insert into tickets table
        db.insert_df("tickets", data)

 

    #print(f'"status": "success", "ticket_id": {routed["ticket_id"]}')
    return {"status": "success", "ticket_id": routed["ticket_id"]}

db = DatabaseFunctions(db_path)
df=db.select_df('conversations')
print(df)