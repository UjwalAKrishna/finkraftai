import configparser
import ast
from fastapi import FastAPI, HTTPException, Form
from pydantic import BaseModel, Field
import json
import requests
import uuid
from create_ticket import create_ticket_db 
from datetime import datetime
from DB.Database import DatabaseFunctions

# Load config
config = configparser.ConfigParser()
config.read("config.properties")

api = FastAPI()
lang = config["Language"]["lang"]
info_url = config['APIENDPOINT']['get_info_api']
product_url = config['APIENDPOINT']['product_info']
db_path = config["DatabaseSection"]["database"]
users = config["DatabaseSection"]["user_map"]

# Track ongoing flows
pending_actions = {}   # {user_id: {"action": "Raise_tickets", "short_description": "..."}}
active_sessions = {}   # {conversation_id: {...}}
product_actions = {}   # {user_id: {"action": "PRODUCT_INFORMATION"}}


def save_message(db, user_id, role, message, sender, session_id, workspace_id="default"):
    """Save a message to conversations table"""
    data = {
        "user_id": str(user_id),
        "role": role,
        "message": str(message),   # always save as string
        "sender": sender,
        "session_id": session_id,
        "workspace_id": workspace_id
        # no need for timestamp, DB default will handle it
    }
    db.insert_df("conversations", data)


@api.post("/login")
async def login(user_id: int = Form(...), password: str = Form(...)):
    db = DatabaseFunctions(db_path)
    user_map = db.select_df(users)
    print("user_map", user_map)

    for u in user_map:
        db_user_id, db_password, db_role = u
        if int(db_user_id) == int(user_id) and db_password == password:
            token = str(uuid.uuid4())
            active_sessions[token] = {
                "user_id": db_user_id,
                "role": db_role,
                "password": db_password
            }
            result = {
                "status": "success",
                "conversation_id": token,
                "role": db_role
            }
            print("Login result:", result)
            return result

    raise HTTPException(status_code=401, detail="Invalid credentials")


@api.post("/chat")
async def chat(conversation_id: str = Form(...), user_message: str = Form(...)):
    if conversation_id not in active_sessions:
        raise HTTPException(status_code=401, detail="Invalid or expired session ID")

    session = active_sessions[conversation_id]
    user_id = session["user_id"]
    role = session["role"]
    password = session["password"]

    db = DatabaseFunctions(db_path)

    # Save user message
    save_message(db, user_id, role, user_message, "user", conversation_id)

    # Handle pending actions (ticket follow-up)
    if user_id in pending_actions:
        action = pending_actions[user_id]["action"]
        short_description = pending_actions[user_id]["short_description"]

        if action == "Raise_tickets":
            ticket_description = user_message
            ticket_id = f"TKT-{user_id}-{uuid.uuid4().hex[:6].upper()}"

            re = {
                "role": role,
                "action_result": action,
                "routed_response": {
                    "status": "success",
                    "user_id": user_id,
                    "ticket_id": ticket_id,
                    "description": ticket_description,
                    "short_description": short_description,
                    "ticket_creation_time": datetime.utcnow().isoformat()
                }
            }
            create_ticket_db(re)

            bot_reply = f"Your ticket {ticket_id} has been raised successfully.An agent will get back to you!"
            save_message(db, user_id, role, bot_reply, "assistant", conversation_id)

            # clear pending action
            del pending_actions[user_id]

            return {"message": bot_reply}

    # Otherwise call classifier
    payload = {"user_id": user_id, "password": password, "user_query": user_message}
    response = requests.post(info_url, data=payload)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    response_json = response.json()
    action = response_json.get("action_result")

    if not action:
        bot_reply = "Sorry, I couldn't understand your request."
        save_message(db, user_id, role, bot_reply, "assistant", conversation_id)
        return {"message": bot_reply}

    # Handle actions
    if action == "Raise_tickets":
        pending_actions[user_id] = {"action": "Raise_tickets", "short_description": user_message}
        bot_reply = "Sure, please provide a detailed description of the issue."
        save_message(db, user_id, role, bot_reply, "assistant", conversation_id)
        return {"message": bot_reply}

    elif action.upper() in ["PRODUCT_INFORMATION", "WEBSITE_FEATURES_INFORMATION"]:
        payload = {"user_query": user_message, "session_id": conversation_id}
        product_actions[user_id] = {"action": "PRODUCT_INFORMATION"}

        response = requests.post(product_url, data=payload)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        response_json = response.json()
    # Safely extract the reply text
        if "response" in response_json and isinstance(response_json["response"], dict):
            bot_reply = response_json["response"].get("reply", str(response_json))
        elif "Result" in response_json:
            bot_reply = response_json["Result"]
        else:
            bot_reply = str(response_json)

        save_message(db, user_id, role, bot_reply, "assistant", conversation_id)
        return {"message": bot_reply} 

    else:
        payload = {"user_query": user_message, "session_id": conversation_id}
        product_actions[user_id] = {"action": "PRODUCT_INFORMATION"}
        response = requests.post(product_url, data=payload) 
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        response_json = response.json()
        bot_reply = response_json.get("Result") if isinstance(response_json, dict) else str(response_json)
        
        save_message(db, user_id, role, bot_reply, "assistant", conversation_id)
        return {"message": bot_reply}
