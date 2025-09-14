import configparser

from langchain_google_genai import ChatGoogleGenerativeAI
config = configparser.ConfigParser()
config.read('config.properties')

def get_llm_model(model_name: str):
    api_key = config['APIKEYs']['gemini_api']
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0.3,
        google_api_key=api_key,
        convert_system_message_to_human=True
    )
    return llm