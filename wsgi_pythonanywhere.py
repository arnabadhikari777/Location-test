# PythonAnywhere -> Web tab -> WSGI configuration file এর ভেতরে এই কোড বসাও।
# 'yourusername' ও 'location_test' নিজের মতো বদলাও।
import sys

path = "/home/yourusername/location_test"
if path not in sys.path:
    sys.path.insert(0, path)

from app import app as application  # noqa
