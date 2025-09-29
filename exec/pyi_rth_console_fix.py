import sys
import os
import io

def _fix_console_output():
    """Fix stdout/stderr issues in PyInstaller bundled applications"""
    try:
        # Set environment variable for unbuffered output
        os.environ['PYTHONUNBUFFERED'] = '1'

        # Check if we're running in a PyInstaller bundle
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):

            # If stdout/stderr are None (common in windowed apps), create dummy ones
            if sys.stdout is None:
                sys.stdout = io.StringIO()
            if sys.stderr is None:
                sys.stderr = io.StringIO()

            # For Windows console applications, try to allocate a console if needed
            if hasattr(sys, 'platform') and sys.platform.startswith('win'):
                try:
                    # Try to allocate a console for output
                    import ctypes
                    from ctypes import wintypes

                    kernel32 = ctypes.windll.kernel32

                    # Check if we already have a console
                    if kernel32.GetConsoleWindow() == 0:
                        # Try to allocate a new console
                        if kernel32.AllocConsole():
                            # Redirect stdout/stderr to the new console
                            import msvcrt

                            # Get console handles
                            stdout_handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
                            stderr_handle = kernel32.GetStdHandle(-12)  # STD_ERROR_HANDLE

                            if stdout_handle and stdout_handle != -1:
                                sys.stdout = io.TextIOWrapper(
                                    io.FileIO(msvcrt.open_osfhandle(stdout_handle, 0), 'w'),
                                    encoding='utf-8', line_buffering=True
                                )
                            if stderr_handle and stderr_handle != -1:
                                sys.stderr = io.TextIOWrapper(
                                    io.FileIO(msvcrt.open_osfhandle(stderr_handle, 0), 'w'),
                                    encoding='utf-8', line_buffering=True
                                )

                except (ImportError, AttributeError, OSError):
                    # If console allocation fails, use string buffers
                    if not hasattr(sys.stdout, 'write'):
                        sys.stdout = io.StringIO()
                    if not hasattr(sys.stderr, 'write'):
                        sys.stderr = io.StringIO()

        # Ensure stdout/stderr have write method
        if not hasattr(sys.stdout, 'write'):
            sys.stdout = io.StringIO()
        if not hasattr(sys.stderr, 'write'):
            sys.stderr = io.StringIO()

    except Exception as e:
        # Last resort: create dummy stdout/stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        # Write error to a file for debugging
        try:
            with open(os.path.join(os.path.dirname(sys.executable), 'console_fix_error.log'), 'w') as f:
                f.write(f"Console fix error: {e}\n")
        except:
            pass

# Execute the fix
_fix_console_output()