import os
from flask import Flask, render_template, request, send_from_directory
from convert_inchi import inchi_to_smiles, inchi_sdf_visualize, inchi_to_xyz_visualize
from convert_smiles import smiles_to_inchi, smiles_sdf_visualize, smiles_to_xyz_visualize

app = Flask(__name__)

TEMP_DIR = "temp_files"
IMAGE_DIR = "static/images"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

ALLOWED_INPUT_TYPES = ["inchi", "smiles"]
ALLOWED_OUTPUT_TYPES = ["smiles", "inchi", "sdf", "xyz"]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    input_type = request.form['input_type']
    output_type = request.form['output_type']
    chemical_input = request.form['chemical_input']

    if input_type not in ALLOWED_INPUT_TYPES or output_type not in ALLOWED_OUTPUT_TYPES:
        return "Invalid input type or output type", 400

    output_file = None
    output_image_file = None
    output_text = None

    if input_type == "inchi":
        if output_type == "smiles":
            output_text = inchi_to_smiles(chemical_input)
        elif output_type == "sdf":
            output_file, output_image_file = inchi_sdf_visualize(chemical_input)
        elif output_type == "xyz":
            output_file, output_image_file = inchi_to_xyz_visualize(chemical_input)
    elif input_type == "smiles":
        if output_type == "inchi":
            output_text = smiles_to_inchi(chemical_input)
        elif output_type == "sdf":
            output_file, output_image_file = smiles_sdf_visualize(chemical_input)
        elif output_type == "xyz":
            output_file, output_image_file = smiles_to_xyz_visualize(chemical_input)

    return render_template('result.html', output_file=output_file, output_text=output_text, output_image_file=output_image_file)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory('temp_files', filename, as_attachment=True)


@app.route('/temp_files/<filename>')
def serve_image(filename):
    return send_from_directory('temp_files', filename)

if __name__ == '__main__':
    app.run(debug=True)