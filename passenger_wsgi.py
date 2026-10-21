import sys, os

# Tambahkan direktori kerja saat ini ke path Python
sys.path.insert(0, os.path.dirname(__file__))

# Import aplikasi Flask
from app import app as application
