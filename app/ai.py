import os
import httpx
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv("/opt/bots/matrix_bot/.env")

PROXY_URL = os.getenv("PROXY_URL")

http_client = httpx.AsyncClient(
    proxy=PROXY_URL,
    timeout=180.0
)

client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    http_client=http_client
)


async def interpret_personal_matrix(matrix: dict):
    from matrix.prompts import build_personal_matrix_prompt

    prompt = build_personal_matrix_prompt(matrix)

    response = await client.responses.create(
        model="gpt-5.4-mini",
        input=prompt
    )

    return response.output_text


async def interpret_compatibility(data: dict):
    from matrix.prompts import build_compatibility_prompt

    prompt = build_compatibility_prompt(data)

    response = await client.responses.create(
        model="gpt-5.4-mini",
        input=prompt
    )

    return response.output_text


async def interpret_money_channel(matrix: dict):
    from matrix.prompts import build_money_channel_prompt

    prompt = build_money_channel_prompt(matrix)

    response = await client.responses.create(
        model="gpt-5.4-mini",
        input=prompt
    )

    return response.output_text


async def interpret_purpose(matrix: dict):
    from matrix.prompts import build_purpose_prompt

    prompt = build_purpose_prompt(matrix)

    response = await client.responses.create(
        model="gpt-5.4-mini",
        input=prompt
    )

    return response.output_text


async def interpret_karma(matrix: dict):
    from matrix.prompts import build_karma_prompt

    prompt = build_karma_prompt(matrix)

    response = await client.responses.create(
        model="gpt-5.4-mini",
        input=prompt
    )

    return response.output_text


async def interpret_child_matrix(matrix: dict):
    from matrix.prompts import build_child_matrix_prompt

    prompt = build_child_matrix_prompt(matrix)

    response = await client.responses.create(
        model="gpt-5.4-mini",
        input=prompt
    )

    return response.output_text
