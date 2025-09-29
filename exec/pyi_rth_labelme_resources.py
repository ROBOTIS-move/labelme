import os
import sys

# Check if running in a PyInstaller bundle
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # Set the temporary directory path from PyInstaller
    temp_dir = sys._MEIPASS

    # Set the environment variable for the version.xml file path
    version_xml_path = os.path.join(temp_dir, 'version.xml')
    if os.path.exists(version_xml_path):
        os.environ['LABELME_VERSION_XML_PATH'] = version_xml_path

    # Set the environment variable for the package.xml file path
    package_xml_path = os.path.join(temp_dir, 'package.xml')
    if os.path.exists(package_xml_path):
        os.environ['LABELME_PACKAGE_XML_PATH'] = package_xml_path

    # Set environment variables for labelme resource directories
    labelme_dir = os.path.join(temp_dir, 'labelme')
    if os.path.exists(labelme_dir):
        os.environ['LABELME_RESOURCE_DIR'] = labelme_dir

        # config directory
        config_dir = os.path.join(labelme_dir, 'config')
        if os.path.exists(config_dir):
            os.environ['LABELME_CONFIG_DIR'] = config_dir

        # icons directory
        icons_dir = os.path.join(labelme_dir, 'icons')
        if os.path.exists(icons_dir):
            os.environ['LABELME_ICONS_DIR'] = icons_dir

        # translate directory
        translate_dir = os.path.join(labelme_dir, 'translate')
        if os.path.exists(translate_dir):
            os.environ['LABELME_TRANSLATE_DIR'] = translate_dir

    # Optional: Set the current working directory to the executable's location
    # os.chdir(os.path.dirname(sys.executable))

    # Add the temporary directory to the Python module search path
    if temp_dir not in sys.path:
        sys.path.insert(0, temp_dir)