
import sys
import os

# Add current directory to sys.path just in case
sys.path.append(os.getcwd())

try:
    from routes.auth import auth_bp
    print("SUCCESS: routes.auth imported successfully")
except Exception as e:
    print(f"FAILURE: Could not import routes.auth: {e}")
    import traceback
    traceback.print_exc()
