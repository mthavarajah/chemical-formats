from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    profile_image = db.Column(db.String(255), default="static/css/images/sample.png")

class SavedConversion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    input_type = db.Column(db.String(50))
    chemical_input = db.Column(db.Text)
    output_type = db.Column(db.String(50))
    output_text = db.Column(db.Text)
    output_file = db.Column(db.String(255))

class RegisterForm(FlaskForm):
    name = StringField(validators=[InputRequired(), Length(min=1, max=150)],
                       render_kw={"placeholder": "Full Name"})
    username = StringField(validators=[InputRequired(), Length(min=4, max=150)], 
                           render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=150)], 
                             render_kw={"placeholder": "Password"})
    submit = SubmitField('Register', render_kw={'class': 'btn'})

    def validate_username(self, username):
        existing_user = User.query.filter_by(username=username.data.lower()).first()
        if existing_user:
            raise ValidationError('Username already exists.')

class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=150)],
                           render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=150)], 
                           render_kw={"placeholder": "Password"})
    submit = SubmitField('Login', render_kw={'class': 'btn'})