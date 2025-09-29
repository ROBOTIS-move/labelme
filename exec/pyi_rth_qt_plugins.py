#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyInstaller runtime hook to fix Qt plugin conflicts between OpenCV and PyQt5.
This hook ensures that only PyQt5's Qt plugins are used, preventing conflicts.
"""

import os
import sys
import logging

def _pyi_rth_qt_plugins():
    """Fix Qt plugin path conflicts between OpenCV and PyQt5"""
    try:
        # OpenCV's Qt plugin paths that cause conflicts
        cv2_qt_paths = [
            os.path.join(sys._MEIPASS, 'cv2', 'qt', 'plugins'),
            os.path.join(sys._MEIPASS, 'cv2', 'qt5', 'plugins'),
        ]
        
        # Remove problematic CV2 Qt plugin paths from environment
        qt_plugin_path = os.environ.get('QT_PLUGIN_PATH', '')
        if qt_plugin_path:
            paths = qt_plugin_path.split(os.pathsep)
            paths = [p for p in paths if not any(cv2_path in p for cv2_path in cv2_qt_paths)]
            os.environ['QT_PLUGIN_PATH'] = os.pathsep.join(paths)
        
        # Ensure PyQt5 plugin path is prioritized
        pyqt5_plugin_path = os.path.join(sys._MEIPASS, 'PyQt5', 'Qt5', 'plugins')
        if os.path.exists(pyqt5_plugin_path):
            if qt_plugin_path:
                os.environ['QT_PLUGIN_PATH'] = pyqt5_plugin_path + os.pathsep + os.environ['QT_PLUGIN_PATH']
            else:
                os.environ['QT_PLUGIN_PATH'] = pyqt5_plugin_path
        
        # Set Qt to prefer PyQt5 plugins
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = pyqt5_plugin_path
        
        # Disable OpenCV's Qt backend to prevent conflicts
        os.environ['OPENCV_IO_ENABLE_JASPER'] = '0'
        os.environ['OPENCV_IO_ENABLE_OPENEXR'] = '0'
        
        # Ensure Qt uses the correct platform plugin
        if 'QT_QPA_PLATFORM' not in os.environ:
            # Try to detect display capability
            if os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'):
                os.environ['QT_QPA_PLATFORM'] = 'xcb'
            else:
                os.environ['QT_QPA_PLATFORM'] = 'offscreen'
        
        # Clean up any conflicting library paths
        ld_library_path = os.environ.get('LD_LIBRARY_PATH', '')
        if ld_library_path:
            paths = ld_library_path.split(os.pathsep)
            # Remove CV2 Qt library paths that might conflict
            paths = [p for p in paths if 'cv2/qt' not in p.lower()]
            os.environ['LD_LIBRARY_PATH'] = os.pathsep.join(paths)
        
    except Exception as e:
        # Log error but don't fail the application startup
        logging.warning(f"Qt plugin path setup warning: {e}")

# Execute the fix
_pyi_rth_qt_plugins()