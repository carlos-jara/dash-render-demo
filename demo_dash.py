# Importar librerías
# ---------------------------------------------------------------
from dash import Dash, html, dcc, callback, Output, Input
import pandas as pd
import plotly.express as px
import geopandas as gpd
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# ---------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------
# Cargar geopackage
aysen = gpd.read_file("data/comunas_aysen.gpkg")
aysen = aysen.to_crs(epsg=4326) # para trabajar en lat long en este caso

# Cargar datos de población
df = pd.read_csv("data/pob_aysen2017.csv")

# Cargar etiquetas comunas
df_comunas = pd.read_csv("data/etiquetas_persona_comuna_16r.csv",sep=';')
df_comunas['glosa'] = df_comunas['glosa'].str.replace("’", "'", regex=False)
dict_comunas =   {glosa: valor for valor, glosa in  df_comunas[df_comunas['valor'].isin(df['COMUNA'].unique())].set_index('valor')['glosa'].items()}

# ---------------------------------------------------------------
# Listas requeridas para pirámide poblacional
# ---------------------------------------------------------------
age_range = np.arange(0,110,5) # Anotamos 105 ya que vimos que el límite llega a 100.
# Vamos a trabajar con numpy.histogram, está función utiliza bins de está manera [0,5), osea considera del 0 al 4, pero para el último dato considera [95,100]

# Podemos crear las etiquetas para el gráfico poblacional
labels = [f'{i}-{i+4}' for i in range(0, 100, 5)] + ["+100"]

# ---------------------------------------------------------------
# Procesamiento de datos mapa región
# ---------------------------------------------------------------
data_region = df.query('REGION == 11')[['COMUNA', 'P09']]
#data_region = df[['COMUNA', 'P09']]
data_region = data_region.groupby("COMUNA").count().reset_index()

data_region = pd.merge(data_region,df_comunas,left_on='COMUNA',right_on='valor', how='inner')

data_region['glosa'] = data_region['glosa'].str.replace("’", "'", regex=False)

# Merge con GeoDataFrame
aysen = aysen.merge(data_region, left_on='Comuna', right_on='glosa')

# Preparar GeoJSON
aysen = aysen.reset_index(drop=True)
aysen['id'] = aysen.index.astype(str)
geojson = aysen.__geo_interface__

# ---------------------------------------------------------------
# Gráfico mapa región
# ---------------------------------------------------------------
minx, miny, maxx, maxy = aysen.total_bounds

center = {
    "lon": (minx + maxx) / 2,
    "lat": (miny + maxy) / 2
}

fig_map = px.choropleth_map(aysen, geojson=geojson, locations="id", color="P09", color_continuous_scale="Blues", center=center, zoom=5.3, opacity=0.6, labels={"P09": "Población"})

fig_map.update_layout(
    title="Población de la Región de Aysén por comuna, 2017",
    #width=600,
    #height=500,
    margin={"r":0, "t":40, "l":0, "b":0}
)

# ---------------------------------------------------------------
# Aplicación Dash
# ---------------------------------------------------------------

# Inicializar app ##############################################
app = Dash()

# App layout ###################################################
app.layout = [
    html.Div([
        # Logo
        html.Img(src='/assets/logo.png', style={'height': '90px', 'object-fit': 'contain'}),
        # Title
        html.H2("Visualización de Datos", style={'margin-right': '20px', 'whiteSpace': 'nowrap'}),
        # Interactive items
        html.Div([
            # Dropdown menu
            html.Div([
                html.Label("Selecciona Comuna",style={"color":"white","font-family": "Arial", "font-size": "18px", "font-weight": "bold"}),
                dcc.Dropdown(options=list(dict_comunas.keys()),value='Coyhaique',id='controls-and-dropdown',clearable=False, style={'width': '180px'})
                ], style={'margin-right': '20px','color': 'black',}),
        ], style={'display': 'flex', 'alignItems': 'center'}),
        html.Div(children="Coyhaique",id="text") # Este div es para testear como se pueden modificar cualquier elemento con las funciones de callback
    ], style={'display': 'flex','alignItems': 'center','padding': '10px 20px','backgroundColor': '#2c3e50','color': 'white','flexWrap': 'nowrap','gap': '10px',"font-family": "Arial"}
    ),
    html.Div([
        # Grafico de pirámide poblacional
        html.Div([dcc.Graph(id="pyramid", style={'height': '80vh'})], style={'flex': '1', 'padding': '10px'}),
        # Mapa de la región
        html.Div([dcc.Graph(figure=fig_map,id="map", style={'height': '80vh'})], style={'flex': '1', 'padding': '10px'})
    ], style={
        'display': 'flex',
        'flexDirection': 'row'
    })
]

# Callbacks ###################################################
# Agregamos controles para construir la interacción
@callback(
    Output(component_id='pyramid', component_property='figure'), # modifica la figura del div con id pyramid
    Output(component_id='text', component_property='children'), # modifica el componente children del div con nombre text
    Input(component_id='controls-and-dropdown',component_property='value') # elemento de entrada de la función, el valor value de controls-and-dropdown
    #Input(component_id='controls-and-radio-item',component_property='value')
)
def update_graph(variable):
    comuna = dict_comunas[variable]
    data = df.query('COMUNA == @comuna')[['P08','P09']]
    data.columns = ['sexo','edad']
    # Ahora podemos filtrar datos por hombres y mujeres en la región de Aysén
    data_hombres = data.query('sexo == 1')['edad'].values # 1 hombre, 2 mujer
    data_mujeres = data.query('sexo == 2')['edad'].values # 1 hombre, 2 mujer
    # la función np.histogram nos cuenta el número de veces que un elemento se repite dentro de los rangos indicados
    hist_hombres, _ = np.histogram(data_hombres, bins=age_range)
    hist_mujeres, _ = np.histogram(data_mujeres, bins=age_range)
    # Crear Figura
    fig = go.Figure()
    # Agregar barras
    fig.add_trace(go.Bar(y=labels, x=-hist_hombres, name='Hombres', orientation='h', marker_color='steelblue'))
    fig.add_trace(go.Bar(y=labels, x=hist_mujeres, name='Mujeres', orientation='h', marker_color='lightcoral'))
    # Ajustes del layout
    fig.update_layout(
        autosize = False,
        #width=400, height=400,
        title=f'Pirámide poblacional comuna de {variable}',
        barmode='relative',
        xaxis=dict(title='Población', tickvals=[-100, -50, 0, 50, 100], ticktext=[100, 50, 0, 50, 100]),
        yaxis=dict(title='Edad'),
        bargap=0.1,
        plot_bgcolor='white'
    )

    return fig,variable # dos variables de retorno para los dos outputs

# Run the app ###################################################
if __name__ == '__main__':
    app.run(debug=True,port=8059)