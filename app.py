import os
import base64
from dotenv import load_dotenv
from flask import Flask, render_template, request, send_from_directory, session, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
from flask_login import login_user, login_required, logout_user, current_user, LoginManager
from flask_bcrypt import Bcrypt
from convert_inchi import inchi_to_inchi, inchi_to_smiles, inchi_sdf_visualize, inchi_to_xyz_visualize
from convert_smiles import smiles_to_smiles, smiles_to_inchi, smiles_sdf_visualize, smiles_to_xyz_visualize
from lipinski_plot import process_lipinski_inputs
from models import db, User, SavedConversion, RegisterForm, LoginForm

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')
SECRET_KEY = os.getenv('SECRET_KEY')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SECRET_KEY'] = SECRET_KEY

db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

TEMP_DIR = "temp_files"
IMAGE_DIR = "static/images"
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

ALLOWED_INPUT_TYPES = ["InChi", "SMILES"]
ALLOWED_OUTPUT_TYPES = ["SMILES", "InChi", "SDF", "XYZ"]

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.lower()).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash("Incorrect username or password.", "error")
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        try:
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            new_user = User(
                name=form.name.data,
                username=form.username.data.lower(),
                password=hashed_password
            )
            db.session.add(new_user)
            db.session.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
        except Exception:
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

def capitalize_words(name):
    return ' '.join(word.capitalize() for word in name.strip().split())

@app.route('/dashboard')
@login_required
def dashboard():
    full_name = capitalize_words(current_user.name)
    return render_template('dashboard.html', full_name=full_name)

@app.route('/convert', methods=['POST'])
def convert():
    input_types = request.form.getlist('input_type[]')
    output_types = request.form.getlist('output_type[]')
    chemical_inputs = request.form.getlist('chemical_input[]')

    results = []
    lipinski_input_list = []

    for input_type, chemical_input, output_type in zip(input_types, chemical_inputs, output_types):
        if input_type not in ALLOWED_INPUT_TYPES or output_type not in ALLOWED_OUTPUT_TYPES:
            return "Invalid input type or output type", 400

        output_file = None
        output_image_file = None
        output_text = None
        html_3d = None

        if input_type in ["SMILES", "InChi"]:
            lipinski_input_list.append((input_type, chemical_input))

        try:
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
        except Exception:
            output_text = "N/A"

        results.append({
            'input_type': input_type,
            'chemical_input': chemical_input,
            'output_type': output_type,
            'output_text': output_text,
            'output_file': os.path.basename(output_file) if output_file else None,
            'output_image_file': os.path.basename(output_image_file) if output_image_file else None,
            'html_3d': html_3d
        })

    lipinski_plot_file = process_lipinski_inputs(lipinski_input_list)

    return render_template('result.html', results=results, lipinski_plot_file=lipinski_plot_file)

@app.route('/save_conversions', methods=['POST'])
@login_required
def save_conversions():
    selected_indices = request.form.getlist('selected_rows')
    for idx in selected_indices:
        new_conversion = SavedConversion(
            user_id=current_user.id,
            input_type=request.form.get(f'input_type_{idx}'),
            chemical_input=request.form.get(f'chemical_input_{idx}'),
            output_type=request.form.get(f'output_type_{idx}'),
            output_text=request.form.get(f'output_text_{idx}'),
            output_file=request.form.get(f'output_file_{idx}')
        )
        db.session.add(new_conversion)
    db.session.commit()
    flash("Selected conversions saved!", "success")
    return redirect(url_for('dashboard'))

@app.route('/saved_conversions')
@login_required
def saved_conversions():
    conversions = SavedConversion.query.filter_by(user_id=current_user.id).all()
    for row in conversions:
        row.image_2d = None
        row.html_3d = None
        if row.output_type in ['SDF', 'XYZ']:
            if row.input_type == 'InChI':
                _, image_file, html_3d = inchi_sdf_visualize(row.chemical_input)
            elif row.input_type == 'SMILES':
                _, image_file, html_3d = smiles_sdf_visualize(row.chemical_input)
            else:
                image_file, html_3d = None, None

            if image_file:
                with open(image_file, "rb") as img_f:
                    encoded_str = base64.b64encode(img_f.read()).decode('utf-8')
                row.image_2d = encoded_str
            row.html_3d = html_3d
    return render_template('saved_conversions.html', conversions=conversions)

@app.route('/delete_saved_conversions', methods=['POST'])
@login_required
def delete_saved_conversions():
    delete_ids = request.form.getlist('delete_ids')
    if delete_ids:
        SavedConversion.query.filter(
            SavedConversion.user_id == current_user.id,
            SavedConversion.id.in_(delete_ids)
        ).delete(synchronize_session=False)
        db.session.commit()
        flash(f"Deleted {len(delete_ids)} conversion(s).", "success")
    else:
        flash("No conversions selected for deletion.", "warning")
    return redirect(url_for('saved_conversions'))

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(TEMP_DIR, filename, as_attachment=True)

@app.route('/temp_files/<filename>')
def serve_image(filename):
    return send_from_directory(TEMP_DIR, filename)

@app.route('/lipinski_plot')
def serve_lipinski_plot():
    return send_from_directory('temp_files', 'lipinski_plot.html')

@app.route('/upload_profile_image', methods=['POST'])
@login_required
def upload_profile_image():
    file = request.files.get('profile_image')
    if file:
        filename = secure_filename(file.filename)
        path = os.path.join('static', 'uploads', filename)
        file.save(path)
        current_user.profile_image = f'uploads/{filename}'
        db.session.commit()
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/delete_profile_image', methods=['POST'])
@login_required
def delete_profile_image():
    current_user.profile_image = 'images/sample.png'
    db.session.commit()
    return redirect(request.referrer or url_for('dashboard'))

@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({"error": "Internal Server Error. Please try again later."}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)