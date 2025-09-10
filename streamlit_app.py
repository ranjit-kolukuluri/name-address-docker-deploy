import os
import sys
from pathlib import Path

# Add project root to path for imports
current_file = Path(__file__).resolve()
project_root = current_file.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import the main app
from ui.app import main

if __name__ == "__main__":
    # 🔧 FIXED: Set dictionary path from environment
    dictionary_path = os.getenv('DICTIONARY_PATH', '/app/dictionaries')
    
    if dictionary_path and os.path.exists(dictionary_path):
        print(f"✅ Using dictionary path: {dictionary_path}")
        files = os.listdir(dictionary_path)
        if files:
            print(f"✅ Dictionary files found: {files}")
        else:
            print("⚠️ Dictionary directory is empty")
    else:
        print("⚠️ No dictionary path found - using AI-only validation")
    
    # Start the app
    main()