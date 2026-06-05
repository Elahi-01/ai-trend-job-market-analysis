"""Entry point for the AI Trend Job Market Analysis application."""
import os
from app import create_app
from config.settings import config

config_name = os.environ.get("FLASK_ENV", "development")
app = create_app(config.get(config_name, config["default"]))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() in {"1", "true", "yes", "on"}
    app.run(host="0.0.0.0", port=port, debug=debug)
