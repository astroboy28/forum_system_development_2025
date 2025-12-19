from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import re
from pathlib import Path

app = Flask(__name__)
app.secret_key = "dev-secret"  # ok for class, not for production

#DB_PATH = Path("database.db")
#SCHEMA_PATH = Path("students.sql")

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database.db"
SCHEMA_PATH = BASE_DIR / "students.sql"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

def is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))

@app.get("/")
def home():
    return redirect(url_for("students_list"))

@app.get("/students")
def students_list():
    q = request.args.get("q", "").strip()
    with get_db() as conn:
        if q:
            rows = conn.execute(
                "SELECT * FROM students WHERE full_name LIKE ? OR email LIKE ? OR course LIKE ? ORDER BY id DESC",
                (f"%{q}%", f"%{q}%", f"%{q}%")
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM students ORDER BY id DESC").fetchall()
    return render_template("students_list.html", students=rows, q=q)

@app.route("/students/new", methods=["GET", "POST"])
def students_new():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        course = request.form.get("course", "").strip()
        year_level = request.form.get("year_level", "").strip()

        errors = []
        if len(full_name) < 2:
            errors.append("フルネームは 2 文字以上である必要があります。")
        if not is_valid_email(email):
            errors.append("有効なメールアドレスを入力してください。")
        if not course:
            errors.append("コースは必須です。")
        if not year_level.isdigit() or not (1 <= int(year_level) <= 5):
            errors.append("学年は 1 から 5 の数字である必要があります。")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("student_form.html", mode="new", student=request.form)

        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO students (full_name, email, course, year_level) VALUES (?, ?, ?, ?)",
                    (full_name, email, course, int(year_level))
                )
            flash("生徒が正常に追加されました。", "success")
            return redirect(url_for("students_list"))
        except sqlite3.IntegrityError:
            flash("メールアドレスは既に存在します。別のメールアドレスを使用してください。", "error")
            return render_template("student_form.html", mode="new", student=request.form)

    return render_template("student_form.html", mode="new", student=None)

@app.get("/students/<int:student_id>")
def students_detail(student_id):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if not row:
        flash("学生が見つかりません。", "error")
        return redirect(url_for("students_list"))
    return render_template("student_detail.html", student=row)

@app.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
def students_edit(student_id):
    with get_db() as conn:
        current = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if not current:
        flash("学生が見つかりません。", "error")
        return redirect(url_for("students_list"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        course = request.form.get("course", "").strip()
        year_level = request.form.get("year_level", "").strip()

        errors = []
        if len(full_name) < 2:
            errors.append("フルネームは 2 文字以上である必要があります。")
        if not is_valid_email(email):
            errors.append("有効なメールアドレスを入力してください。")
        if not course:
            errors.append("コースは必須です。")
        if not year_level.isdigit() or not (1 <= int(year_level) <= 5):
            errors.append("学年は 1 から 5 の数字である必要があります。")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("student_form.html", mode="edit", student_id=student_id, student=request.form)

        try:
            with get_db() as conn:
                # Unique email check except current student
                existing = conn.execute(
                    "SELECT id FROM students WHERE email = ? AND id != ?",
                    (email, student_id)
                ).fetchone()
                if existing:
                    flash("他の学生のメールアドレスが既に存在します。", "error")
                    return render_template("student_form.html", mode="edit", student_id=student_id, student=request.form)

                conn.execute(
                    "UPDATE students SET full_name=?, email=?, course=?, year_level=? WHERE id=?",
                    (full_name, email, course, int(year_level), student_id)
                )
            flash("生徒が正常に更新されました。", "success")
            return redirect(url_for("students_detail", student_id=student_id))
        except sqlite3.IntegrityError:
            flash("データベースルールにより更新に失敗しました。", "error")
            return render_template("student_form.html", mode="edit", student_id=student_id, student=request.form)

    return render_template("student_form.html", mode="edit", student_id=student_id, student=current)

@app.route("/students/<int:student_id>/delete", methods=["GET", "POST"])
def students_delete(student_id):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if not row:
        flash("学生が見つかりません。", "error")
        return redirect(url_for("students_list"))

    if request.method == "POST":
        with get_db() as conn:
            conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
        flash("生徒が削除されました。", "success")
        return redirect(url_for("students_list"))

    return render_template("confirm_delete.html", student=row)

if __name__ == "__main__":
    init_db()  # safe to run; uses IF NOT EXISTS
    app.run(debug=True)
