import asyncio
import json
import time
from datetime import datetime
import aiohttp
from config import (
    RETRIEVAL_API_KEY,
    RETRIEVAL_BASE_URL,
    RETRIEVAL_MODEL,
    RETRIEVAL_API_STYLE,
    RETRIEVAL_EXTRA_BODY,
)
from http_client import create_session

RETRIEVE_PROMPT = """You are a document retrieval assistant.

User question: {question}

Document content:
Filename: {file} ({segment}, {line_range})

---
{content}
---

Determine if this document contains information relevant to the user's question.

If relevant, return JSON:
{{"relevant": true, "findings": "Brief summary of relevant content (max 100 chars)", "quotes": "Key quote from the original text (max 80 chars)"}}

If not relevant, return JSON:
{{"relevant": false}}

Return ONLY the JSON, nothing else."""


def _now():
    return datetime.now().strftime('%H:%M:%S.%f')[:-3]


class RetrieveTracker:
    """Track concurrent retrieval progress"""

    def __init__(self, total, logger=None):
        self.total = total
        self.done = 0
        self.relevant_count = 0
        self.start_time = time.time()
        self.logger = logger

    def report(self, segment, result, request_elapsed, timing=None, error=None):
        self.done += 1
        batch_elapsed = time.time() - self.start_time
        name = f"{segment['file']} ({segment['segment']})"

        if result and result.get('relevant'):
            self.relevant_count += 1
            print(f"  [HIT] [{self.done}/{self.total}] {name} -> relevant  ({batch_elapsed:.1f}s)")
        elif result:
            print(f"  [---] [{self.done}/{self.total}] {name} -> not relevant  ({batch_elapsed:.1f}s)")
        else:
            err_msg = f": {error}" if error else ""
            print(f"  [ERR] [{self.done}/{self.total}] {name} -> failed{err_msg}  ({batch_elapsed:.1f}s)")

        if self.logger:
            self.logger.log_retrieve_result(segment, result, request_elapsed, batch_elapsed, error, timing)


async def retrieve_one(session, segment, question, tracker):
    """Retrieve from a single segment"""
    request_start = time.time()
    prompt = RETRIEVE_PROMPT.format(
        question=question,
        file=segment['file'],
        segment=segment['segment'],
        line_range=segment['line_range'],
        content=segment['content']
    )

    payload = _build_payload(prompt)
    if RETRIEVAL_EXTRA_BODY:
        payload.update(RETRIEVAL_EXTRA_BODY)

    headers = {
        "Authorization": f"Bearer {RETRIEVAL_API_KEY}",
        "Content-Type": "application/json"
    }

    result = None
    error = None
    timing = {
        'send_time': _now(),
        'first_byte_time': None,
        'complete_time': None,
    }

    try:
        async with session.post(
            _request_url(),
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=120)
        ) as resp:
            timing['first_byte_time'] = _now()

            data = await resp.json()
            timing['complete_time'] = _now()

            if 'error' in data:
                error = str(data['error'])
                tracker.report(segment, None, time.time() - request_start, timing, error)
                return None

            text = _extract_text(data).strip()
            text = text.replace('```json', '').replace('```', '').strip()
            result = json.loads(text)
            result['file'] = segment['file']
            result['segment'] = segment['segment']
            result['line_range'] = segment['line_range']

    except json.JSONDecodeError as e:
        timing['complete_time'] = _now()
        error = f"JSON parse error: {text[:200] if 'text' in locals() else str(e)}"
    except Exception as e:
        timing['complete_time'] = _now()
        error = str(e)

    tracker.report(segment, result, time.time() - request_start, timing, error)
    return result


def _request_url():
    _, request_url = _resolved_style_and_url()
    return request_url


def _build_payload(prompt):
    style, _ = _resolved_style_and_url()
    if style == "responses":
        return {
            "model": RETRIEVAL_MODEL,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt,
                        }
                    ],
                }
            ],
        }

    return {
        "model": RETRIEVAL_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }


def _extract_text(data):
    style, _ = _resolved_style_and_url()
    if style != "responses":
        return data['choices'][0]['message']['content']

    if isinstance(data.get('output_text'), str) and data['output_text']:
        return data['output_text']

    parts = []
    for item in data.get('output', []):
        for content in item.get('content', []):
            text = content.get('text')
            if isinstance(text, str):
                parts.append(text)
            elif isinstance(text, dict) and isinstance(text.get('value'), str):
                parts.append(text['value'])

    if parts:
        return ''.join(parts)

    raise KeyError("No text content found in responses payload")


def _resolved_style_and_url():
    base_url = RETRIEVAL_BASE_URL.rstrip("/")
    style = RETRIEVAL_API_STYLE

    if style == "auto":
        if base_url.endswith("/responses"):
            return "responses", base_url
        if base_url.endswith("/chat/completions"):
            return "chat_completions", base_url
        return "chat_completions", f"{base_url}/chat/completions"

    if style == "responses":
        if base_url.endswith("/responses"):
            return style, base_url
        return style, f"{base_url}/responses"

    if base_url.endswith("/chat/completions"):
        return "chat_completions", base_url
    return "chat_completions", f"{base_url}/chat/completions"


async def retrieve_all(segments, question, logger=None):
    """Concurrently retrieve from all segments"""
    total = len(segments)
    tracker = RetrieveTracker(total, logger)

    print(f"\n[SEARCH] Retrieving from {total} segments... ({_now()})\n")
    if logger:
        logger.log_question(question, total)

    async with create_session() as session:
        tasks = [retrieve_one(session, seg, question, tracker) for seg in segments]
        results = await asyncio.gather(*tasks)

    relevant = [r for r in results if r and r.get('relevant')]

    elapsed = time.time() - tracker.start_time
    print(f"\n  [DONE] {len(relevant)}/{total} segments relevant, took {elapsed:.1f}s")
    print(f"  [SUM]  Generating answer...\n")
    return relevant
