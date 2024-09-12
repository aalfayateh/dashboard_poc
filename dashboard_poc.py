import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import streamlit as st
import plotly.io as pio

# Initialize global variable for the DataFrame
df = pd.DataFrame()

# Function to load CSV file
def load_file(uploaded_file):
    global df
    if uploaded_file is None:
        st.error("Please upload a valid CSV file.")
        return False

    try:
        df = pd.read_csv(uploaded_file)
        df['tiempo'] = pd.to_datetime(df['tiempo'], format='%d-%m-%Y %H:%M:%S')
        df['date'] = df['tiempo'].dt.date
        df['hour'] = df['tiempo'].dt.hour
        
        # Check if necessary columns exist
        if 'carretera' not in df.columns or 'velocidad_promedio' not in df.columns:
            raise ValueError("Required columns are missing in the file")
        
        st.success("File loaded successfully.")
        return True
    
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return False

# Function to update the plot
def update_plot(start_date, end_date, save_path=None):
    if df.empty:
        st.error("No data available. Please upload a CSV file.")
        return

    # Filter data based on the selected date range
    filtered_df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    
    if filtered_df.empty:
        st.warning("No data available for the selected date range.")
        return
    
    # Group by 'carretera' and 'hour', then calculate the mean velocity
    grouped_df = filtered_df.groupby(['carretera', 'hour'])['velocidad_promedio'].mean().reset_index()
    
    # Calculate the number of entries per 'carretera' and 'hour'
    entries_count_df = filtered_df.groupby(['carretera', 'hour']).size().reset_index(name='entries')
    
    # Create a consistent color map for each carretera
    unique_carreteras = df['carretera'].unique()
    colors = {carretera: f'rgba({int(255 * i / len(unique_carreteras))}, {int(255 * (len(unique_carreteras) - i) / len(unique_carreteras))}, 150, 1)'
              for i, carretera in enumerate(unique_carreteras)}
    
    # Create subplots: one for the line plot and one for the bar chart
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=False, 
        vertical_spacing=0.2,
        subplot_titles=('Average Speed by Road and Hour', 'Number of Entries by Road and Hour'),
        row_width=[0.3, 0.7]
    )
    
    # Line plot for average speed and bar chart for number of entries
    for carretera in unique_carreteras:
        carretera_grouped_df = grouped_df[grouped_df['carretera'] == carretera]
        carretera_entries_df = entries_count_df[entries_count_df['carretera'] == carretera]
        
        # Add line plot trace
        fig.add_trace(go.Scatter(
            x=carretera_grouped_df['hour'],
            y=carretera_grouped_df['velocidad_promedio'],
            mode='lines+markers',
            name=carretera,
            marker=dict(size=8, line=dict(width=1, color=colors[carretera])),
            line=dict(width=2, color=colors[carretera]),
            showlegend=True,
            legendgroup=carretera,
            hovertemplate='%{y:.2f}<extra></extra>'
        ), row=1, col=1)
        
        # Add bar plot trace
        fig.add_trace(go.Bar(
            x=carretera_entries_df['hour'].astype(str),
            y=carretera_entries_df['entries'],
            name=carretera,
            marker=dict(color=colors[carretera]),
            showlegend=False,
            legendgroup=carretera,
            hovertemplate='%{y}<extra></extra>'
        ), row=2, col=1)
    
    # Update layout for a professional look
    fig.update_layout(
        title={
            'text': f'Report of Average Speed and Entries from {start_date} to {end_date}',
            'font': {'size': 24, 'family': 'Arial', 'color': '#004d99'}
        },
        xaxis=dict(
            title='Hour',
            tickvals=list(range(24)),
            tickfont=dict(size=12, color='#666666'),
            showgrid=True,
            range=[-0.5, 23.5]
        ),
        xaxis2=dict(
            title='Hour',
            tickvals=list(range(24)),
            tickfont=dict(size=12, color='#666666'),
            showgrid=True,
            range=[-0.5, 23.5]
        ),
        yaxis=dict(
            title='Average Speed (km/h)',
            tickfont=dict(size=12, color='#666666')
        ),
        yaxis2=dict(
            title='# Entries',
            tickfont=dict(size=12, color='#666666')
        ),
        legend=dict(
            title='Road',
            font=dict(size=12, color='#333333'),
            orientation='v',
            x=1.02,
            xanchor='left',
            y=1,
            yanchor='top'
        ),
        margin=dict(l=50, r=150, t=60, b=50),
        template='plotly_white'
    )
    
    # Display the plot in the Streamlit app
    st.plotly_chart(fig)

    # Optionally save the plot
    if save_path:
        try:
            pio.write_html(fig, save_path)
            st.success(f"Plot saved to {save_path}")
        except Exception as e:
            st.error(f"Error saving the plot: {e}")

# Streamlit app main function
def main():
    st.title("Traffic Data Analysis")

    # File upload section
    uploaded_file = st.file_uploader("Upload your CSV file", type="csv")
    
    if uploaded_file is not None and load_file(uploaded_file):
        # Date input for filtering data
        start_date = st.date_input(f"Start Date (available from {df['date'].min()})", df['date'].min())
        end_date = st.date_input(f"End Date (available until {df['date'].max()})", df['date'].max())
        
        if st.button("Generate Plot"):
            # Text input to save the plot as HTML (optional)
            save_path = st.text_input("Enter the file path to save the plot (optional)", "")
            update_plot(start_date, end_date, save_path)

# Run the Streamlit app
if __name__ == "__main__":
    main()
