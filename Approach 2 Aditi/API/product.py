import configparser
import uuid
from fastapi import FastAPI,Form
from pydantic import BaseModel, Field
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.messages import SystemMessage, HumanMessage
from API.llm import get_llm_model
from DB.matching_result import getResult
from DB.Database import DatabaseFunctions


def get_conversation_history(session_id):
    db = DatabaseFunctions("chatbot.db")
    rows = db.select_df("conversations")
    # filter by session_id
    history = [row for row in rows if row[5] == session_id]  
    messages = []
    for row in history:
        msg_text = row[3]   # message column
        sender = row[4]     # sender column
        messages.append(SystemMessage(content=msg_text))
    return messages

config = configparser.ConfigParser()
config.read("config.properties")
k = int(config['Embedding']['top_k'])
model=config['ModelName']['gemini']

api = FastAPI()

# Session history
session_history = {}

# Pydantic schema
class Product_mes(BaseModel):
    reply: str = Field(..., description="Information about the product or website")

# Endpoint
@api.post("/Get-Product_info")
async def get_product_features(
    user_query: str=Form(...), 
    session_id: str = Form(None)
    ):
     
    if session_id is None:
        session_id = str(uuid.uuid4())
    
    if session_id not in session_history:
        session_history[session_id] = []
    
    parser = PydanticOutputParser(pydantic_object=Product_mes)
    format_instructions = parser.get_format_instructions()
    
    history_rows = get_conversation_history(session_id)

    # Fetch top-k results from your retriever
    top_matching_result = getResult(user_query, k)  
    print('The top matching Results ',top_matching_result)
    system_message = SystemMessage(
        
    content=f"""You are a smart, friendly, and very helpful AI assistant for Smart Room Search.
Your primary role is to guide users and answer their queries related to the Smart Room Search website.
Always focus only on topics connected to Smart Room Search (such as searching rooms, booking details, pricing, availability, features, or support).
Provide clear, concise, and accurate responses that directly address the user's question.
Maintain a polite, supportive, and friendly tone to make the user feel comfortable.
Do not provide answers unrelated to Smart Room Search.
Do not generate extra or off-topic responses beyond the scope of the website.
Only return the parsed output.
Do not just copy the retrieved content verbatim. Instead, use it to generate a natural assistant-style reply that directly answers the user.

Your goal is to make the user's experience smooth, informative, and helpful while staying strictly within the subject of Smart Room Search.

Here are top {k} matching results you have to use in order to retrieve relevant query. Out of the information given select the most matching and 
relevant information and based on the information generate the message:
{top_matching_result}

{format_instructions}

ALSO FIND THE CONVERSATION HISTORY FOR THIS USER:\n
{history_rows}

"""

)

    human_message = HumanMessage(content=f"User is asking for: {user_query}")
    session_history[session_id].append(HumanMessage(content=user_query))

    
    # Call your LLM
    llm = get_llm_model(model)
    messages = [system_message] + session_history[session_id]
    response = llm.invoke(messages)

    result=parser.parse(response.content)
    session_history[session_id].append(SystemMessage(content=result.reply))
    print('Result',result)
   
    return {"response": result}
