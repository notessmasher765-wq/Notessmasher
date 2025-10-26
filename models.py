from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=True)
    phone = db.Column(db.String(15), unique=True, nullable=True)
    user_type = db.Column(db.String(20), nullable=False)
    course = db.Column(db.String(100), nullable=True)
    school_class = db.Column(db.String(100), nullable=True)

    notes = db.relationship("Note", backref="user", lazy=True)
    saved_notes = db.relationship("SavedNote", backref="user", lazy=True)
    viewed_notes = db.relationship("ViewedNote", backref="user", lazy=True)
    explanations = db.relationship("Explanation", backref="user", lazy=True)
    questions = db.relationship("Question", backref="user", lazy=True)
    answers = db.relationship("Answer", backref="user", lazy=True)

    def __repr__(self):
        return f"<User {self.username}>"


class Note(db.Model):
    __tablename__ = 'note'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    course = db.Column(db.String(100), nullable=True)
    note_type = db.Column(db.String(50), nullable=True)
    subject = db.Column(db.String(100), nullable=True)
    session = db.Column(db.String(20), nullable=True)
    typed_content = db.Column(db.Text, nullable=True)
    year = db.Column(db.String(20), nullable=True)

    file_name = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(300), nullable=False)
    file_url = db.Column(db.String(500), nullable=False)
    thumbnail_url = db.Column(db.String(500), nullable=True)
    pages = db.Column(db.Integer, nullable=True)

    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    saved_by_users = db.relationship('SavedNote', backref='note', lazy=True, cascade="all, delete-orphan")
    viewed_by_users = db.relationship('ViewedNote', backref='note', lazy=True, cascade="all, delete-orphan")
    explanations = db.relationship('Explanation', backref='note', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Note {self.title}>"


class SavedNote(db.Model):
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id', ondelete='CASCADE'), nullable=False)

    def __repr__(self):
        return f"<SavedNote User {self.user_id} → Note {self.note_id}>"


class ViewedNote(db.Model):
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id', ondelete='CASCADE'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ViewedNote User {self.user_id} viewed Note {self.note_id} at {self.timestamp}>"


class StudyTip(db.Model):
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    tip_text = db.Column(db.Text, nullable=False)
    submitted_by = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f"<StudyTip #{self.id} by {self.submitted_by or 'Anonymous'}>"


class StickyNote(db.Model):
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    x = db.Column(db.Integer, default=100)
    y = db.Column(db.Integer, default=100)

    def __repr__(self):
        return f"<StickyNote #{self.id} at ({self.x}, {self.y})>"


class Explanation(db.Model):
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(200), nullable=False)
    explanation = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id', ondelete='CASCADE'), nullable=True)

    def __repr__(self):
        return f"<Explanation {self.topic}>"


class FeatureSuggestion(db.Model):
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    priority = db.Column(db.String(50))
    attachment = db.Column(db.String(300))
    username = db.Column(db.String(100))
    email = db.Column(db.String(100))
    status = db.Column(db.String(100), default='Under Review')
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<FeatureSuggestion {self.title} ({self.status})>"


class Feedback(db.Model):
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120))
    feedback_type = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    mood = db.Column(db.String(20))
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Feedback {self.feedback_type} - {self.name or 'Anonymous'}>"


class AKTU(db.Model):
    __tablename__ = 'aktu'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    session = db.Column(db.String(50), nullable=False)
    year = db.Column(db.String(20), nullable=False)
    file_url = db.Column(db.String(500), nullable=False)

    def __repr__(self):
        return f"<AKTU {self.title}>"


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    image_filename = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    answers = db.relationship('Answer', backref='question', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Question {self.topic}>"


class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    answer_text = db.Column(db.Text, nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Answer {self.id} for Question {self.question_id}>"
