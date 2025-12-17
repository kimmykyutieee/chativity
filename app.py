from flask import Flask, redirect, url_for
from database_connector import get_db_connection

# Import all route blueprints
from routes.index_route import index_bp
from routes.auth_route import auth_bp
from routes.dashboard_route import dashboard_bp
from routes.profile_route import profile_bp
from routes.task_route import task_bp
from routes.notification_route import notification_bp
from routes.group_route import group_bp

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Needed for session management

# -----------------------------
# REGISTER BLUEPRINTS
# -----------------------------
app.register_blueprint(index_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(task_bp)
app.register_blueprint(notification_bp)
app.register_blueprint(group_bp)

# -----------------------------
# REDIRECT ROOT TO INDEX
# -----------------------------
@app.route("/")
def home():
    return redirect(url_for("index_bp.index"))

# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
