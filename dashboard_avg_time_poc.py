import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import io
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
        df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d')

        required_columns = ['date', 'hour', 'sentido', 'pkm', 'avg_time_diff']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Required column missing: {col}")

        # Display available options for filters
        st.success(f"File loaded successfully.")
        return True

    except Exception as e:
        st.error(f"Error loading file: {e}")
        return False

def calculate_average_time_diff(selected_date, pkm1, pkm2, sentido):
    selected_date = pd.to_datetime(selected_date).date()

    # Ensure pkm1 is smaller than pkm2 for proper range filtering
    pkm_min, pkm_max = min(pkm1, pkm2), max(pkm1, pkm2)

    # Filter data based on the selected date, PKM range, and sentido
    day_data = df[
        (df['date'].dt.date == selected_date) &
        (df['pkm'] >= pkm_min) & (df['pkm'] <= pkm_max) &
        (df['sentido'] == sentido)
    ]

    if day_data.empty:
        return pd.DataFrame(columns=['hour', 'average_time_diff']), 0

    # Calculate the sum of avg_time_diff per hour for PKMs in the range
    time_diffs = day_data.groupby('hour').agg({'avg_time_diff': 'sum'}).reset_index()

    # Calculate the overall average of the time differences (total sum / number of hours)
    overall_avg_time_diff = time_diffs['avg_time_diff'].mean()

    return time_diffs, overall_avg_time_diff


def update_plot(selected_date, pkm1, pkm2, sentido):
    if df.empty:
        st.error("No data available. Please upload a CSV file.")
        return None

    time_diff_df, overall_avg_time_diff = calculate_average_time_diff(selected_date, pkm1, pkm2, sentido)

    if time_diff_df.empty:
        st.warning("No data available for the selected criteria.")
        return None

    # Create the plot
    fig = go.Figure()

    # Line plot for average time difference
    fig.add_trace(go.Scatter(
        x=time_diff_df['hour'],
        y=time_diff_df['avg_time_diff'],
        mode='lines+markers',
        name='Avg Time Difference',
        line=dict(color='lightgreen', width=2),
        marker=dict(size=8, color='lightgreen', line=dict(width=1, color='darkgreen')),
        hovertemplate='Avg Time: %{y:.2f} mins<extra></extra>'
    ))

    # Horizontal line for overall average time difference
    fig.add_trace(go.Scatter(
        x=[0, 23],
        y=[overall_avg_time_diff, overall_avg_time_diff],
        mode='lines',
        name='Overall Avg Time',
        line=dict(color='darkgreen', width=2, dash='dash'),
        hovertemplate='Overall Avg Time: %{y:.2f} mins<extra></extra>'
    ))

    # Update layout
    fig.update_layout(
        title=f'Avg Time Difference between PKM {pkm1} and PKM {pkm2} on {selected_date} for sentido {sentido}',
        xaxis_title='Hour',
        yaxis_title='Avg Time (mins)',
        xaxis=dict(tickmode='linear', dtick=1, range=[-0.5, 23.5]),
        yaxis=dict(range=[0, max(time_diff_df['avg_time_diff'].max(), overall_avg_time_diff) + 2]),
        template='plotly_white'
    )

    return fig

# Streamlit app main function
def main():
    st.title("Traffic Average Time and PKMs Analysis")

    # File upload section
    uploaded_file = st.file_uploader("Upload your CSV file", type="csv")

    if uploaded_file is not None and load_file(uploaded_file):
        min_date = df['date'].min().date()
        max_date = df['date'].max().date()
        unique_sentidos = df['sentido'].unique()
        min_pkm = df['pkm'].min()
        max_pkm = df['pkm'].max()

        # Date input for filtering
        selected_date = st.date_input("Select a Date", min_value=min_date, max_value=max_date, value=min_date)

        # Dropdown for sentido
        sentido = st.selectbox("Select a Sentido", unique_sentidos)

        # Sliders for PKM range
        pkm1 = st.slider(f"Select Start PKM (available range: {min_pkm}-{max_pkm})", min_value=min_pkm, max_value=max_pkm, value=min_pkm)
        pkm2 = st.slider(f"Select End PKM (available range: {min_pkm}-{max_pkm})", min_value=min_pkm, max_value=max_pkm, value=max_pkm)

        if st.button("Generate Plot"):
            fig = update_plot(selected_date, pkm1, pkm2, sentido)

            if fig:
                st.plotly_chart(fig)

                # Provide option to download the plot as HTML
                buf = io.StringIO()
                pio.write_html(fig, buf)
                html_bytes = buf.getvalue().encode()

                file_name = f"Traffic_Time_Avg_{selected_date}_{pkm1}_{pkm2}.html"
                st.download_button(
                    label="Download Plot as HTML",
                    data=html_bytes,
                    file_name=file_name,
                    mime='text/html'
                )

# Run the Streamlit app
if __name__ == "__main__":
    main()
