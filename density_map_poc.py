import pandas as pd
from shapely import wkt
import folium
import streamlit as st
from streamlit_folium import st_folium
from io import BytesIO

# Function to extract 2D coordinates from a geometry
def extract_2d_coords(geometry):
    """ Extracts 2D coordinates from a LineStringZ geometry, swapping x and y values """
    if geometry is None:
        return []
    if geometry.geom_type == 'LineString':
        return [(y, x) for x, y, _ in geometry.coords]
    elif geometry.geom_type == 'MultiLineString':
        return [coord for line in geometry for coord in extract_2d_coords(line)]
    else:
        return []

# Function to load the dataframe from a CSV file
@st.cache_data
def load_dataframe(file):
    df = pd.read_csv(file)
    df['geometry'] = df['geometry'].apply(wkt.loads)  # Convert WKT to shapely geometry
    return df

# Function to create color based on vehicle count
def get_color(vehicle_count):
    if vehicle_count < 500:
        return 'green'
    elif 1000 <= vehicle_count < 2500:
        return 'orange'
    else:
        return 'red'

# Function to generate the map
def generate_map(df, selected_date, road_type):
    filtered_df = df[(df['fecha'] == str(selected_date)) & (df['nombre'] == road_type)]

    if filtered_df.empty:
        return None, "No data found for the selected date and road type."

    m = folium.Map(location=[40.4168, -3.7038], zoom_start=6, tiles='CartoDB Positron')

    for _, road in filtered_df.iterrows():
        vehicle_count = road.get('vehicle_count', 0)
        color = get_color(vehicle_count)
        coords = extract_2d_coords(road.geometry)
        if road.geometry.geom_type == 'MultiLineString':
            coords = [coord for sublist in coords for coord in sublist]
        folium.PolyLine(coords, color=color, weight=5).add_to(m)

    html_data = BytesIO()
    m.save(html_data, close_file=False)
    
    return m, html_data

# Streamlit app
st.title("Density Traffic Map Generator")

# Step 1: Upload CSV file
uploaded_file = st.file_uploader("Upload CSV file", type="csv")

if uploaded_file is not None:
    # Step 2: Load the DataFrame
    df = load_dataframe(uploaded_file)
    st.success(f"CSV file loaded with {len(df)} entries.")

    # Step 3: Select date and road type
    min_date = pd.to_datetime(df['fecha'].min()).date()
    max_date = pd.to_datetime(df['fecha'].max()).date()
    road_types = df['nombre'].unique()

    st.write(f"Available dates: {min_date} to {max_date}")

    # Input widgets for selecting date and road type
    selected_date = st.date_input("Select date", min_value=min_date, max_value=max_date, key='date_input')
    road_type = st.selectbox("Select road type", road_types, key='road_select')

    # Add a button to generate the map
    generate_button_enabled = selected_date and road_type
    if st.button("Generate Map", disabled=not generate_button_enabled):
        # Step 4: Generate the map
        map_object, html_data = generate_map(df, selected_date, road_type)

        if map_object is None:
            st.warning(html_data)  # Display warning if no data found
        else:
            # Step 5: Display the map
            st_folium(map_object, width=700, height=500)

            # Step 6: Export the map to HTML and allow downloading
            st.download_button(
                label="Download Density Heatmap as HTML",
                data=html_data.getvalue(),
                file_name=f"traffic_map_{selected_date}_{road_type}.html",
                mime='text/html'
            )
