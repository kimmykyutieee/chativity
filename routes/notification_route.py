# routes/notification_route.py
from flask import Blueprint, session, redirect, url_for, render_template
from database_connector import get_db_connection

notification_bp = Blueprint("notification_bp", __name__, template_folder="../templates")

def create_notification(user_id, message):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO notifications (user_id, message) VALUES (%s, %s)",
        (user_id, message)
    )
    conn.commit()
    cursor.close()
    conn.close()


@notification_bp.route("/notifications")
def notifications():
    if "user_id" not in session:
        return redirect(url_for("auth_bp.login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM notifications WHERE user_id=%s ORDER BY created_at DESC",
        (session["user_id"],)
    )
    notes = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("notifications.html", notifications=notes)
