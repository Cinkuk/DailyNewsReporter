"""LLM request module for DeepSeek API (deepseek-v4-flash, 1M context)."""

import json
import urllib.request
import urllib.error

DEEPSEEK_API_URL = 'https://api.deepseek.com/chat/completions'
MODEL = 'deepseek-v4-flash'
BATCH_SIZE = 30


def load_api_key(filepath: str) -> str:
    """Load DEEPSEEK_API_KEY from API_KEYS.txt. Format: DEEPSEEK_API_KEY=<key>"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('DEEPSEEK_API_KEY='):
                    return line.split('=', 1)[1].strip()
                elif line.startswith('ARK_API_KEY='):
                    return line.split('=', 1)[1].strip()
    except FileNotFoundError:
        pass
    return ''


def build_request(system_prompt: str, user_prompt: str) -> dict:
    """Build request body for DeepSeek API chat completion."""
    return {
        'model': MODEL,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ],
        'stream': False,
        'reasoning_effort': 'high',
        'thinking': {'type': 'enabled'},
    }


def parse_response(response_data: dict) -> tuple[str, dict]:
    """Extract content and usage from API response. Returns (content, usage_dict)."""
    choices = response_data.get('choices', [])
    if not choices:
        return '', {}
    content = choices[0]['message']['content']
    usage = response_data.get('usage', {})
    return content, usage


def call_llm(api_key: str, system_prompt: str, user_prompt: str) -> tuple[str, dict]:
    """Send chat completion request to DeepSeek API. Returns (content, usage)."""
    body = build_request(system_prompt, user_prompt)
    data = json.dumps(body).encode('utf-8')

    req = urllib.request.Request(DEEPSEEK_API_URL, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', f'Bearer {api_key}')

    try:
        with urllib.request.urlopen(req) as resp:
            response_data = json.loads(resp.read().decode('utf-8'))
            return parse_response(response_data)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'LLM API error {e.code}: {error_body}') from e
    except urllib.error.URLError as e:
        raise RuntimeError(f'LLM API connection error: {e.reason}') from e


def call_llm_batch(api_key: str, system_prompt: str, user_prompt: str) -> tuple[list[dict], dict]:
    """Send batch classification request. Returns (results_list, usage_dict).

    Expected response format: {"results": [{"index": N, "topics": [...]}, ...]}
    On parse failure, returns ([], usage).
    """
    content, usage = call_llm(api_key, system_prompt, user_prompt)
    try:
        parsed = json.loads(content)
        results = parsed.get('results', [])
        return results, usage
    except (json.JSONDecodeError, TypeError):
        return [], usage
