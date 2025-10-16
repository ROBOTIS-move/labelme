import os
import sys

def resource_path(relative_path):
    """
    Returns the absolute path to a resource file in a PyInstaller environment.

    Args:
        relative_path (str): The relative path of the resource file.

    Returns:
        str: The absolute path of the resource file.
    """
    try:
        # If in a PyInstaller environment
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # Resource path in the temporary directory
            return os.path.join(sys._MEIPASS, relative_path)
        else:
            # If in a development environment
            return os.path.join(os.path.abspath('.'), relative_path)
    except Exception:
        # Fallback: based on the current directory
        return relative_path

# Add to builtins to be globally available
try:
    import builtins
    builtins.resource_path = resource_path
except ImportError:
    # Python 2 compatibility
    import __builtin__
    __builtin__.resource_path = resource_path

# Detect PyInstaller environment and set paths
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    temp_dir = sys._MEIPASS

    # Set environment variables for major resource directories
    resource_mappings = {
        'LABELME_BASE_DIR': temp_dir,
        'LABELME_DATA_DIR': os.path.join(temp_dir, 'labelme'),
        'LABELME_CONFIG_DIR': os.path.join(temp_dir, 'labelme', 'config'),
        'LABELME_ICONS_DIR': os.path.join(temp_dir, 'labelme', 'icons'),
        'LABELME_TRANSLATE_DIR': os.path.join(temp_dir, 'labelme', 'translate'),
    }

    for env_var, path in resource_mappings.items():
        if os.path.exists(path):
            os.environ[env_var] = path

    # Set Qt resource path
    qt_conf_path = os.path.join(temp_dir, 'qt.conf')
    if not os.path.exists(qt_conf_path):
        try:
            with open(qt_conf_path, 'w') as f:
                f.write('[Paths]\n')
                f.write(f'Prefix = {temp_dir}\n')
                f.write('Binaries = .\n')
                f.write('Libraries = .\n')
                f.write('Plugins = qt5_plugins\n')
        except Exception:
            pass
