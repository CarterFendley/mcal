import os
from typing import Optional

import dash
import dash_bootstrap_components as dbc
from dash import html

from mcal.runner.models import load_run

# Incorporate data
run = load_run(os.environ["RUN_PATH"])

dash.register_page(__name__, order=0)

def attribute_table(sampler: str) -> dbc.Table:
    dtypes_df = run.collected_data[sampler].data.dtypes
    dtypes_df = dtypes_df.to_frame()

    dtypes_df = dtypes_df.rename(columns={0: 'dtype'})
    dtypes_df = dtypes_df.reset_index().rename(columns={'index': 'attribute'})

    dtypes_df['dtype'] = dtypes_df['dtype'].apply(lambda dtype: f"{dtype}")

    table: dbc.Table = dbc.Table.from_dataframe(
        df=dtypes_df,
        hover=True
    )

    # Hack hrefs in there
    for child in table.children:
        if not isinstance(child, html.Tbody):
            # Skip the head
            continue
        for row in child.children:
            if False:
                # This code gets the href property to show up, but still not clickable
                row._prop_names.append("href")
                row.href = f"?sampler={sampler}&attr={row.children[0].children}"

            # This code is okay-ish, a little buggy
            for td in row.children:
                td.children = html.A(
                    children=td.children,
                    href=f"?sampler={sampler}&attr={row.children[0].children}",
                    style={
                        "display": "block",
                        "color": "inherit",
                        "text-decoration": "none",
                    }
                )
            # row.to_plotly_json()
    return table

def attr_info(sampler: str, attribute: Optional[str]) -> dbc.Card:
    if attribute is None:
        title = html.H3("Attribute Info")
        contents = html.H5("<Select an attribute>")
    else:
        title = html.H3(f"Attribute Info - {attribute}")
        contents = []

        data = run.collected_data[sampler].data[attribute]
        describe_df = data.describe().to_frame()
        describe_df = describe_df.rename(columns={attribute: 'value'})
        describe_df = describe_df.reset_index().rename(columns={'index': 'metric'})

        contents.extend((
            html.H6("describe:"),
            dbc.Table.from_dataframe(df=describe_df)
        ))

    return [
        title,
        dbc.Card(
            dbc.CardBody(children=contents)
        )
    ]


def layout(sampler=None, attr=None, **other_unknown_query_strings):
    print(attr)
    if sampler is not None:
        selected_sampler = sampler
    else:
        selected_sampler = run.config.samplers[0].kind

    return dbc.Container(
        dbc.Row([
            dbc.Col(
                children=[
                html.H3("Samplers"),
                dbc.ListGroup([
                    dbc.ListGroupItem(
                        sampler.kind,
                        href=f"?sampler={sampler.kind}",
                        action=True,
                        color='primary' if sampler.kind == selected_sampler else None
                    )
                    for sampler in run.config.samplers
                ])],
                width=3,
            ),
            dbc.Col(
                children=[
                    html.H3(f"Attributes - {selected_sampler}", style={"height": "5%"}),
                    html.Div(
                        attribute_table(selected_sampler),
                        style={"max-height": "95%", "overflow": "scroll"}
                    )
                ],
                width=6,
                style={"height": "100%"}
            ),
            dbc.Col(
                attr_info(sampler, attr),
                width=3
            )
        ], style={"height": "100%"}),
        # TODO: This is based on the nav bar height
        style={"height": "90vh", "width": "90vw"},
    )