from mangum import Mangum
import sys
import os

# Add app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.main import create_app

app = create_app()
handler = Mangum(app)