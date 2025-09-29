#!/usr/bin/env python3
"""
PyInstaller runtime hook for handling user data files like worker_name.txt
"""

import os
import sys
import shutil

def get_user_data_dir(app_name="labelme"):
    """
    Returns the user data directory path.
    Windows: %APPDATA%\\labelme
    """
    if sys.platform.startswith('win'):
        base_dir = os.path.expandvars('%APPDATA%')
    else:
        # Linux/Mac support
        base_dir = os.path.expanduser('~/.config')
    
    user_data_dir = os.path.join(base_dir, app_name)
    
    # Create directory if it doesn't exist
    os.makedirs(user_data_dir, exist_ok=True)
    
    return user_data_dir

def setup_user_data_paths():
    """
    Sets up paths for user data files.
    """
    try:
        user_data_dir = get_user_data_dir()
        
        # Set worker_name.txt file path
        worker_name_file = os.path.join(user_data_dir, 'worker_name.txt')
        os.environ['LABELME_WORKER_NAME_FILE'] = worker_name_file
        
        # Set paths for other user configuration files
        config_file = os.path.join(user_data_dir, 'config.yaml')
        os.environ['LABELME_CONFIG_FILE'] = config_file
        
        # Set user data directory itself as environment variable
        os.environ['LABELME_USER_DATA_DIR'] = user_data_dir
        
        # If running in PyInstaller environment, migrate files from temporary directory
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            temp_worker_file = os.path.join(sys._MEIPASS, 'worker_name.txt')
            
            # If worker_name.txt exists in temp directory but not in user directory, copy it
            if os.path.exists(temp_worker_file) and not os.path.exists(worker_name_file):
                try:
                    shutil.copy2(temp_worker_file, worker_name_file)
                except Exception:
                    pass  # Continue even if copy fails
        
        # Debug output (uncomment if needed)
        # print(f"[DEBUG] User data dir: {user_data_dir}")
        # print(f"[DEBUG] Worker name file: {worker_name_file}")
        
    except Exception as e:
        # Continue program execution even if an error occurs
        print(f"[WARNING] Failed to setup user data paths: {e}")

# Execute runtime hook
if __name__ == '__main__' or getattr(sys, 'frozen', False):
    setup_user_data_paths()

# Add to builtins for global function usage
try:
    import builtins
    builtins.get_user_data_dir = get_user_data_dir
except ImportError:
    pass