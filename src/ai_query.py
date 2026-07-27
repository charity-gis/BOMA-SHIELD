import os
import re
import duckdb
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize Groq client using OpenAI SDK
api_key = os.getenv('GROQ_API_KEY')
if not api_key:
    raise RuntimeError('GROQ_API_KEY not found in environment variables')

client = OpenAI(
    api_key=api_key,
    base_url="https://api.groq.com/openai/v1"
)

# Expanded safety check to block data manipulation and arbitrary file reading
DISALLOWED_PATTERNS = re.compile(r"\b(DROP|DELETE|INSERT|UPDATE|ALTER|COPY|INSTALL|LOAD|ATTACH|DETACH|READ_CSV|READ_PARQUET|READ_JSON|PRAGMA|SYSTEM)\b", re.IGNORECASE)

def is_safe_prompt(prompt: str) -> bool:
    """Return False if the prompt appears to request disallowed operations."""
    return not bool(DISALLOWED_PATTERNS.search(prompt))

def generate_sql(prompt: str, temperature: float = 0.2) -> str:
    """Generate a SELECT SQL query using Groq."""
    if not is_safe_prompt(prompt):
        raise ValueError('Prompt contains disallowed operations. Only data-retrieval queries are allowed.')

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

    response = client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[
            {"role": "system", "content": schema_instruction},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        top_p=0.95,
    )
    
    sql = response.choices[0].message.content.strip()
    
    # Robustly extract SQL if it is wrapped in markdown
    match = re.search(r"```(?:sql)?(.*?)```", sql, re.DOTALL | re.IGNORECASE)
    if match:
        sql = match.group(1).strip()
    
    sql = sql.strip()
    
    # Ensure it starts with SELECT
    if not sql.lower().startswith('select'):
        raise ValueError('Generated content is not a SELECT query.')
    return sql

def run_query(sql: str, df_scored=None) -> duckdb.DuckDBPyRelation:
    """Execute the given SELECT SQL against the project DuckDB database."""
    con = duckdb.connect('data/boma_shield.duckdb', read_only=True)
    con.execute("INSTALL spatial; LOAD spatial;")
    
    if df_scored is not None:
        df_safe = df_scored.copy()
        if 'geometry' in df_safe.columns:
            df_safe['wkt'] = df_safe['geometry'].apply(lambda geom: geom.wkt if getattr(geom, 'wkt', None) else None)
            df_safe = df_safe.drop(columns=['geometry'])
        con.register('scored_zones', df_safe)
        
    result = con.execute(sql)
    return result

def generate_report_answer(prompt: str, report_text: str, temperature: float = 0.2) -> str:
    """Answers a user's question based on the provided situation report text using Groq."""
    system_instruction = (
        "You are an expert conservation analyst and assistant for the Boma Shield project. "
        "You are provided with the latest generated Situation Report. "
        "Answer the user's question strictly based on the information in the report. "
        "If the answer is not contained in the report, politely say so. Do NOT invent data.\n\n"
        f"--- SITUATION REPORT ---\n{report_text}\n-----------------------"
    )

    response = client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        top_p=0.95,
    )
    
    return response.choices[0].message.content.strip()
