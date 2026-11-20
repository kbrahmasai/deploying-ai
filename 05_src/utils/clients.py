from openai import OpenAI
import os

USE_GATEWAY = (os.getenv('USE_GATEWAY', 'FALSE').upper() == 'TRUE')

def get_client(use_gateway: bool = USE_GATEWAY) -> OpenAI:
    if use_gateway:
        client = OpenAI(
                    api_key=os.getenv('OPENAI_API_KEY'),
                    )
    else:
        client = OpenAI()
    return client