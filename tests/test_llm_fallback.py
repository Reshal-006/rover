import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_call_gemini_falls_back_to_openrouter_when_gemini_fails(monkeypatch):
    import src.llm as llm

    monkeypatch.setenv('LLM_PROVIDER', 'gemini')
    monkeypatch.setenv('GEMINI_API_KEY', 'dummy-gemini-key')
    monkeypatch.setenv('OPENROUTER_API_KEY', 'dummy-openrouter-key')
    monkeypatch.setenv('OPENROUTER_MODEL', 'qwen/qwen3-coder:free')

    calls = []

    def fake_gemini_api(contents, model, system_prompt, tools):
        calls.append('gemini')
        raise RuntimeError('429 quota exceeded')

    def fake_openrouter_api(contents, model, system_prompt, tools):
        calls.append('openrouter')
        return llm.NormalizedResponse(text='fallback response', function_calls=[], candidates=[])

    monkeypatch.setattr(llm, '_call_gemini_api', fake_gemini_api)
    monkeypatch.setattr(llm, '_call_openrouter_api', fake_openrouter_api)

    response = llm.call_gemini([])

    assert response.text == 'fallback response'
    assert calls == ['gemini', 'openrouter']
