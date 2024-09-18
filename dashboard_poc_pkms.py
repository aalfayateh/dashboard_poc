import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import io

# Global DataFrame
df = pd.DataFrame()

def load_file():
    """
    Load CSV file and preprocess data.
    """
    global df
    file = st.file_uploader("Upload a CSV file", type="csv")
    
    if file is None:
        st.warning("Please upload a CSV file.")
        return False

    try:
        df = pd.read_csv(file)
        df['tiempo'] = pd.to_datetime(df['tiempo'], format='%d-%m-%Y %H:%M:%S')
        df['date'] = df['tiempo'].dt.date
        df['hour'] = df['tiempo'].dt.hour
        
        # Check if necessary columns exist
        required_columns = ['carretera', 'velocidad_promedio', 'sentido', 'pkm']
        for col in required_columns:
            if col not in df.columns:
                st.error(f"Required column is missing: {col}")
                return False

        # Display available filters
        min_date = df['date'].min()
        max_date = df['date'].max()
        unique_sentidos = df['sentido'].unique()
        min_pkm = df['pkm'].min()
        max_pkm = df['pkm'].max()

        st.write(f"Available data from {min_date} to {max_date}")
        st.write(f"Available directions: {', '.join(unique_sentidos)}")
        st.write(f"PKM range: {min_pkm} - {max_pkm}")
        
        return True
    
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return False

def update_plot(start_date, end_date, sentido, pkm1, pkm2):
    """
    Generate and display the plot based on selected filters.
    """
    if df.empty:
        st.warning("No data available. Please load a file.")
        return None

    # Filter data based on the selected date range and other filters
    filtered_df = df[
        (df['date'] >= start_date) &
        (df['date'] <= end_date) & 
        (df['sentido'] == sentido) & 
        (df['pkm'].between(pkm1, pkm2))
    ]

    if filtered_df.empty:
        st.warning("No data available for the selected filters.")
        return None

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
        shared_xaxes=False,  # No shared x-axis
        vertical_spacing=0.2,
        subplot_titles=('Velocidad promedio por vía y hora', 'Número de tránsitos por vía y hora'),
        row_width=[0.3, 0.7]  # Adjust the row height ratio
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
            showlegend=True,  # Show legend for lines
            legendgroup=carretera,  # Group by carretera
            hovertemplate='%{y:.2f}<extra></extra>'  # Only show y-value
        ), row=1, col=1)

        # Add bar plot trace
        fig.add_trace(go.Bar(
            x=carretera_entries_df['hour'].astype(str),
            y=carretera_entries_df['entries'],
            name=carretera,
            marker=dict(color=colors[carretera]),
            showlegend=False,  # Do not show separate legend for bars
            legendgroup=carretera,  # Group by carretera
            hovertemplate='%{y}<extra></extra>'  # Only show y-value
        ), row=2, col=1)

    # Update layout for a professional look
    fig.update_layout(
        title={
            'text': (f'Reporte Vpromedio y #Tránsitos desde {start_date} hasta {end_date} '
                     f'| Sentido: {sentido} | PKM {pkm1} - {pkm2}'),
            'font': {'size': 16, 'family': 'Arial', 'color': '#004d99'}  # Adjusted title font size
        },
        xaxis=dict(
            title='Hora',
            tickvals=list(range(24)),
            tickfont=dict(size=12, color='#666666'),
            showgrid=True,  # Show grid for clarity
            range=[-0.5, 23.5]
        ),
        xaxis2=dict(  # Duplicate x-axis for the second row
            title='Hora',
            tickvals=list(range(24)),
            tickfont=dict(size=12, color='#666666'),
            showgrid=True,  # Show grid for clarity
            range=[-0.5, 23.5]
        ),
        yaxis=dict(
            title='Vpromedio (km/h)',
            tickfont=dict(size=12, color='#666666')
        ),
        yaxis2=dict(
            title='# Tránsitos',
            tickfont=dict(size=12, color='#666666')
        ),
        legend=dict(
            title='Carretera',
            font=dict(size=12, color='#333333'),
            orientation='v',  # Vertical legend
            x=1.02,  # Position legend to the right
            xanchor='left',
            y=1,
            yanchor='top'
        ),
        margin=dict(l=50, r=150, t=60, b=50),  # Adjust margins for better spacing
        template='plotly_white'  # Clean white background for professional appearance
    )

    return fig

def main():
    st.title("Traffic PKMs Data Analysis")

    # Load CSV and preprocess data
    if load_file():
        # User selects filter parameters
        start_date = st.date_input("Start date", min_value=df['date'].min(), max_value=df['date'].max(), value=df['date'].min())
        end_date = st.date_input("End date", min_value=df['date'].min(), max_value=df['date'].max(), value=df['date'].max())
        sentido = st.selectbox("Direction", df['sentido'].unique())
        pkm1, pkm2 = st.slider("Select PKM range", min_value=int(df['pkm'].min()), max_value=int(df['pkm'].max()), value=(int(df['pkm'].min()), int(df['pkm'].max())))

        # Button to generate the plot
        if st.button("Generate Plot"):
            fig = update_plot(start_date, end_date, sentido, pkm1, pkm2)
            if fig:
                # Display the plot in the Streamlit app
                st.plotly_chart(fig)

                # Create an HTML export of the plot
                html_buffer = io.StringIO()
                fig.write_html(html_buffer, include_plotlyjs='cdn')
                html_data = html_buffer.getvalue()

                # Generate the filename using PKM range and sentido
                filename = f"traffic_analysis_{pkm1}_{pkm2}_{sentido}_plot.html"

                # Download button for the plot with dynamic filename
                st.download_button(
                    label="Download Plot as HTML",
                    data=html_data,
                    file_name=filename,
                    mime='text/html'
                )

if __name__ == "__main__":
    main()
