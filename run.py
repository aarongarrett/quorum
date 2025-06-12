import os

from app import create_app

from dotenv import load_dotenv, find_dotenv

env_path = find_dotenv()
if env_path:
    load_dotenv(env_path, override=False)

app = create_app(os.getenv("QUORUM_FLASK_ENV", "development"))

if __name__ == "__main__":
    app.run(debug=True)