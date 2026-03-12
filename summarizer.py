import sys
import json
import time
import aiohttp
from config import MAIN_API_KEY, MAIN_BASE_URL, MAIN_MODEL
from http_client import create_session

SUMMARY_PROMPT = """You are a professional document analysis assistant.

User question: {question}

The following relevant information was retrieved from multiple documents:

{findings}

Synthesize the above information to answer the user's question. Requirements:
1. Cite the source (filename and location) for every piece of information
2. Contradiction check (mandatory):
   a. For the same fact (dates, amounts, names, etc.), cross-check all sources
   b. If different sources give different values for the same fact, list ALL of them and mark as "CONTRADICTION"
   c. Analyze possible reasons for contradictions
   d. Never omit or merge differing information for narrative smoothness
3. Provide a clear conclusion
4. If information is insufficient, state what is missing"""


def _format_findings(results):
    parts = []
    for i, r in enumerate(results, 1):
        parts.append(f"[Source {i}] {r['file']} ({r['segment']}, {r['line_range']})")
        parts.append(f"Summary: {r.get('findings', 'N/A')}")
        parts.append(f"Quote: {r.get('quotes', 'N/A')}")
        parts.append("")
    return '\n'.join(parts)


async def summarize(results, question, logger=None):
    """Stream summarization of retrieval results"""
    if not results:
        msg = "No relevant content found in any document."
        print(msg)
        if logger:
            logger.log_summary(msg, 0)
        return msg

    findings_text = _format_findings(results)
    prompt = SUMMARY_PROMPT.format(question=question, findings=findings_text)

    payload = {
        "model": MAIN_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "stream": True
    }
    headers = {
        "Authorization": f"Bearer {MAIN_API_KEY}",
        "Content-Type": "application/json"
    }

    full_answer = []
    summary_start = time.time()

    try:
        async with create_session() as session:
            async with session.post(
                f"{MAIN_BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=180)
            ) as resp:
                if resp.status != 200:
                    data = await resp.json()
                    err = f"Summarization error: {data}"
                    print(err)
                    return err

                async for line in resp.content:
                    line = line.decode('utf-8').strip()
                    if not line or not line.startswith('data:'):
                        continue

                    data_str = line[5:].strip()
                    if data_str == '[DONE]':
                        break

                    try:
                        chunk = json.loads(data_str)
                        delta = chunk['choices'][0].get('delta', {})
                        content = delta.get('content', '')
                        if content:
                            sys.stdout.write(content)
                            sys.stdout.flush()
                            full_answer.append(content)
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

        print()

    except Exception as e:
        err = f"Summarization error: {e}"
        print(err)
        return err

    answer = ''.join(full_answer)
    if logger:
        logger.log_summary(answer, time.time() - summary_start)
    return answer
