"""Test LLM request module."""

import json
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from llm import load_api_key, build_request, parse_response, call_llm, call_llm_batch


def test_load_api_key():
    api_key_path = os.path.join(os.path.dirname(__file__), '..', 'API_KEYS.txt')
    key = load_api_key(api_key_path)
    assert len(key) > 10
    assert ' ' not in key


def test_load_api_key_invalid_file():
    key = load_api_key('/nonexistent/path.txt')
    assert key == ''


def test_build_request_body():
    body = build_request(
        system_prompt='You are helpful.',
        user_prompt='Hello'
    )
    assert body['model'] == 'deepseek-v4-flash'
    assert len(body['messages']) == 2
    assert body['messages'][0]['role'] == 'system'
    assert body['messages'][0]['content'] == 'You are helpful.'
    assert body['messages'][1]['role'] == 'user'
    assert body['messages'][1]['content'] == 'Hello'
    assert body['reasoning_effort'] == 'high'
    assert body['thinking'] == {'type': 'enabled'}


def test_parse_response_success():
    mock_response = {
        'choices': [{
            'finish_reason': 'stop',
            'message': {
                'content': '{"topics": ["Tech/AI"]}',
                'role': 'assistant'
            }
        }],
        'usage': {'total_tokens': 100}
    }
    content, usage = parse_response(mock_response)
    assert content == '{"topics": ["Tech/AI"]}'
    assert usage['total_tokens'] == 100


def test_parse_response_empty():
    result = parse_response({})
    assert result == ('', {})


def test_parse_response_no_choices():
    result = parse_response({'usage': {}})
    assert result == ('', {})


def test_call_llm_mocked():
    """Test call_llm with mocked HTTP response."""
    mock_response_data = json.dumps({
        'choices': [{
            'finish_reason': 'stop',
            'message': {
                'content': '{"topics": ["Tech/AI"]}',
                'role': 'assistant'
            }
        }],
        'usage': {'total_tokens': 50}
    }).encode('utf-8')

    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_response_data
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        content, usage = call_llm(
            api_key='test-key',
            system_prompt='test system',
            user_prompt='test user'
        )

        assert content == '{"topics": ["Tech/AI"]}'
        assert usage['total_tokens'] == 50

        # Verify the request was built correctly
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        assert req.headers['Authorization'] == 'Bearer test-key'
        assert req.headers['Content-type'] == 'application/json'


def test_call_llm_json_parse_error():
    """Test that non-JSON content in LLM response is returned as-is."""
    mock_response_data = json.dumps({
        'choices': [{
            'finish_reason': 'stop',
            'message': {
                'content': 'just plain text, not json',
                'role': 'assistant'
            }
        }],
        'usage': {'total_tokens': 30}
    }).encode('utf-8')

    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_response_data
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        content, usage = call_llm(
            api_key='test-key',
            system_prompt='test',
            user_prompt='test'
        )
        assert content == 'just plain text, not json'
        assert usage['total_tokens'] == 30


def test_call_llm_batch_mocked():
    """Test batch LLM call with mocked HTTP response."""
    batch_response = json.dumps({
        'results': [
            {'index': 0, 'topics': ['Tech/AI']},
            {'index': 1, 'topics': []},
            {'index': 2, 'topics': ['Finance/Markets']},
        ]
    })

    mock_response_data = json.dumps({
        'choices': [{
            'finish_reason': 'stop',
            'message': {
                'content': batch_response,
                'role': 'assistant'
            }
        }],
        'usage': {'total_tokens': 100}
    }).encode('utf-8')

    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_response_data
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        results, usage = call_llm_batch(
            api_key='test-key',
            system_prompt='test system',
            user_prompt='test batch prompt'
        )

        assert len(results) == 3
        assert results[0] == {'index': 0, 'topics': ['Tech/AI']}
        assert results[1] == {'index': 1, 'topics': []}
        assert usage['total_tokens'] == 100


def test_call_llm_batch_parse_failure():
    """Test that batch call handles invalid JSON gracefully."""
    mock_response_data = json.dumps({
        'choices': [{
            'finish_reason': 'stop',
            'message': {
                'content': 'not json at all {{',
                'role': 'assistant'
            }
        }],
        'usage': {'total_tokens': 10}
    }).encode('utf-8')

    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_response_data
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        results, usage = call_llm_batch(
            api_key='test-key',
            system_prompt='test',
            user_prompt='test'
        )
        assert results == []
        assert usage['total_tokens'] == 10
