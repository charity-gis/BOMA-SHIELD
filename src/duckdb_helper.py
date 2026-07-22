import duckdb
import os

def connect_db(path="data/boma_shield.duckdb"):
    """Connect to DuckDB and ensure spatial extension is loaded."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    con = duckdb.connect(path)
    con.execute("INSTALL spatial; LOAD spatial;")
    return con

def register_parquet(con, table_name, parquet_path):
    """Register a GeoParquet file as a DuckDB table."""
    if os.path.exists(parquet_path):
        con.execute(f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM read_parquet('{parquet_path}');")
        print(f"Registered {table_name} from {parquet_path}")
    else:
        print(f"Warning: {parquet_path} not found.")

def init_tables():
    """Initialize all static parquet tables."""
    con = connect_db()
    register_parquet(con, 'hex_grid', 'data/parquet/hex_grid.parquet')
    return con

if __name__ == "__main__":
    init_tables()
