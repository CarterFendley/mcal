import json
import os
from typing import List, Optional, Tuple

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash import ALL, MATCH, Input, Output, Patch, callback, dcc, html
from dash.exceptions import PreventUpdate
from plotly.subplots import make_subplots

from mcal.runner.models import load_run
from mcal.utils.format import bytes_units

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
PRESET_DIR = os.path.join(THIS_DIR, "../preset")
DASK_WORKER_DASHBOARD = os.path.join(PRESET_DIR, 'dask_worker.json')

# Incorporate data
run = load_run(os.environ["RUN_PATH"])

OPTIONS = []
for sampler, sampler_data in run.collected_data.items():
    OPTIONS.extend((
        f"{sampler}:{c}"
        for c in list(sampler_data.data.drop(columns="timestamp").columns)
    ))

dash.register_page(__name__)

def format_bytes(bytes: pd.Series) -> Tuple[pd.Series, str]:
    max_value = bytes.max()
    _, base, units = bytes_units(max_value)

    return bytes / base, units

ENTITY_MAPPING = {}
def simple_id_formatter(ids: pd.Series) -> pd.Series:
    global ENTITY_MAPPING
    for value in ids.unique():
        if value not in ENTITY_MAPPING:
            ENTITY_MAPPING[value] = f"Entity #{len(ENTITY_MAPPING)+1}"

    return ids.map(ENTITY_MAPPING)

FORMATTERS = {
    "bytes": format_bytes
}

def layout():
    dashboard_path = os.environ.get("DASHBOARD", DASK_WORKER_DASHBOARD)
    with open(dashboard_path, 'r') as f:
        graphs = json.load(f)

    return dbc.Container([
        html.Div(
            id="attribute-div"
        ),
        dbc.Row([
            dbc.Col(dbc.Button("+ Add", id="add-button", n_clicks=0), width=3),
            dbc.Col(
                dbc.Button(
                    "Get Parameters",
                    id="get-parameters",
                    disabled=True,
                    color='secondary'
                ),
                width=2
            )
        ], justify="between"),
        html.Div(id="alert-container"),
        dbc.Modal([
            dbc.Row([
                dbc.Col(dcc.Textarea(id="parameters", style=dict(height=300, width="100%")), width=11),
                dbc.Col(dcc.Clipboard(
                    target_id="parameters",
                    title="copy",
                    style={
                        "display": "inline-block",
                        "fontSize": 20,
                        "verticalAlign": "top",
                    },
                ), width=1),
            ])
        ], id="modal"),
        dcc.Graph(
            id="dynamic-graph"
        ),
        *(
            dcc.Graph(figure=create_graph(**kwargs)[0])
            for kwargs in graphs
        )
    ])

@callback(
    Output("attribute-div", "children"),
    Input("add-button", "n_clicks")
)
def add_dropdown(n_clicks: int):
    patched_children = Patch()
    patched_children.append(dbc.Row([
        dbc.Col([
            "Attribute:",
            dcc.Dropdown(id={"type": "attribute-select", "index": n_clicks})
        ]),
        dbc.Col([
            "Units Formatter:",
            dcc.Dropdown(
                id={"type": "units-formatter", "index": n_clicks},
                options=list(FORMATTERS.keys())
            )
        ], width=2)
    ]))

    return patched_children

@callback(
    Output({"type": "attribute-select", "index": MATCH}, "options"),
    Input({"type": "attribute-select", "index": MATCH}, "search_value")
)
def update_options(search_value):
    if not search_value:
        raise PreventUpdate

    return [o for o in OPTIONS if search_value in o]

@callback(
    Output("get-parameters", "disabled"),
    Input("parameters", "value")
)
def disable_get_parameters(value: Optional[str]) -> bool:
    return value is None

@callback(
    Output("modal", "is_open"),
    Input("get-parameters", "n_clicks"),
    prevent_initial_call=True
)
def toggle_modal(n: int):
    return True

@callback(
    Output("dynamic-graph", "figure"),
    Output("alert-container", "children"),
    Output("parameters", "value"),
    Input({"type": "attribute-select", "index": ALL}, "value"),
    Input({"type": "units-formatter", "index": ALL}, "value"),
    prevent_initial_call=True
)
def update_graph(values: Optional[str], formatters: Optional[str]):
    sampler_name = None
    attributes = []
    for value, formatter in zip(values, formatters):
        if value is None:
            raise PreventUpdate
        name, attribute = value.split(":")

        if sampler_name is not None and name != sampler_name:
            return (
                None,
                [dbc.Alert("Currently merging different samples in graphs is not supported. Please select two attributes from the same sample. ", color='danger')],
                None
            )

        sampler_name = name
        attributes.append((attribute, formatter))

    kwargs = {
        'sampler_name': sampler_name,
        'attributes': attributes
    }
    fig, alerts = create_graph(**kwargs)
    return fig, alerts, json.dumps(kwargs, indent=4)

def create_graph(
    sampler_name: str,
    attributes: list,
    title: Optional[str] = None
) -> Tuple[Optional[go.Figure], List[dbc.Alert]]:
    by_formatter = {}

    for attr, formatter in attributes:
        if formatter not in by_formatter:
            by_formatter[formatter] = []
        by_formatter[formatter].append(attr)

    if len(by_formatter) > 2:
        return None, [dbc.Alert("Currently only two formatters are supported.", color='danger')]

    sampler_data = run.collected_data[sampler_name]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    units = {}
    dash = {0: None, 1: "dash"}
    for i, (formatter, attrs) in enumerate(by_formatter.items()):
        for attr in attrs:
            attr_timeseries = sampler_data.raw_data[["id", "timestamp", attr]]
            attr_timeseries["id"] = simple_id_formatter(attr_timeseries["id"])

            if formatter is not None:
                attr_timeseries[attr], units[i] = FORMATTERS[formatter](
                    attr_timeseries[attr]
                )

            for id, timeseries in attr_timeseries.groupby("id"):
                fig.add_trace(
                    go.Scatter(
                        x=timeseries["timestamp"],
                        y=timeseries[attr],
                        name=f"{attr} ({id})",
                        line={'dash': dash[i]},
                        legendgroup=f"{i+1}"
                    ),
                    secondary_y=i != 0
                )

    for i, formatter in enumerate(by_formatter):
        secondary = i != 0
        if formatter is None:
            name = "value"
            ticksuffix = ""
        else:
            name = formatter
            ticksuffix = units[i]

        fig.update_yaxes(
            title_text=name,
            secondary_y=secondary
        )
        common = dict(
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.2,
                xanchor="center",
                x=0.5
            ),
            margin=dict(l=20, r=20, t=20, b=100)
        )
        if not secondary:
            fig.update_layout(
                yaxis={
                    'ticksuffix': ticksuffix
                },
                **common
            )
        else:
            fig.update_layout(
                yaxis2={
                    'ticksuffix': ticksuffix
                },
                **common
            )

    if title is not None:
        fig.update_layout(
            title_text=title
        )

    # Set x-axis title
    # fig.update_xaxes(title_text="xaxis title")

    return fig, []

# def create_graph(
#     sampler_name: str,
#     attribute: str,
#     formatter: Optional[str] = None
# ) -> Figure:
#     sampler_data = run.collected_data[sampler_name]
#     timeseries = sampler_data.raw_data[["id", "timestamp", attribute]]

#     if formatter is not None:
#         scaled, units = FORMATTERS[formatter](timeseries[attribute])
#         timeseries[attribute] = scaled
#     else:
#         units = ""

#     fig = px.line(
#         data_frame=timeseries,
#         x="timestamp",
#         y=attribute,
#         color="id",
#         title=attribute,
#     )
#     fig.update_layout(
#         yaxis={
#             'ticksuffix': units
#         }
#     )

#     return fig
