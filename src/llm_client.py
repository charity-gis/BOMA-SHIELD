import os
import re
from google import genai
from dotenv import load_dotenv

# Load environment variables (expects GEMINI_API_KEY in .env)
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY not set in environment")

# Configure the Gemini client
client = genai.Client(api_key=API_KEY)

def _extract_sql(response_text: str) -> str:
    """Extract the first SELECT statement from the LLM response."""
    # Remove markdown fences if present
    cleaned = response_text.strip().strip('`')
    # Search for a SELECT line
    match = re.search(r"SELECT[\s\S]*", cleaned, re.IGNORECASE)
    if match:
        return match.group(0).strip()
    # Fallback: return the whole cleaned text
    return cleaned

def generate_sql(question: str) -> str:
    """Generate a DuckDB SELECT query using Gemini.

    The prompt supplies a brief description of the available tables. The function
    returns only the SQL string (no explanatory text).
    """
    prompt = f"""
You are a data analyst with access to a DuckDB database that contains the following tables:
- conservancies (columns: name, area_km2, risk_score, risk_level, primary_drivers, ...)
- parks (columns: name, area_km2, ...)
- settlements (columns: name, lat, lon, population, ...)
- waterpoints (columns: name, lat, lon, ...)

Write a single valid DuckDB SELECT statement that answers the user's natural‑language question.
Return only the SQL query, without any additional commentary.

User question: {question}
"""
    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    sql = _extract_sql(response.text)
    return sql
