import os
import re
import duckdb
from dotenv import load_dotenv
from google import genai

# Load environment variables (including GEMINI_API_KEY)
load_dotenv()

# Initialize Gemini client
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    raise RuntimeError('GEMINI_API_KEY not found in environment variables')
client = genai.Client(api_key=api_key)

# Simple safety check for disallowed SQL commands
DISALLOWED_PATTERNS = re.compile(r"\b(DROP|DELETE|INSERT|UPDATE|ALTER)\b", re.IGNORECASE)

def is_safe_prompt(prompt: str) -> bool:
    """Return False if the prompt appears to request disallowed operations."""
    return not bool(DISALLOWED_PATTERNS.search(prompt))

def generate_sql(prompt: str, temperature: float = 0.2, max_output_tokens: int = 256) -> str:
    """Generate a SELECT SQL query using Gemini.

    Args:
        prompt: User's natural‑language request.
        temperature: Controls randomness (0.0‑1.0).
        max_output_tokens: Upper bound on token count for the response.
    Returns:
        The generated SQL string.
    """
    if not is_safe_prompt(prompt):
        raise ValueError('Prompt contains disallowed operations. Only data‑retrieval queries are allowed.')

    # Construct a system instruction that tells the model about the schema
    schema_instruction = (
        "You are given a DuckDB database with the following tables and columns:\n"
        "- conservancies(id INTEGER, name TEXT, clean_name TEXT, geometry GEOMETRY, ... )\n"
        "- parks(id INTEGER, name TEXT, clean_name TEXT, geometry GEOMETRY, ... )\n"
        "- settlements(id INTEGER, name TEXT, geometry GEOMETRY, ... )\n"
        "- waterpoints(id INTEGER, name TEXT, lat FLOAT, lon FLOAT, geometry GEOMETRY, ... )\n"
        "Write ONLY a single SELECT statement that fulfills the user's request. Do not include any explanation or extra text."
    )

    response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=[schema_instruction, f"User request: {prompt}"],
    generation_config=genai.types.GenerationConfig(
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        top_p=0.95,
    ),
)
    sql = response.text.strip()
    # Ensure it starts with SELECT
    if not sql.lower().startswith('select'):
        raise ValueError('Generated content is not a SELECT query.')
    return sql

def run_query(sql: str) -> duckdb.DuckDBPyRelation:
    """Execute the given SELECT SQL against the project DuckDB database.
    Returns a DuckDB relation (can be converted to pandas with .df()).
    """
    con = duckdb.connect('data/boma_shield.duckdb')
    result = con.execute(sql)
    return result
