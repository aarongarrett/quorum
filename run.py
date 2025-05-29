import os
from app import create_app

# Read FLASK_CONFIG (or FLASK_ENV) to decide which config to use
cfg = os.getenv("FLASK_CONFIG", os.getenv("FLASK_ENV", "default"))
app = create_app(cfg)

if __name__ == '__main__':
    app.run(debug=True)
