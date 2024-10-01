import pandas as pd
import folium
from folium.plugins import HeatMap, Draw
import json
from branca.element import Template, MacroElement
from shapely.geometry import Point, Polygon
import streamlit as st
import string
import random
from streamlit_folium import st_folium
import streamlit.components.v1 as components

# Variable global para almacenar las coordenadas del polígono
coordenadas_poligono = None

# Mapeo de TipoEvento a su descripción
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

# Función para capturar coordenadas del polígono
def capturar_coordenadas_poligono(geo_json):
    global coordenadas_poligono
    try:
        data = json.loads(geo_json)
        coordenadas_poligono = data['features'][0]['geometry']['coordinates']
        st.success(f"Coordenadas del polígono capturadas: {coordenadas_poligono}")
    except Exception as e:
        st.error(f"Error al capturar las coordenadas: {e}")

def generar_nombre_aleatorio(longitud=8):
    letras = string.ascii_letters + string.digits
    return ''.join(random.choice(letras) for _ in range(longitud))

# Funciones de carga de datos
def cargar_datos(archivo_json):
    return pd.DataFrame(archivo_json['rows'])  # Leer desde el JSON directamente

def cargar_poligono(archivo_poligono, radio_circulo_grados=0.01):
    try:
        # Extraer las coordenadas del primer feature
        coordinates = archivo_poligono['features'][0]['geometry']['coordinates']
        
        # Verificar si las coordenadas son de un polígono o un punto
        if archivo_poligono['features'][0]['geometry']['type'] == 'Polygon':
            return Polygon(coordinates[0])
        elif archivo_poligono['features'][0]['geometry']['type'] == 'Point':
            # Convertir el punto en un polígono circular usando el radio proporcionado
            point = Point(coordinates)
            circle = point.buffer(radio_circulo_grados)
            return circle
        else:
            raise ValueError("Geometry type not supported")
    except KeyError as e:
        raise ValueError(f"Error loading polygon: {e}")



# Función para validar el archivo JSON de eventos
def validar_json_eventos(datos_eventos):
    try:
        pd.DataFrame(datos_eventos['rows'])  # Convertir a DataFrame para validar
        return "Events loaded"
    except Exception as e:
        return f"✘ Error: {e}"

def validar_json_poligono(datos_poligono, radio_circulo_grados=0.01):
    try:
        # Extraer las coordenadas del primer feature
        coordinates = datos_poligono['features'][0]['geometry']['coordinates']
        
        # Verificar si las coordenadas son de un polígono o un punto
        if datos_poligono['features'][0]['geometry']['type'] == 'Polygon':
            Polygon(coordinates[0])  # Validar el polígono
        elif datos_poligono['features'][0]['geometry']['type'] == 'Point':
            # Convertir el punto en un polígono circular para validación usando el radio proporcionado
            point = Point(coordinates)
            circle = point.buffer(radio_circulo_grados)
            if not isinstance(circle, Polygon):
                raise ValueError("Error converting polygon into circular area")
        else:
            raise ValueError("Geometry type not supported")
        
        return "Polígono cargado con éxito"
    except Exception as e:
        return f"✘ Error: {e}"



# Función para crear la leyenda 
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
                <div>Very Low</div>
                <div>Low</div>
                <div>Medium</div>
                <div>High</div>
                <div>Very High</div>
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

# Función para exportar el mapa a un archivo HTML
def exportar_mapa(mapa, nombre_archivo):
    mapa.save(nombre_archivo)

# Función para generar el mapa de calor - aqui se añaden las capas
def generar_mapa_con_capas(data, fecha_inicio, fecha_fin, hora_inicio, hora_fin, precision, poligono=None):

    # Filtrar los eventos por fecha y hora
    data['Fecha'] = pd.to_datetime(data['Fecha'], unit='ms')
    fecha_inicio = pd.to_datetime(fecha_inicio)
    fecha_fin = pd.to_datetime(fecha_fin)
    data = data[(data['Fecha'] >= fecha_inicio) & (data['Fecha'] <= fecha_fin)]
    data = data[(data['Fecha'].dt.hour >= hora_inicio) & (data['Fecha'].dt.hour <= hora_fin)]

    conteo_eventos = {}  # Inicializar conteo_eventos

    # Filtrar los eventos por el polígono si se proporciona
    if poligono is not None:
        puntos = [Point(lon, lat) for lat, lon in zip(data['Latitud'], data['Longitud'])]
        data = data[[poligono.contains(punto) for punto in puntos]]

    # Crear un mapa centrado en Santa Cruz de Mudela o donde queramos - mas adelante, intentar que coja el centro los eventos
    mapa = folium.Map(location=[38.2016424,-1.3441754], zoom_start=12)

    # Inicializar la capa_evento
    capa_evento = folium.FeatureGroup(name="Eventos")

    # Asignar valores de precisión
    precision_values = {
        'Low': (15, 15),
        'Medium': (10, 10),
        'High': (3, 3)
    }
    
    radius, blur = precision_values.get(precision, (10, 10))  # Valor por defecto

    # Verificar si la columna 'TipoEvento' existe antes de filtrar
    if 'TipoEvento' in data.columns and not data.empty:
        # Filtrar los eventos que tienen traducción en nuestro diccionario
        data = data[data['TipoEvento'].isin(eventos_traducidos.keys())]

        # Crear un gradiente dinámico basado en los eventos seleccionados
        gradient = {0: 'lightgreen', 0.25: 'yellow', 0.5: 'orange', 0.75: 'red', 1: 'darkred'}

        # Calcular la densidad máxima de eventos para ajustar el gradiente
        max_densidad = data.shape[0]

        # Crear una capa para cada tipo de evento
        for tipo_evento, descripcion in eventos_traducidos.items():
            # Filtrar los datos por el tipo de evento
            datos_filtrados = data[data['TipoEvento'] == tipo_evento]
            conteo_eventos[descripcion] = len(datos_filtrados)

            # Crear los datos para el mapa de calor de este tipo de evento
            heat_data = [[row['Latitud'], row['Longitud'], 1] for _, row in datos_filtrados.iterrows()]

            if heat_data:  # Solo añadir la capa si hay datos
                capa_evento = folium.FeatureGroup(name=descripcion)
                HeatMap(
                    heat_data, 
                    min_opacity=0.3, 
                    radius=radius,  # Usar el valor del radio según la precisión seleccionada
                    blur=blur,  # Usar el valor del blur según la precisión seleccionada
                    gradient=gradient,  # Usar el gradiente dinámico
                    max_zoom=18,
                    max_value=max_densidad  # Ajustar el valor máximo al valor de densidad real
                ).add_to(capa_evento)
                capa_evento.add_to(mapa)
    else:
        print("No events to be shown.")

    # Agregar el control de capas al mapa para selección dinámica
    folium.LayerControl().add_to(mapa)

    # Agregar herramienta de dibujo
    draw = Draw(export=True)
    draw.add_to(mapa)

    # Agregar leyenda
    agregar_leyenda(mapa, conteo_eventos, fecha_inicio, fecha_fin, hora_inicio, hora_fin)

    archivo_salida = f"C:\\Users\\dmurias\\Desktop\\Telefonica\\SCRIPTS3\\workspace\\Mapas de Calor\\ficheros\\Mapa_Calor_Polygon_{generar_nombre_aleatorio()}.html"
    # Mostrar el mapa
    return mapa, archivo_salida

# Interfaz de Streamlit
st.title("Events Density Maps Application")

# Carga de archivos
uploaded_file_eventos = st.file_uploader("Upload events JSON file", type=["json"])
uploaded_file_poligono = st.file_uploader("Upload polygon JSON (optional)", type=["geojson"])

# Inicializar las variables
datos_eventos = None
poligono = None

if uploaded_file_eventos is not None:
    try:
        datos_eventos = json.load(uploaded_file_eventos)  # Leer el JSON
        validacion_eventos = validar_json_eventos(datos_eventos)  # Validar eventos
        st.success(validacion_eventos)
    except Exception as e:
        st.error(f"Error loading events file: {e}")

if uploaded_file_poligono is not None:
    try:
        datos_poligono = json.load(uploaded_file_poligono)  # Leer el JSON
        validacion_poligono = validar_json_poligono(datos_poligono)  # Validar polígono
        st.success(validacion_poligono)
        poligono = cargar_poligono(datos_poligono)  # Cargar el polígono
        print(poligono)
    except Exception as e:
        st.error(f"Error loading polygon file: {e}")

# Parámetros de configuración
col1, col2 = st.columns(2)

with col1:
    fecha_inicio = st.date_input("Start date")
    hora_inicio = st.number_input("Start hour (0-24)", min_value=0, max_value=23, value=0)

with col2:
    fecha_fin = st.date_input("End date")
    hora_fin = st.number_input("End hour (0-23)", min_value=0, max_value=23, value=23)

precision = st.selectbox("Precision", options=['High', 'Medium', 'Low'])

# Botón para generar mapa
if st.button("Generar Mapa", key="generar_mapa"):
    try:
        if datos_eventos is not None:
            eventos_df = cargar_datos(datos_eventos)  # Cargar los datos en DataFrame
            mapa, archivo_salida = generar_mapa_con_capas(eventos_df, fecha_inicio, fecha_fin, hora_inicio, hora_fin, precision, poligono)

            # Mostrar el mapa
            map_container = st.empty()
            with map_container:
                components.html(mapa._repr_html_(), height=800)  

            # Habilitar campo para cargar el polígono dibujado
            st.session_state['map_generated'] = True
            st.session_state['mapa'] = mapa
            st.session_state['archivo_salida'] = archivo_salida
        else:
            st.error("Por favor, sube un archivo JSON de eventos válido.")

    except Exception as e:
                st.error(f"Error: {e}")

# Mostrar el botón "Exportar Mapa" solo si el mapa ha sido generado
if 'map_generated' in st.session_state and st.session_state['map_generated']:
    try:
        if st.button("Export map", key="exportar_mapa"):
            # Exportar el mapa
            st.session_state['mapa'].save(st.session_state['archivo_salida'])
            exportar_mapa(st.session_state['mapa'], st.session_state['archivo_salida'])

            with open(st.session_state['archivo_salida'], "r") as f:
                st.download_button("Descargar Mapa", data=f, file_name=st.session_state['archivo_salida'], mime="text/html")

            # Mantener el mapa cargado después de exportar
            map_container = st.empty()
            with map_container:
                components.html(st.session_state['mapa']._repr_html_(), height=800)

            # Resetear el estado del mapa generado después de descargar
            st.session_state['map_generated'] = False

    except Exception as e:
                st.error(f"Error: {e}")

# Campo para cargar el polígono dibujado
if 'map_generated' in st.session_state and st.session_state['map_generated']:

    try:
        uploaded_file_dibujado = st.file_uploader("Upload GeoJSON polygon file or existed GeoJSON polygon file", type=["geojson"])

        if uploaded_file_dibujado is not None:
            
            try:
                eventos_df = cargar_datos(datos_eventos)  # Cargar los datos en DataFrame
                geojson_data = json.load(uploaded_file_dibujado)  # Leer el GeoJSON
                capturar_coordenadas_poligono(json.dumps(geojson_data))  # Capturar coordenadas

                # Verificar si el GeoJSON es de tipo "Point"
                if geojson_data['features'][0]['geometry']['type'] == 'Point':
                    # Solicitar al usuario que ingrese el radio del círculo en metros
                    radio_circulo_metros = st.number_input("Ingresa el radio del círculo (en metros)", min_value=0.0, value=1000.0)
                    # Convertir el radio de metros a grados (aproximadamente)
                    radio_circulo_grados = radio_circulo_metros / 111320  # 1 grado ≈ 111.32 km

                    # Cargar el polígono dibujado con el radio proporcionado
                    poligono_dibujado = cargar_poligono(geojson_data, radio_circulo_grados)  # Pasar el radio a la función
                else:
                    # Cargar el polígono dibujado sin necesidad de radio
                    poligono_dibujado = cargar_poligono(geojson_data)

                # Generar el mapa con el polígono dibujado
                mapa, archivo_salida = generar_mapa_con_capas(eventos_df, fecha_inicio, fecha_fin, hora_inicio, hora_fin, precision, poligono_dibujado)

                # Mostrar el mapa
                map_container = st.empty()
                with map_container:
                    components.html(mapa._repr_html_(), height=800)  

                # Botón para descargar el mapa
                if st.button("Export map", key="exportar_mapa_dibujado"):
                    # Exportar el mapa
                    mapa.save(archivo_salida)
                    exportar_mapa(mapa, archivo_salida)

                    with open(archivo_salida, "r") as f:
                        st.download_button("Download map", data=f, file_name=archivo_salida, mime="text/html")

    
                    # Resetear el estado del mapa generado después de descargar
                    st.session_state['map_generated'] = False

            except Exception as e:
                st.error(f"Error: {e}")
    except Exception as e:
        st.error(f"General error: {e}")











