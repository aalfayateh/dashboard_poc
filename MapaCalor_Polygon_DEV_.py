# Import libraries
import pandas as pd
import folium
from folium.plugins import HeatMap, Draw
import json
from branca.element import Template, MacroElement
from shapely.geometry import Point, Polygon
import streamlit as st
import random
import string
from streamlit_folium import st_folium
import streamlit.components.v1 as components
import time

# Global variable to store polygon coordinates
coordenadas_poligono = None

# Event types mapping
eventos_traducidos = {
    5001: "Encendido",
    5002: "Apagado",
    5003: "Movimiento",
    5016: "Aceleración brusca",
    5017: "Deceleración brusca",
    5018: "Giro brusco",
    6001: "Exceso de velocidad",
    5006: "Remolcado",
    5009: "Avería",
    6128: "Proximidad ZBE",
    6125: "Entrada en ZBE",
    6127: "Parada en ZBE",
    6126: "Salida de ZBE",
    6012: "Carretera en mal estado",
    5020: "Impacto"
}

# Function to reset the app state automatically after download
def reset_app_state():
    st.session_state.clear()

# Function to generate a random file name
def generar_nombre_aleatorio(longitud=8):
    letras = string.ascii_letters + string.digits
    return ''.join(random.choice(letras) for _ in range(longitud))

# Function to load event data
def cargar_datos(archivo_json):
    return pd.DataFrame(archivo_json['rows'])

# Function to load polygon data
def cargar_poligono(archivo_poligono, radio_circulo_grados=0.01):
    try:
        coordinates = archivo_poligono['features'][0]['geometry']['coordinates']
        if archivo_poligono['features'][0]['geometry']['type'] == 'Polygon':
            return Polygon(coordinates[0])
        elif archivo_poligono['features'][0]['geometry']['type'] == 'Point':
            point = Point(coordinates)
            circle = point.buffer(radio_circulo_grados)
            return circle
        else:
            raise ValueError("Tipo de geometría no soportado")
    except KeyError as e:
        raise ValueError(f"Error al cargar el polígono: {e}")

# Function to validate event JSON
def validar_json_eventos(datos_eventos):
    try:
        pd.DataFrame(datos_eventos['rows'])
        return "Eventos cargados con éxito"
    except Exception as e:
        return f"✘ Error: {e}"

# Function to validate polygon JSON
def validar_json_poligono(datos_poligono, radio_circulo_grados=0.01):
    try:
        coordinates = datos_poligono['features'][0]['geometry']['coordinates']
        if datos_poligono['features'][0]['geometry']['type'] == 'Polygon':
            Polygon(coordinates[0])
        elif datos_poligono['features'][0]['geometry']['type'] == 'Point':
            point = Point(coordinates)
            circle = point.buffer(radio_circulo_grados)
            if not isinstance(circle, Polygon):
                raise ValueError("Error al convertir el punto en un polígono circular")
        else:
            raise ValueError("Tipo de geometría no soportado")
        return "Polígono cargado con éxito"
    except Exception as e:
        return f"✘ Error: {e}"

# Legend creation function
def agregar_leyenda(mapa, conteo_eventos, fecha_inicio, fecha_fin, hora_inicio, hora_fin):
    info_fechas_horas = f'''
        <b>Rango de Fechas:</b> {fecha_inicio.strftime('%d.%m.%Y')} - {fecha_fin.strftime('%d.%m.%Y')}<br>
        <b>Rango de Horas:</b> {hora_inicio}:00 - {hora_fin}:00<br><br>
    '''
    eventos_html = ''.join([f'<li>{descripcion}: {conteo}</li>' for descripcion, conteo in conteo_eventos.items() if conteo > 0])
    template = '''
    {% macro html(this, args) %}
    <div style="position: absolute; top: 350px; right: 10px; width: 300px; height: auto; border:2px solid grey; background: white; z-index:9998; font-size:14px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);">
        <div style="background: #f9f9f9; padding: 10px; font-size: 12px; border-radius: 10px;">
            <ul style="list-style-type: none; padding: 0; margin: 0;">
            ''' + info_fechas_horas + '''
            </ul>
            <b>Intensidad del Evento</b>
            <br>
            <div style="width: 100%; height: 20px; background: linear-gradient(to right, green, yellow, orange, red, darkred);"></div>
            <div style="display: flex; justify-content: space-between; width: 100%; font-size: 12px; margin-top: 5px;">
                <div>Muy baja</div>
                <div>Baja</div>
                <div>Media</div>
                <div>Alta</div>
                <div>Muy Alta</div>
            </div>
            <br>
            <b>Total de Eventos</b>
            <ul style="list-style-type: none; padding: 0; margin: 0;">
                ''' + eventos_html + '''
            </ul>
        </div>
    </div>
    {% endmacro %}
    '''
    legend = MacroElement()
    legend._template = Template(template)
    mapa.get_root().add_child(legend)

# Function to export the map
def exportar_mapa(mapa, nombre_archivo):
    mapa.save(nombre_archivo)

# Function to generate the heatmap with layers and progress bar
def generar_mapa_con_progreso(data, fecha_inicio, fecha_fin, hora_inicio, hora_fin, precision, poligono=None):
    progress_bar = st.progress(0)  # Initialize progress bar
    try:
        progress_bar.progress(10)  # Step 1: Loading initial data

        zoom_start = 0
        data['Fecha'] = pd.to_datetime(data['Fecha'], unit='ms')
        fecha_inicio = pd.to_datetime(fecha_inicio)
        fecha_fin = pd.to_datetime(fecha_fin)

        data = data[(data['Fecha'] >= fecha_inicio) & (data['Fecha'] <= fecha_fin)]
        data = data[(data['Fecha'].dt.hour >= hora_inicio) & (data['Fecha'].dt.hour <= hora_fin)]
        progress_bar.progress(25)  # Step 2: Data filtered by date and time

        conteo_eventos = {}
        if poligono is not None:
            puntos = [Point(lon, lat) for lat, lon in zip(data['Latitud'], data['Longitud'])]
            data = data[[poligono.contains(punto) for punto in puntos]]
        progress_bar.progress(50)  # Step 3: Filtered by polygon

        if not data.empty:
            centro_lat = data['Latitud'].mean()
            centro_lon = data['Longitud'].mean()
            zoom_start = 12
        else:
            centro_lat = 40.3453  # Default lat
            centro_lon = -3.6604  # Default lon
            zoom_start = 6
        progress_bar.progress(60)  # Step 4: Map center calculated

        mapa = folium.Map(location=[centro_lat, centro_lon], zoom_start=zoom_start)
        capa_evento = folium.FeatureGroup(name="Eventos")

        precision_values = {
            'Baja': (15, 15),
            'Media': (10, 10),
            'Alta': (3, 3)
        }
        radius, blur = precision_values.get(precision, (10, 10))

        if 'TipoEvento' in data.columns and not data.empty:
            data = data[data['TipoEvento'].isin(eventos_traducidos.keys())]
            gradient = {0: 'lightgreen', 0.25: 'yellow', 0.5: 'orange', 0.75: 'red', 1: 'darkred'}
            max_densidad = data.shape[0]

            for tipo_evento, descripcion in eventos_traducidos.items():
                datos_filtrados = data[data['TipoEvento'] == tipo_evento]
                conteo_eventos[descripcion] = len(datos_filtrados)
                heat_data = [[row['Latitud'], row['Longitud'], 1] for _, row in datos_filtrados.iterrows()]
                if heat_data:
                    capa_evento = folium.FeatureGroup(name=descripcion)
                    HeatMap(
                        heat_data, 
                        min_opacity=0.3, 
                        radius=radius, 
                        blur=blur, 
                        gradient=gradient, 
                        max_zoom=18,
                        max_value=max_densidad
                    ).add_to(capa_evento)
                    capa_evento.add_to(mapa)
        progress_bar.progress(85)  # Step 5: Added heatmap layers

        # Add draw tool and legend
        folium.LayerControl().add_to(mapa)
        draw = Draw(export=True)
        draw.add_to(mapa)
        agregar_leyenda(mapa, conteo_eventos, fecha_inicio, fecha_fin, hora_inicio, hora_fin)
        progress_bar.progress(100)  # Step 6: Final touches

        archivo_salida = f"Mapa_Calor_Polygon_{generar_nombre_aleatorio()}.html"
        return mapa, archivo_salida, conteo_eventos

    except Exception as e:
        st.error(f"Error al generar el mapa: {e}")
        return None, None, None


# Streamlit configuration
st.set_page_config(layout="wide")
st.title("Aplicación de Mapa de Calor de Eventos")
datos_eventos = None
poligono = None

# Flag to check if the map was generated by clicking the button
mapa_generado_con_boton = False

# Load event and polygon files before generating the map
col1, col2 = st.columns(2)

with col1:
    uploaded_file_eventos = st.file_uploader("Sube tu archivo JSON de eventos", type=["json"], key="file_eventos")
    if uploaded_file_eventos is not None:
        try:
            datos_eventos = json.load(uploaded_file_eventos)
            validacion_eventos = validar_json_eventos(datos_eventos)
            st.success(validacion_eventos)
        except Exception as e:
            st.error(f"Error al cargar el archivo de eventos: {e}")

with col2:
    uploaded_file_poligono = st.file_uploader("Sube tu archivo JSON de polígono (opcional)", type=["geojson"], key="file_poligono")
    if uploaded_file_poligono is not None:
        try:
            datos_poligono = json.load(uploaded_file_poligono)
            validacion_poligono = validar_json_poligono(datos_poligono)
            st.success(validacion_poligono)
            poligono = cargar_poligono(datos_poligono)
        except Exception as e:
            st.error(f"Error al cargar el archivo de polígono: {e}")

# Configuration settings for date, time, and precision
col1, col2 = st.columns(2)

with col1:
    fecha_inicio = st.date_input("Fecha de inicio")
    hora_inicio = st.number_input("Hora de inicio (0-24)", min_value=0, max_value=23, value=0)
    precision = st.selectbox("Precisión", options=['Alta', 'Media', 'Baja'])

with col2:
    fecha_fin = st.date_input("Fecha de fin")
    hora_fin = st.number_input("Hora de fin (0-23)", min_value=0, max_value=23, value=23)

# Generate map button
if st.button("Generar Mapa", key="generar_mapa"):
    try:
        if datos_eventos is not None:
            eventos_df = cargar_datos(datos_eventos)
            mapa, archivo_salida, conteo_eventos = generar_mapa_con_progreso(eventos_df, fecha_inicio, fecha_fin, hora_inicio, hora_fin, precision, poligono)

            # Show the map only the first time when generating, not after export
            map_container = st.empty()
            if not st.session_state.get('export_successful', False):  # Only show the map if it's not exported yet
                with map_container:
                    components.html(mapa._repr_html_(), height=800)

            # Store map and relevant data in session state
            st.session_state['map_generated'] = True
            st.session_state['mapa'] = mapa
            st.session_state['archivo_salida'] = archivo_salida
            st.session_state['conteo_eventos'] = conteo_eventos
        else:
            st.error("Por favor, sube un archivo JSON de eventos válido.")
    except Exception as e:
        st.error(f"Error: {e}")

# Check if the export button should be enabled based on the presence of events in the map
exportar_button_enabled = False
if 'conteo_eventos' in st.session_state and any(st.session_state['conteo_eventos'].values()):
    exportar_button_enabled = True

# Show the export map button if the map is generated and contains events
if 'map_generated' in st.session_state and st.session_state['map_generated']:
    if exportar_button_enabled:
        if st.button("Exportar Mapa", key="exportar_mapa"):
            with st.spinner("Exportando mapa..."):
                st.session_state['mapa'].save(st.session_state['archivo_salida'])
                exportar_mapa(st.session_state['mapa'], st.session_state['archivo_salida'])

                with open(st.session_state['archivo_salida'], "r") as f:
                    st.download_button("Descargar Mapa", data=f, file_name=st.session_state['archivo_salida'], mime="text/html")

                # Disable the export button and show success message
                st.success("Export generado con éxito. Puedes descargar el mapa.")
                st.session_state['map_generated'] = False
                st.session_state['export_successful'] = True
    else:
        st.button("Exportar Mapa", key="exportar_mapa", disabled=True, help="No hay eventos que exportar en el mapa")

# Automatically reset app state after downloading the map
if 'export_successful' in st.session_state and st.session_state['export_successful']:
    time.sleep(2)  # Delay to allow user to see success message before reset
    reset_app_state()
