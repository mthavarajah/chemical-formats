import os
from flask import Flask, render_template, request, send_from_directory
from convert_inchi import inchi_to_inchi, inchi_to_smiles, inchi_sdf_visualize, inchi_to_xyz_visualize
from convert_smiles import smiles_to_smiles, smiles_to_inchi, smiles_sdf_visualize, smiles_to_xyz_visualize

app = Flask(__name__)

TEMP_DIR = "temp_files"
IMAGE_DIR = "static/images"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

ALLOWED_INPUT_TYPES = ["InChi", "SMILES"]
ALLOWED_OUTPUT_TYPES = ["SMILES", "InChi", "SDF", "XYZ"]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    input_types = request.form.getlist('input_type')
    output_types = request.form.getlist('output_type')
    chemical_inputs = request.form.getlist('chemical_input')

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
    return send_from_directory('temp_files', filename, as_attachment=True)

@app.route('/temp_files/<filename>')
def serve_image(filename):
    return send_from_directory('temp_files', filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)