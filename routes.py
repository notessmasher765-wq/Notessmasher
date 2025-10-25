import os
import random
import uuid
from datetime import datetime
from flask import (
    Blueprint, render_template, redirect, url_for, request,
    flash, send_from_directory, jsonify  , current_app 
)
from flask_login import  login_required , login_user, logout_user, current_user
from werkzeug.utils import secure_filename
from flask_login import current_user
from models import db
from flask_dance.contrib.google import google
from models import User , Note ,AKTU , StickyNote , StudyTip , Explanation , SavedNote , ViewedNote , FeatureSuggestion , Feedback , Question , Answer 

from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from pdf2image import convert_from_path





routes = Blueprint("routes", __name__)
UPLOAD_FOLDER = "uploaded_notes"




# extensions.py
from extensions import db, bcrypt








# ✨ IMPORT CLEANED MODELS
from models import db, User, Note, SavedNote, ViewedNote, StudyTip, StickyNote, Explanation, FeatureSuggestion, Feedback

routes = Blueprint("routes", __name__)
UPLOAD_FOLDER = "uploaded_notes"
UPLOAD_FOLDER_NOTES = os.path.join("static", "uploads", "notes")
UPLOAD_FOLDER_THUMBNAILS = os.path.join("static", "uploads", "thumbnails")

# ------------------ BASIC ROUTES ------------------

@routes.route("/")
def home():
    try:
        latest_notes = Note.query.order_by(Note.created_at.desc()).limit(6).all()
    except Exception as e:
        db.session.rollback()  # important!
        print("Home page query error:", e)
        latest_notes = Note.query.order_by(Note.id.desc()).limit(6).all()
    return render_template('index.html', latest_notes=latest_notes)


@routes.route("/auth", methods=["GET", "POST"])
def auth():
    if request.method == "POST":
        action = request.form.get("action")

        if action == "login":
            identifier = request.form.get("username")
            password = request.form.get("password")
            user = User.query.filter((User.email == identifier) | (User.phone == identifier)).first()
            
            if user and user.password and bcrypt.check_password_hash(user.password, password):
                remember = True if request.form.get("remember") else False
                login_user(user, remember=remember)
                flash("Login successful!", "success")
                return redirect(url_for("routes.home"))
            else:
                flash("Invalid email/phone or password", "danger")

        elif action == "register":
            name = request.form.get("name")
            email = request.form.get("email")
            username = request.form.get("username")
            phone = request.form.get("phone")
            user_type = request.form.get("user_type")
            course = request.form.get("course") if user_type == "College" else None
            school_class = request.form.get("school_class") if user_type == "School" else None
            password = request.form.get("password")
            hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

            if User.query.filter((User.email == email) | (User.phone == phone)).first():
                flash("Email or Phone already registered. Try another!", "danger")
                return redirect(url_for("routes.auth"))

            new_user = User(
                name=name,
                username=username,
                email=email,
                phone=phone,
                user_type=user_type,
                course=course,
                school_class=school_class,
                password=hashed_password
            )
            db.session.add(new_user)
            db.session.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("routes.auth"))

    return render_template("auth.html")



@routes.route("/register", methods=["GET", "POST"])
def register():
    return redirect(url_for("routes.auth"))


@routes.route("/login", methods=["GET", "POST"])
def login():
    return redirect(url_for("routes.auth"))


@routes.route("/logout")
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("routes.home"))


# ------------------ DASHBOARD ------------------

@routes.route("/dashboard")
def dashboard():
    if current_user.is_authenticated:
        saved_notes = SavedNote.query.filter_by(user_id=current_user.id).all()
        viewed = (
            ViewedNote.query.filter_by(user_id=current_user.id)
            .order_by(ViewedNote.timestamp.desc())
            .limit(5)
            .all()
        )
        recently_viewed = [v.note for v in viewed]

        # ✅ Upload stats (real count)
        upload_count = Note.query.filter_by(user_id=current_user.id).count()

        # 🔻 Placeholder values (you can update logic later)
        download_count = 0  # Optional: track this in a new column or table
        public_view_count = 0  # Optional: maybe track Note views across users
    else:
        saved_notes = []
        recently_viewed = []
        upload_count = 0
        download_count = 0
        public_view_count = 0

    public_notes = Note.query.filter_by(is_public=True).order_by(Note.id.desc()).limit(5).all()

    return render_template(
        "dashboard.html",
        saved_notes=saved_notes,
        public_notes=public_notes,
        recently_viewed=recently_viewed,
        upload_count=upload_count,
        download_count=download_count,
        public_view_count=public_view_count
    )


@routes.route("/save_note/<int:note_id>", methods=["POST"])
def save_note(note_id):
    existing = SavedNote.query.filter_by(user_id=current_user.id, note_id=note_id).first()
    if not existing:
        new_saved = SavedNote(user_id=current_user.id, note_id=note_id)
        db.session.add(new_saved)
        db.session.commit()
        flash("Note saved! ⭐")
    else:
        flash("Already saved this note!")
    return redirect(request.referrer or url_for("routes.dashboard"))


@routes.route("/note/<int:note_id>")
def view_note(note_id):
    note = Note.query.get_or_404(note_id)
    view = ViewedNote(user_id=current_user.id, note_id=note_id)
    db.session.add(view)
    db.session.commit()
    return render_template("view_notes.html", note=note)

# ------------------ UPLOAD ------------------
import os
import uuid
from werkzeug.utils import secure_filename
from flask import request, redirect, url_for, flash, render_template, send_from_directory, current_app
from flask_login import current_user

# Folders
UPLOAD_FOLDER_NOTES = os.path.join("static", "uploads", "notes")
UPLOAD_FOLDER_THUMBNAILS = os.path.join("static", "uploads", "thumbnails")

@routes.route("/upload", methods=["GET", "POST"])
def upload():
    def allowed_file(filename):
        allowed_extensions = {'pdf', 'doc', 'docx', 'txt', 'png', 'jpg', 'jpeg'}
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

    if request.method == "POST":
        if not current_user.is_authenticated:
            flash("Please log in to upload notes.", "danger")
            return redirect(url_for("routes.auth"))

        # --- Get form data ---
        title = request.form.get("title", "").strip()
        course = request.form.get("course", "").strip()
        subject = request.form.get("subject", "").strip()
        session_val = request.form.get("session", "").strip()
        note_type = request.form.get("note_type", "").strip()
        typed_content = request.form.get("typed_content", "").strip()
        is_public = 'is_public' in request.form

        file = request.files.get("file")  # ✅ only once

        # --- Validate required fields ---
        if not title or not file or file.filename == "":
            flash("Please provide a title and upload a file!", "danger")
            return redirect(request.url)

        file_name = None
        file_url = None
        thumbnail_url = "/static/defaults/file_icon.png"

        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            extension = filename.rsplit('.', 1)[1].lower()

            # --- Choose upload folder ---
            if extension in ['pdf', 'doc', 'docx', 'txt']:
                upload_folder = UPLOAD_FOLDER_NOTES
            else:  # jpg, jpeg, png
                upload_folder = UPLOAD_FOLDER_THUMBNAILS

            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)

            # --- Browser-friendly path ---
            file_name = filename
            file_url = file_path.replace("static/", "/static/").replace("\\", "/")

          # --- Thumbnail logic ---
            if extension in ["jpg", "jpeg", "png"]:
                thumbnail_url = file_url
            
            elif extension == "pdf":
               os.makedirs(UPLOAD_FOLDER_THUMBNAILS, exist_ok=True)
           
            # OS-aware Poppler path
            import platform
            if platform.system() == "Windows":
                poppler_path = r"C:\Users\Lenovo\Downloads\Release-24.08.0-0\poppler-24.08.0\Library\bin"
                preview = convert_from_path(file_path, first_page=1, last_page=1, poppler_path=poppler_path)
            else:  # Linux / Render
                preview = convert_from_path(file_path, first_page=1, last_page=1)

            # This part must be OUTSIDE the if/else so it runs on both Windows & Linux
            thumb_name = f"{uuid.uuid4()}.jpg"
            thumb_path = os.path.join(UPLOAD_FOLDER_THUMBNAILS, thumb_name)
            preview[0].save(thumb_path, "JPEG")
            thumbnail_url = f"/static/uploads/thumbnails/{thumb_name}"



# --- Count pages based on file type ---
            ext = filename.rsplit('.', 1)[1].lower()
            pages = None

            if ext == "pdf":
                try:
                    reader = PdfReader(file_path)
                    pages = len(reader.pages)
                except Exception as e:
                    print("PDF page count error:", e)

            elif ext == "docx":
                try:
                    doc = docx.Document(file_path)
                    # Word doesn’t have real “pages”, so we’ll estimate:
                    word_count = sum(len(p.text.split()) for p in doc.paragraphs)
                    pages = max(1, word_count // 300)  # ~300 words = 1 page
                except Exception as e:
                    print("DOCX page count error:", e)

            elif ext == "txt":
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        words = f.read().split()
                        pages = max(1, len(words) // 300)
                except Exception as e:
                    print("TXT page count error:", e)

            elif ext in ["jpg", "jpeg", "png"]:
                pages = 1


            if not pages:
                pages = 1
                print("Final pages value:", pages)



            if not file_url:
                file_url = file_path.replace("static/", "/static/").replace("\\", "/")


       # --- Save note to DB ---
        new_note = Note(
        user_id=current_user.id,
        title=title,
        course=course or None,
        subject=subject or None,
        session=session_val or None,
        note_type=note_type or None,
        typed_content=typed_content or None,
        year=session_val or None,
        file_name=file_name,
        file_path=file_path.replace("static/", "/static/").replace("\\", "/"),  # absolute storage path
        file_url=file_url,  # ✅ now saving proper file_url
        is_public=is_public,
        thumbnail_url=thumbnail_url,
        pages=pages
                     )


        db.session.add(new_note)
        db.session.commit()
        flash("Note uploaded successfully!", "success")

    return render_template("upload.html", is_authenticated=current_user.is_authenticated)


@routes.route("/download/<int:note_id>")
def download_note(note_id):
    note = Note.query.get_or_404(note_id)
    if note.file_path:
        file_full_path = note.file_path.lstrip("/")
        abs_path = os.path.join("static", file_full_path.replace("static/", ""))

        if os.path.exists(abs_path):
            # Get file extension (.pdf, .jpg, etc.)
            _, ext = os.path.splitext(abs_path)

            # Use note title as download name
            download_name = f"{note.title}{ext}"

            return send_from_directory(
                directory=os.path.dirname(abs_path),
                path=os.path.basename(abs_path),
                as_attachment=True,
                download_name=download_name  # 👈 New name for download
            )

    flash("File not found", "danger")
    return redirect(url_for("routes.dashboard"))



# ------------------ STUDY TIPS ------------------

@routes.route("/study_tips", methods=["GET", "POST"])
def study_tips():
    if request.method == "POST":
        tip_text = request.form.get("tip_text")
        submitted_by = current_user.name if current_user.is_authenticated else "Anonymous"
        if tip_text.strip():
            tip = StudyTip(tip_text=tip_text.strip(), submitted_by=submitted_by)
            db.session.add(tip)
            db.session.commit()
            flash("Tip submitted successfully!", "success")
        else:
            flash("Tip can't be empty!", "danger")

    all_tips = StudyTip.query.order_by(StudyTip.id.desc()).all()
    return render_template("study_tips.html", tips=all_tips)


@routes.route("/share_tips", methods=["GET", "POST"])
def share_tips():
    if request.method == "POST":
        tip_text = request.form.get("tip_text")
        submitted_by = current_user.name if current_user.is_authenticated else "Anonymous"
        if tip_text.strip():
            tip = StudyTip(tip_text=tip_text.strip(), submitted_by=submitted_by)
            db.session.add(tip)
            db.session.commit()
            flash("Tip submitted successfully!", "success")
            return redirect(url_for("routes.study_tips"))
        else:
            flash("Tip can't be empty!", "danger")
    return render_template("share_tips.html")


# ------------------ POMODORO ------------------

@routes.route("/pomodoro")
def pomodoro():
    return render_template("pomodoro.html")


# ------------------ STICKY NOTES ------------------

@routes.route("/sticky_notes", methods=["GET", "POST"])
def sticky_notes():
    if request.method == "POST":
        content = request.form["note"]
        x = random.randint(50, 300)
        y = random.randint(50, 300)
        new_note = StickyNote(content=content, x=x, y=y)
        db.session.add(new_note)
        db.session.commit()
        return redirect(url_for("routes.sticky_notes"))

    notes = StickyNote.query.all()
    return render_template("sticky_notes.html", notes=notes)


@routes.route("/update_position/<int:note_id>", methods=["POST"])
def update_position(note_id):
    data = request.get_json()
    note = StickyNote.query.get(note_id)
    if note:
        note.x = data["x"]
        note.y = data["y"]
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"success": False}), 404


# ------------------ EXPLAIN ------------------

@routes.route("/explain", methods=["GET", "POST"])
def explain():
    if request.method == "POST":
        topic = request.form.get("topic")
        explanation = request.form.get("explanation")
        user_id = current_user.id if current_user.is_authenticated else None

        if topic and explanation:
            new_expl = Explanation(topic=topic, explanation=explanation, user_id=user_id)
            db.session.add(new_expl)
            db.session.commit()
            flash("Explanation posted!", "success")
            return redirect(url_for("routes.explain"))

    explanations = Explanation.query.order_by(Explanation.timestamp.desc()).all()
    return render_template("explain.html", explanations=explanations)


# ------------------ MY NOTES ------------------

@routes.route("/my_notes")
def my_notes():
    user_id = current_user.id if current_user.is_authenticated else 1

    search = request.args.get("search", "")
    subject = request.args.get("subject", "")
    note_type = request.args.get("type", "")
    session = request.args.get("session", "")

    query = Note.query.filter_by(user_id=user_id)

    if search:
        query = query.filter(Note.title.ilike(f"%{search}%"))
    if subject:
        query = query.filter_by(subject=subject)
    if note_type:
        query = query.filter_by(note_type=note_type)
    if session:
        query = query.filter_by(session=session)

    notes = query.order_by(Note.id.desc()).all()

    # Make sure we ignore None values before sorting
    all_subjects = sorted({n.subject for n in Note.query.filter_by(user_id=user_id) if n.subject})
    all_types = sorted({n.note_type for n in Note.query.filter_by(user_id=user_id) if n.note_type})
    all_sessions = sorted({n.session for n in Note.query.filter_by(user_id=user_id) if n.session})

    return render_template(
        "my_notes.html", 
        notes=notes,
        subjects=all_subjects, 
        types=all_types, 
        sessions=all_sessions
    )



# ------------------ VIEW NOTES ------------------

@routes.route("/view_notes")
def view_notes():
    search = request.args.get("search", "")
    subject = request.args.get("subject", "")
    note_type = request.args.get("type", "")
    session = request.args.get("session", "")

    query = Note.query

    if search:
        query = query.filter(Note.title.ilike(f"%{search}%"))
    if subject:
        query = query.filter_by(subject=subject)
    if note_type:
        query = query.filter_by(note_type=note_type)
    if session:
        query = query.filter_by(session=session)

    notes = query.order_by(Note.id.desc()).all()
    return render_template("view_notes.html", notes=notes)



@routes.route("/delete/<int:note_id>", methods=["POST"])
def delete_note(note_id):
    note = Note.query.get_or_404(note_id)
    
    # remove file from static folder if it exists
    if note.file_path:
        abs_path = note.file_path
        if abs_path.startswith("static/"):
            abs_path = abs_path
        else:
            abs_path = os.path.join("static", note.file_path)

        if os.path.exists(abs_path):
            os.remove(abs_path)

    db.session.delete(note)
    db.session.commit()
    
    flash("Note deleted successfully!", "success")
    return redirect(url_for("routes.view_notes"))



# ------------------ OTHER ROUTES ------------------
@routes.route("/user_home")
def user_home():   # 👈 renamed
    return render_template("user_home.html")



@routes.route("/about")
def about_us():
    return render_template("about_us.html")


@routes.route("/contact")
def contact():
    return render_template("contact.html")


@routes.route("/submit_contact", methods=["POST"])
def submit_contact():
    name = request.form.get("name") or "Anonymous"
    email = request.form.get("email")
    subject = request.form.get("subject")
    message = request.form.get("message")

    if not email or not subject or not message:
        flash("Please fill in all required fields.", "error")
        return redirect(url_for("routes.contact"))

    flash("Thanks for reaching out! I’ll get back to you soon 💌", "success")
    return redirect(url_for("routes.contact"))


# ------------------ SUGGESTIONS & FEEDBACK ------------------

@routes.route("/suggest")
def suggest_feature():
    suggestions = FeatureSuggestion.query.order_by(FeatureSuggestion.submitted_at.desc()).all()
    return render_template("suggest_feature.html", suggestions=suggestions)


@routes.route("/submit_feature", methods=["POST"])
def submit_feature():
    title = request.form["title"]
    description = request.form["description"]
    category = request.form["category"]
    priority = request.form.get("priority") or None
    username = request.form.get("username") or "Anonymous"
    email = request.form.get("email") or None

    attachment_file = request.files.get("attachment")
    filename = None
    if attachment_file and attachment_file.filename:
        filename = os.path.join(UPLOAD_FOLDER, attachment_file.filename)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        attachment_file.save(filename)

    suggestion = FeatureSuggestion(
        title=title, description=description, category=category,
        priority=priority, username=username, email=email, attachment=filename
    )

    db.session.add(suggestion)
    db.session.commit()
    flash("Thank you for your suggestion! 💜", "success")
    return redirect(url_for("routes.suggest_feature"))


@routes.route("/feedback", methods=["GET"])
def feedback():
    return render_template("feedback.html")


@routes.route("/submit_feedback", methods=["POST"])
def submit_feedback():
    name = request.form.get("name") or "Anonymous"
    email = request.form.get("email")
    feedback_type = request.form.get("type")
    message = request.form.get("message")
    mood = request.form.get("mood")

    if not feedback_type or not message:
        flash("Feedback Type and Message are required!", "error")
        return redirect(url_for("routes.feedback"))

    new_feedback = Feedback(
        name=name, email=email, feedback_type=feedback_type,
        message=message, mood=mood
    )

    db.session.add(new_feedback)
    db.session.commit()
    flash("Thanks for the feedback! You're helping us improve 💜", "success")
    return redirect(url_for("routes.feedback"))

# ------------------ PROFILE-------------------------------------------------------------------------------------------------------


@routes.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        current_user.name = request.form.get("name")
        current_user.email = request.form.get("email")
        current_user.course = request.form.get("course")
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("routes.profile"))

    uploaded_notes_count = Note.query.filter_by(user_id=current_user.id).count()

    return render_template("profile.html", user=current_user, uploaded_notes_count=uploaded_notes_count)

#-----------Terms And Conditions-------------------------------------------------------------------------------------------------

@routes.route('/terms')
def terms():
    return render_template('terms.html')  # create this file next

#------------------------GOOGLE LOGIN---------------------------------------------------------------------------------------------
import random
import uuid
from flask import redirect, url_for, flash
from flask_login import login_user
from models import User, db
from flask_dance.contrib.google import google

@routes.route("/google_login")
def google_login():
    if not google.authorized:
        return redirect(url_for("google.login"))  # Trigger Google OAuth

    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("Google login failed.", "danger")
        return redirect(url_for("routes.auth"))

    user_info = resp.json()
    email = user_info.get("email")
    name = user_info.get("name", "Google User")

    # Check if user already exists
    user = User.query.filter_by(email=email).first()

    if not user:
        # Generate a unique username
        username_base = name.lower().replace(" ", "")
        username = f"{username_base}{random.randint(1000,9999)}"

        # Create new user
        user = User(
            name=name,
            username=username,
            email=email,
            user_type="Google",
            password=None  # Make sure your User model allows password=None
        )
        db.session.add(user)
        db.session.commit()

    # Log the user in
    login_user(user)
    flash(" WELCOME !!! Logged in with Google!!!", "success")
    return redirect(url_for("routes.home"))




#-----------------------------------------------------------------------------------------------------------------------------



@routes.route("/note/<int:note_id>")
def view_note_page(note_id):
    note = Note.query.get_or_404(note_id)
    return render_template("view_note.html", note=note)

 #-----------------------------------------------------------------------------------------------------------------------------


@routes.route('/search_notes')
def search_notes():
    query = request.args.get('q', '').lower()
    if query:
        results = Note.query.filter(Note.title.ilike(f'%{query}%')).all()  # case-insensitive search
        notes_list = [{'id': n.id, 'title': n.title} for n in results]
    else:
        notes_list = []
    return jsonify(notes_list)

 #-----------------------------------------------------------------------------------------------------------------------------

@routes.route('/edit_note/<int:note_id>', methods=['GET', 'POST'])
@login_required
def edit_note(note_id):
    note = Note.query.get_or_404(note_id)

    if note.user_id != current_user.id:
        flash("You can't edit this note.", "danger")
        return redirect(url_for('routes.my_notes'))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('typed_content')
        if not title or not content:
            flash("Title and content cannot be empty!", "warning")
            return redirect(url_for('routes.edit_note', note_id=note_id))
        
        note.title = title
        note.typed_content = content
        db.session.commit()
        flash("Note updated successfully!", "success")
        return redirect(url_for('routes.my_notes'))

    return render_template('edit_note.html', note=note)



@routes.route('/aktu')
def aktu():
    year_filter = request.args.get('year')
    session_filter = request.args.get('session')

    # Start with all AKTU PYQ notes
    query = Note.query.filter_by(note_type="aktu_pyq")

    # Apply session filter only if provided
    if session_filter:
        query = query.filter_by(session=session_filter)

    # Apply year filter only if provided
    if year_filter:
        query = query.filter_by(year=year_filter)

    # Order by newest first
    aktu_notes = query.order_by(Note.created_at.desc()).all()

    # Sessions list from existing AKTU PYQs (for dropdown)
    sessions = sorted(set(n.session for n in Note.query.filter_by(note_type="aktu_pyq").all() if n.session))

    # Years list from existing AKTU PYQs (optional, if you want a dropdown for year too)
    years = sorted(set(n.year for n in Note.query.filter_by(note_type="aktu_pyq").all() if n.year))

    return render_template(
        'aktu.html',
        aktu=aktu_notes,
        sessions=sessions,
        years=years,
        selected_year=year_filter,
        selected_session=session_filter
    )

@routes.route("/question/", defaults={"question_id": None}, methods=["GET", "POST"])
@routes.route("/question/<int:question_id>", methods=["GET", "POST"])
def view_question(question_id):
    if question_id is None:
        # No question selected → show a blank form for asking a new question
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            content = request.form.get("content", "").strip()
            if title and content:
                new_question = Question(
                    title=title,
                    content=content,
                    user_id=current_user.id if current_user.is_authenticated else None
                )
                db.session.add(new_question)
                db.session.commit()
                flash("Question posted successfully! 💡", "success")
                return redirect(url_for("routes.view_question", question_id=new_question.id))
            else:
                flash("Title and content cannot be empty.", "warning")
        
        # Render the same template but with empty question
        return render_template("question.html", question=None, answers=[])

    # Existing logic for viewing a question
    question = Question.query.get_or_404(question_id)
    answers = Answer.query.filter_by(question_id=question.id).order_by(Answer.timestamp.desc()).all()

    if request.method == "POST":
        answer_text = request.form.get("answer_text", "").strip()
        if answer_text:
            new_answer = Answer(
                answer_text=answer_text,
                question_id=question.id,
                user_id=current_user.id if current_user.is_authenticated else None
            )
            db.session.add(new_answer)
            db.session.commit()
            flash("Answer submitted successfully! 💡", "success")
            return redirect(url_for("routes.view_question", question_id=question.id))
        else:
            flash("Answer cannot be empty.", "warning")

    return render_template("question.html", question=question, answers=answers)



# Robots.txt
@routes.route("/robots.txt")
def robots():
    return send_from_directory(current_app.static_folder, "robots.txt")

# Sitemap.xml
@routes.route("/sitemap.xml", methods=["GET"])
def sitemap():
    pages = []

    # ✅ Static pages with priority
    static_pages = {
        "routes.aktu": 0.9,
        "routes.home": 0.9,
        "routes.view_notes": 0.9,
        "routes.about": 0.6,
        "routes.share_tips": 0.6,
        "routes.dashboard": 0.6,
        "routes.upload": 0.6,
        "routes.explain": 0.6,
        "routes.study_tips": 0.6,
        "routes.sticky_notes": 0.6,
        "routes.contact": 0.6
    }

    for route_name, priority in static_pages.items():
        try:
            pages.append({
                "loc": url_for(route_name, _external=True),
                "lastmod": datetime.utcnow().strftime("%Y-%m-%d"),
                "priority": str(priority),
                "changefreq": "weekly" if priority == 0.6 else "daily"
            })
        except Exception as e:
            print(f"Error adding {route_name}: {e}")

    # ✅ Dynamic AKTU Notes
    aktu_notes = Note.query.filter_by(is_public=True, category="aktu").all()  # make sure you have a 'category' field
    for note in aktu_notes:
        pages.append({
            "loc": url_for("routes.view_note", note_id=note.id, _external=True),
            "lastmod": (note.updated_at or datetime.utcnow()).strftime("%Y-%m-%d"),
            "priority": "0.9",
            "changefreq": "daily"
        })

    # ✅ Other Public Notes (non-AKTU)
    other_notes = Note.query.filter_by(is_public=True).filter(Note.category != "aktu").all()
    for note in other_notes:
        pages.append({
            "loc": url_for("routes.view_note", note_id=note.id, _external=True),
            "lastmod": (note.updated_at or datetime.utcnow()).strftime("%Y-%m-%d"),
            "priority": "0.7",
            "changefreq": "daily"
        })

    # ✅ Render sitemap XML
    xml = render_template("sitemap_template.xml", pages=pages)
    return xml, 200, {"Content-Type": "application/xml"}


@routes.route('/googlef76d8f642f530023.html')
def google_verify():
    return send_from_directory('.', 'googlef76d8f642f530023.html')
