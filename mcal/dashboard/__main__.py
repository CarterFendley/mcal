# Import packages
import dash
import dash_bootstrap_components as dbc
from dash import Dash

# Initialize the app - incorporate a Dash Bootstrap theme
external_stylesheets = [dbc.themes.LUMEN]
app = Dash(__name__, use_pages=True, external_stylesheets=external_stylesheets)

# TODO: Must be a better way to make sure the 

# App layout
app.layout = dbc.Container([
    dbc.NavbarSimple(
        children = [
            dbc.NavItem(dbc.NavLink(page["name"], href=page["relative_path"]))
            for page in dash.page_registry.values()
        ],
        brand="Dashboard",
        style={"height": "10vh"}
    ),
    dbc.Container(
        dash.page_container,
        fluid=True,
        # class_name="h-50",
    )

], fluid=True)

# Run the app
if __name__ == '__main__':
    app.run(debug=True)