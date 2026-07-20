import os
import sys
import json
import ee

CONFIG_FILE = os.path.join("data", "gee_config.json")

def setup_gee_authentication(project_id=None):
    print("======================================================")
    print("Boma Shield - Google Earth Engine Setup & Auth")
    print("======================================================")

    # Load existing config if available
    os.makedirs("data", exist_ok=True)
    if not project_id and os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                cfg = json.load(f)
                project_id = cfg.get("project_id")
        except Exception:
            pass

    if not project_id:
        if len(sys.argv) > 1:
            project_id = sys.argv[1]
        else:
            try:
                project_id = input("\nEnter your Google Cloud Project ID (e.g. ee-yourname or my-project-id): ").strip()
            except EOFError:
                project_id = os.getenv("EE_PROJECT_ID")

    if not project_id:
        print("[!] Project ID cannot be empty.")
        print("    Usage: python authenticate_gee.py <your-gcp-project-id>")
        sys.exit(1)

    print(f"\n[*] Initiating GEE Authentication for Project: '{project_id}'...")

    try:
        # Trigger GEE OAuth Web Flow
        ee.Authenticate()
        ee.Initialize(project=project_id)
        
        # Test query to confirm GEE access
        print("[*] Testing Earth Engine connection to Sentinel-2 collection...")
        image_count = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
                        .filterDate('2024-09-01', '2024-09-30') \
                        .size().getInfo()
        print(f"[+] Success! Connected to GEE. Found {image_count} Sentinel-2 scenes for Sept 2024.")

        # Save verified config
        with open(CONFIG_FILE, 'w') as f:
            json.dump({"project_id": project_id, "status": "AUTHENTICATED"}, f, indent=2)

        print(f"\n[+] GEE Authorization Complete! Config saved to {CONFIG_FILE}.")
        print("    Now you can run live satellite fetches using:")
        print("    python -m src.gee_fetcher")
        return True

    except Exception as e:
        print(f"\n[-] Error during GEE Authentication: {e}")
        print("    Ensure that your Google Cloud Project has Earth Engine API enabled in Google Cloud Console.")
        return False

if __name__ == "__main__":
    setup_gee_authentication()
