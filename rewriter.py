import aiohttp
from config import MAIN_API_KEY, MAIN_BASE_URL, MAIN_MODEL
from http_client import create_session

REWRITE_PROMPT = """You are a query optimization assistant for document retrieval.

Original question: {question}

Rewrite this question to improve retrieval accuracy:
1. Clarify vague expressions
2. Add synonyms that may appear in documents
3. Preserve the original intent

Return only the rewritten question text, nothing else."""


async def rewrite_query(question):
    """Rewrite user question to improve retrieval recall"""
    prompt = REWRITE_PROMPT.format(question=question)

    payload = {
        "model": MAIN_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0
    }
    headers = {
        "Authorization": f"Bearer {MAIN_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        async with create_session() as session:
            async with session.post(
                f"{MAIN_BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                data = await resp.json()
                if 'error' in data:
                    print(f"  [ERR] Query rewrite failed: {data['error']}")
                    return question
                rewritten = data['choices'][0]['message']['content'].strip()
                return rewritten
    except Exception as e:
        print(f"  [ERR] Query rewrite failed: {e}")
        return question
