from rdkit import Chem
from rdkit.Chem import Descriptors
import plotly.graph_objs as go
import os

def compute_lipinski(chemical_input, input_type):
    try:
        if input_type == "SMILES":
            mol = Chem.MolFromSmiles(chemical_input)
        elif input_type == "InChi":
            mol = Chem.MolFromInchi(chemical_input)
        else:
            return None
        if mol is None:
            return None
        return {
            "input": chemical_input,
            "MW": Descriptors.MolWt(mol),
            "logP": Descriptors.MolLogP(mol),
            "HDonors": Descriptors.NumHDonors(mol),
            "HAcceptors": Descriptors.NumHAcceptors(mol),
            "RotBonds": Descriptors.NumRotatableBonds(mol),
        }
    except Exception:
        return None

def create_lipinski_plot(data, output_path):
    if not data:
        return

    trace = go.Scatter(
        x=[d["MW"] for d in data],
        y=[d["logP"] for d in data],
        mode='markers',
        text=[d["input"] for d in data],
        marker=dict(size=12, color='black'),
        hovertemplate=(
            "Input: %{text}<br>" +
            "Molecular Weight: %{x}<br>" +
            "LogP: %{y}<extra></extra>"
        ),
        hoverlabel=dict(
            bgcolor="black",
            font_size=14,
            font_family="Arial",
            font_color="white"
        )
    )

    layout = go.Layout(
        title="Lipinski Scatter Plot (Molecular Weight vs LogP)",
        xaxis=dict(title="Molecular Weight"),
        yaxis=dict(title="LogP"),
        plot_bgcolor='#eeeeee',

    )

    fig = go.Figure(data=[trace], layout=layout)

    fig_html = fig.to_html(full_html=False)

    with open(output_path, 'w') as f:
        f.write('<div id="lipinski-plot">\n')
        f.write(fig_html)

def process_lipinski_inputs(input_list, output_dir="temp_files", filename="lipinski_plot.html"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    lipinski_data = []
    for input_type, chemical_input in input_list:
        props = compute_lipinski(chemical_input, input_type)
        if props:
            lipinski_data.append(props)

    output_path = os.path.join(output_dir, filename)
    create_lipinski_plot(lipinski_data, output_path)
    return filename