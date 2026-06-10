import os
import httpx
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv("/opt/bots/matrix_bot/.env")

PROXY_URL = os.getenv("PROXY_URL")

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    http_client=httpx.Client(
        proxy=PROXY_URL,
        timeout=180.0
    )
)


def interpret_personal_matrix(matrix: dict):
    from matrix.prompts import build_personal_matrix_prompt

    prompt = build_personal_matrix_prompt(matrix)

    response = client.responses.create(
        model="gpt-5.4",
        input=prompt
    )

    return response.output_text
