# routes/task_route.py
from flask import Blueprint, render_template, request, redirect, url_for, session
from database_connector import get_db_connection
from .notification_route import create_notification

task_bp = Blueprint("task_bp", __name__, template_folder="../templates")

# -----------------------------
# List all tasks
# -----------------------------
@task_bp.route("/tasks")
def task_list():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth_bp.login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT t.*, u.name AS created_name, au.name AS assigned_name, g.name AS group_name
        FROM tasks t
        JOIN users u ON u.id = t.created_by
        LEFT JOIN users au ON au.id = t.assigned_to
        LEFT JOIN groups g ON g.id = t.group_id
        WHERE t.assigned_to=%s OR t.created_by=%s
        ORDER BY t.due_date ASC
    """, (user_id, user_id))
    tasks = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("task.html", tasks=tasks)

# -----------------------------
# View task details
# -----------------------------
@task_bp.route("/tasks/<int:task_id>")
def task_view(task_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth_bp.login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT t.*, u.name AS created_name, au.name AS assigned_name, g.name AS group_name
        FROM tasks t
        JOIN users u ON u.id = t.created_by
        LEFT JOIN users au ON au.id = t.assigned_to
        LEFT JOIN groups g ON g.id = t.group_id
        WHERE t.id = %s
    """, (task_id,))
    task = cursor.fetchone()
    cursor.close()
    conn.close()

    if not task:
        return "Task not found!", 404

    return render_template("task_view.html", task=task)

# -----------------------------
# Create a personal task
# -----------------------------
@task_bp.route("/tasks/new/personal", methods=["GET", "POST"])
def new_task_personal():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth_bp.login"))

    if request.method == "POST":
        title = request.form["title"]
        description = request.form.get("description")
        due_date = request.form.get("due_date")
        priority = request.form.get("priority")
        work_link = request.form.get("work_link") or None

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tasks (title, description, due_date, priority, assigned_to, created_by, status, work_link)
            VALUES (%s,%s,%s,%s,%s,%s,'pending',%s)
        """, (title, description, due_date, priority, user_id, user_id, work_link))
        conn.commit()
        cursor.close()
        conn.close()

        # Notify yourself that the task was created
        create_notification(user_id, f"You created a new personal task '{title}'")
        return redirect(url_for("task_bp.task_list"))

    return render_template("task_new.html")

# -----------------------------
# Create a group task
# -----------------------------
@task_bp.route("/tasks/new/group", methods=["GET", "POST"])
def new_task_group():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth_bp.login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    # Users to assign
    cursor.execute("SELECT id, name FROM users")
    users = cursor.fetchall()
    # Groups user belongs to
    cursor.execute("""
        SELECT g.id, g.name
        FROM groups g
        JOIN group_members gm ON g.id = gm.group_id
        WHERE gm.user_id=%s
    """, (user_id,))
    groups = cursor.fetchall()
    cursor.close()
    conn.close()

    if request.method == "POST":
        title = request.form["title"]
        description = request.form.get("description")
        due_date = request.form.get("due_date")
        priority = request.form.get("priority")
        assigned_to = request.form.get("assigned_to") or user_id
        group_id = request.form.get("group_id")
        work_link = request.form.get("work_link") or None

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tasks (title, description, due_date, priority, assigned_to, created_by, group_id, status, work_link)
            VALUES (%s,%s,%s,%s,%s,%s,%s,'pending',%s)
        """, (title, description, due_date, priority, assigned_to, user_id, group_id, work_link))
        conn.commit()
        cursor.close()
        conn.close()

        # Notify the assignee if it's not the creator
        if int(assigned_to) != user_id:
            create_notification(assigned_to, f"You have been assigned a new task '{title}' in a group.")

        return redirect(url_for("task_bp.task_list"))

    return render_template("task_new_group.html", users=users, groups=groups)

# -----------------------------
# Toggle task completion
# -----------------------------
@task_bp.route("/tasks/<int:task_id>/toggle", methods=["POST"])
def toggle_task(task_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth_bp.login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tasks WHERE id=%s", (task_id,))
    task = cursor.fetchone()

    if not task or task["assigned_to"] != user_id:
        cursor.close()
        conn.close()
        return "You cannot update this task.", 403

    new_status = "completed" if task["status"] != "completed" else "pending"
    cursor.execute("UPDATE tasks SET status=%s WHERE id=%s", (new_status, task_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    # Redirect back to the same page (task list)
    return redirect(url_for("task_bp.task_list"))


# -----------------------------
# Approve task (creator only)
# -----------------------------
@task_bp.route("/tasks/<int:task_id>/approve")
def approve_task(task_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth_bp.login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tasks WHERE id=%s", (task_id,))
    task = cursor.fetchone()

    if not task or task["created_by"] != user_id:
        cursor.close()
        conn.close()
        return "Not allowed", 403

    cursor.execute("UPDATE tasks SET is_approved=1 WHERE id=%s", (task_id,))
    conn.commit()
    cursor.close()
    conn.close()

    # Notify assignee
    if task["assigned_to"] != user_id:
        create_notification(task["assigned_to"], f"Your task '{task['title']}' was approved by the creator.")

    return redirect(url_for("task_bp.task_view", task_id=task_id))

@task_bp.route("/tasks/<int:task_id>/delete", methods=["POST"])
def delete_task(task_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth_bp.login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tasks WHERE id=%s", (task_id,))
    task = cursor.fetchone()

    if not task or task["created_by"] != user_id:
        cursor.close()
        conn.close()
        return "You cannot delete this task.", 403

    cursor.execute("DELETE FROM tasks WHERE id=%s", (task_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("task_bp.task_list"))