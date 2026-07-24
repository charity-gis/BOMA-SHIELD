# Migrate AI Backend to Groq

This plan outlines the steps to replace the Google GenAI backend with the ultra-fast Groq API running `llama-3.3-70b-versatile`, as recommended.

## Proposed Changes

### `requirements.txt`
- Add the `openai` package, as Groq provides full compatibility with the OpenAI SDK.

### `src/ai_query.py`
- Remove the `google-genai` imports.
- Initialize the `openai.OpenAI` client with `base_url="https://api.groq.com/openai/v1"` and load the API key from `os.getenv("GROQ_API_KEY")`.
- Update the `generate_sql` function to use `client.chat.completions.create` with `model="llama-3.3-70b-versatile"`. We will format the instructions into a `system` message and the user request into a `user` message.
- Update the `generate_report_answer` function identically, passing the report text context in a `system` message.
- We will retain the exact same function signatures so the frontend does not break.

### `pages/2_AI_Query.py`
- No major changes required since the interface functions (`generate_sql`, `generate_report_answer`) remain the same.

## Verification Plan
1. Install the new dependencies.
2. Run a background script to test the Groq endpoint directly to confirm the API key is active.
3. Attempt to run a database query from the UI using the new Groq backend.
