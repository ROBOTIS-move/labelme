# Runtime hook for labelme resource files
import os
import sys

# PyInstaller 환경에서 실행 중인지 확인
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # version.xml 파일 경로를 환경변수로 설정
    version_xml_path = os.path.join(sys._MEIPASS, 'version.xml')
    if os.path.exists(version_xml_path):
        os.environ['LABELME_VERSION_XML_PATH'] = version_xml_path
    
    package_xml_path = os.path.join(sys._MEIPASS, 'package.xml')  
    if os.path.exists(package_xml_path):
        os.environ['LABELME_PACKAGE_XML_PATH'] = package_xml_path
