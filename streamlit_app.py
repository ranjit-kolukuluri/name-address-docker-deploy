import sys
import os
from pathlib import Path

# Add the project directories to the Python path
current_dir = Path(__file__).parent
ui_dir = current_dir / "ui"
project_root = current_dir

for path in [str(project_root), str(ui_dir)]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Set environment for Docker
os.environ.setdefault('DOCKER_ENV', 'true')

def main():
    """Main entry point for Streamlit Cloud"""
    try:
        # Import and run the main app directly
        # Let the existing ValidatorApp.run() method handle set_page_config
        from ui.app import main as app_main
        
        # Run the application
        app_main()
        
    except ImportError as e:
        import streamlit as st
        st.error(f"❌ Import Error: {str(e)}")
        st.error("Please ensure all dependencies are installed and paths are correct.")
        st.code(f"""
        # Debug information:
        Current directory: {current_dir}
        Python path: {sys.path}
        """)
        
    except Exception as e:
        import streamlit as st
        st.error(f"❌ Application Error: {str(e)}")
        st.error("Please check the application logs for more details.")

if __name__ == "__main__":
    main()