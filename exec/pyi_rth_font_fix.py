import os
import sys

try:
    # Suppress Qt font warnings
    os.environ['QT_LOGGING_RULES'] = 'qt5ct.debug=false;*.debug=false'

    # Force use of Windows system fonts
    os.environ['QT_QPA_FONTDIR'] = ''  # Set to empty to use system default fonts

    # Qt platform settings
    if sys.platform.startswith('win'):
        os.environ['QT_QPA_PLATFORM'] = 'windows:fontengine=directwrite'

    # Minimize Qt debug output
    os.environ['QT_QUIET_WARNINGS'] = '1'

except Exception as e:
    # Continue even if an error occurs
    pass