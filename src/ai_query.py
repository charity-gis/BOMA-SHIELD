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

    schema_instruction = (
        "You are an expert DuckDB spatial SQL analyst. You are given a DuckDB database with the EXACT following tables and columns. DO NOT invent or shorten table names:\n"
        "- scored_zones(name TEXT, category TEXT, risk_level TEXT, risk_score DOUBLE, ndvi_stress DOUBLE, rainfall_deficit DOUBLE, water_proximity DOUBLE, boundary_proximity DOUBLE, livestock_density DOUBLE, corridor_obstruction DOUBLE, primary_drivers TEXT, area_km2 DOUBLE, wkt VARCHAR)\n"
        "- conservancies(name TEXT, clean_name TEXT, wkt VARCHAR)\n"
        "- parks(Name TEXT, name_en TEXT, wkt VARCHAR)\n"
        "- settlements(name TEXT, wkt VARCHAR)\n"
        "- waterpoints(Name TEXT, wkt VARCHAR)\n"
        "Rules:\n"
        "1. Write ONLY a single valid DuckDB SELECT statement.\n"
        "2. Do not include any explanation or markdown formatting (no ```sql).\n"
        "3. Use proper table aliases (e.g. FROM scored_zones AS sz).\n"
        "4. You MUST use the exact table names provided. Do not abbreviate them.\n"
        "5. The spatial data is stored as a string in the 'wkt' column. You MUST use ST_GeomFromText(wkt) to convert it to a geometry before using DuckDB spatial functions."
    )

    response = client.models.generate_content(
    model='gemini-2.0-flash',
    contents=[schema_instruction, f"User request: {prompt}"],
    config=genai.types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=1024,
        top_p=0.95,
    ),
)
    sql = response.text.strip()
    
    # Robustly extract SQL if it is wrapped in markdown, ignoring any surrounding text
    match = re.search(r"```(?:sql)?(.*?)```", sql, re.DOTALL | re.IGNORECASE)
    if match:
        sql = match.group(1).strip()
    
    # Fallback to strip trailing semicolons for single queries, though DuckDB usually accepts them
    sql = sql.strip()
    
    # Ensure it starts with SELECT
    if not sql.lower().startswith('select'):
        raise ValueError('Generated content is not a SELECT query.')
    return sql

def run_query(sql: str, df_scored=None) -> duckdb.DuckDBPyRelation:
    """Execute the given SELECT SQL against the project DuckDB database.
    Returns a DuckDB relation (can be converted to pandas with .df()).
    """
    con = duckdb.connect('data/boma_shield.duckdb', read_only=True)
    con.execute("INSTALL spatial; LOAD spatial;")
    
    if df_scored is not None:
        # Create a safe copy with WKT strings instead of Shapely geometries for DuckDB
        df_safe = df_scored.copy()
        if 'geometry' in df_safe.columns:
            df_safe['wkt'] = df_safe['geometry'].apply(lambda geom: geom.wkt if getattr(geom, 'wkt', None) else None)
            df_safe = df_safe.drop(columns=['geometry'])
        con.register('scored_zones', df_safe)
        
    result = con.execute(sql)
    return result
