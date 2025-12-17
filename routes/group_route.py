# routes/group_route.py
from flask import Blueprint, render_template, request, redirect, url_for, session
from database_connector import get_db_connection
import random, string
from .notification_route import create_notification

group_bp = Blueprint('group_bp', __name__, template_folder='../templates')

def generate_group_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


@group_bp.route("/groups")
def groups_list():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth_bp.login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT g.id, g.name FROM groups g
        JOIN group_members gm ON g.id = gm.group_id
        WHERE gm.user_id=%s
    """, (user_id,))
    groups = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("groups.html", groups=groups)


@group_bp.route("/groups/new", methods=["GET", "POST"])
def new_group():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth_bp.login"))

    if request.method == "POST":
        name = request.form["name"]
        code = generate_group_code()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO groups (name, created_by, code) VALUES (%s, %s, %s)",
            (name, user_id, code)
        )
        group_id = cursor.lastrowid
        cursor.execute("INSERT INTO group_members (group_id, user_id) VALUES (%s, %s)", (group_id, user_id))
        conn.commit()
        cursor.close()
        conn.close()

        create_notification(user_id, f"You created a new group '{name}'")
        return redirect(url_for("group_bp.groups_list"))

    return render_template("new_group.html")


@group_bp.route("/groups/join", methods=["GET", "POST"])
def join_group_by_code():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth_bp.login"))

    if request.method == "POST":
        code = request.form["code"].upper()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM groups WHERE code=%s", (code,))
        group = cursor.fetchone()
        if group:
            cursor.execute(
                "SELECT * FROM group_members WHERE group_id=%s AND user_id=%s",
                (group["id"], user_id)
            )
            membership = cursor.fetchone()
            if not membership:
                cursor.execute("INSERT INTO group_members (group_id, user_id) VALUES (%s,%s)", (group["id"], user_id))
                conn.commit()
                create_notification(user_id, f"You were added to the group '{group['name']}'")
            cursor.close()
            conn.close()
            return redirect(url_for("group_bp.group_chat", group_id=group["id"]))
        cursor.close()
        conn.close()
        return "Invalid group code!", 400

    return render_template("join_group.html")


@group_bp.route("/groups/<int:group_id>", methods=["GET", "POST"])
def group_chat(group_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth_bp.login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST" and "message" in request.form:
        message = request.form["message"]
        cursor.execute(
            "INSERT INTO group_messages (group_id, sender_id, message) VALUES (%s,%s,%s)",
            (group_id, user_id, message)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for("group_bp.group_chat", group_id=group_id))

    cursor.execute("SELECT * FROM groups WHERE id=%s", (group_id,))
    group = cursor.fetchone()
    if not group:
        cursor.close()
        conn.close()
        return "Group not found!", 404

    cursor.execute("""
        SELECT gm.*, u.name AS sender_name
        FROM group_messages gm
        JOIN users u ON u.id = gm.sender_id
        WHERE gm.group_id=%s
        ORDER BY gm.created_at ASC
    """, (group_id,))
    messages = cursor.fetchall()

    cursor.execute("""
        SELECT u.id, u.name
        FROM group_members gm
        JOIN users u ON u.id = gm.user_id
        WHERE gm.group_id=%s
    """, (group_id,))
    members = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template("group_chat.html", group=group, messages=messages, members=members)


@group_bp.route("/groups/<int:group_id>/delete", methods=["POST"])
def delete_group(group_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth_bp.login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM groups WHERE id=%s", (group_id,))
    group = cursor.fetchone()
    if not group:
        cursor.close()
        conn.close()
        return "Group not found!", 404

    if group["created_by"] != user_id:
        cursor.close()
        conn.close()
        return "You are not allowed to delete this group.", 403

    # Notify members
    cursor.execute("SELECT user_id FROM group_members WHERE group_id=%s", (group_id,))
    members = cursor.fetchall()
    for m in members:
        create_notification(m["user_id"], f"The group '{group['name']}' was deleted.")

    cursor.execute("DELETE FROM group_messages WHERE group_id=%s", (group_id,))
    cursor.execute("DELETE FROM group_members WHERE group_id=%s", (group_id,))
    cursor.execute("DELETE FROM groups WHERE id=%s", (group_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("group_bp.groups_list"))
