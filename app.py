import os
from flask import Flask, render_template, request, send_from_directory, session, redirect, url_for, flash
from convert_inchi import inchi_to_inchi, inchi_to_smiles, inchi_sdf_visualize, inchi_to_xyz_visualize
from convert_smiles import smiles_to_smiles, smiles_to_inchi, smiles_sdf_visualize, smiles_to_xyz_visualize
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, login_required, logout_user, current_user, LoginManager
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'mysecretkey'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

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

TEMP_DIR = "temp_files"
IMAGE_DIR = "static/images"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

ALLOWED_INPUT_TYPES = ["InChi", "SMILES"]
ALLOWED_OUTPUT_TYPES = ["SMILES", "InChi", "SDF", "XYZ"]

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.lower()).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('dashboard'))
            else:
                flash("Incorrect username or password.", "error")
        else:
            flash("Incorrect username or password.", "error")
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        try:
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            new_user = User(name=form.name.data,
                            username=form.username.data.lower(),
                            password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash("An error occurred during registration. Please try again.", "error")
    elif request.method == 'POST':
        flash("Please fix the errors in the form.", "error")
    return render_template('register.html', form=form)


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/convert', methods=['POST'])
def convert():
    input_types = request.form.getlist('input_type[]')
    output_types = request.form.getlist('output_type[]')
    chemical_inputs = request.form.getlist('chemical_input[]')

    results = []

    for input_type, chemical_input, output_type in zip(input_types, chemical_inputs, output_types):
        if input_type not in ALLOWED_INPUT_TYPES or output_type not in ALLOWED_OUTPUT_TYPES:
            return "Invalid input type or output type", 400

        output_file = None
        output_image_file = None
        output_text = None
        html_3d = None

        if input_type == "InChi":
            if output_type == "InChi":
                output_text, output_file = inchi_to_inchi(chemical_input)
            elif output_type == "SMILES":
                output_text, output_file = inchi_to_smiles(chemical_input)
            elif output_type == "SDF":
                output_file, output_image_file, html_3d = inchi_sdf_visualize(chemical_input)
            elif output_type == "XYZ":
                output_file, output_image_file, html_3d = inchi_to_xyz_visualize(chemical_input)
        elif input_type == "SMILES":
            if output_type == "SMILES":
                output_text, output_file = smiles_to_smiles(chemical_input)
            elif output_type == "InChi":
                output_text, output_file = smiles_to_inchi(chemical_input)
            elif output_type == "SDF":
                output_file, output_image_file, html_3d = smiles_sdf_visualize(chemical_input)
            elif output_type == "XYZ":
                output_file, output_image_file, html_3d = smiles_to_xyz_visualize(chemical_input)

        results.append({
            'input_type': input_type,
            'chemical_input': chemical_input,
            'output_type': output_type,
            'output_text': output_text,
            'output_file': os.path.basename(output_file) if output_file else None,
            'output_image_file': os.path.basename(output_image_file) if output_image_file else None,
            'html_3d': html_3d
        })

    return render_template('result.html', results=results)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(TEMP_DIR, filename, as_attachment=True)

@app.route('/temp_files/<filename>')
def serve_image(filename):
    return send_from_directory(TEMP_DIR, filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
