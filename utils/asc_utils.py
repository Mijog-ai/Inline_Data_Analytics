# asc_processor.py

import pandas as pd
import plotly.graph_objects as go
from scipy.signal import savgol_filter
from scipy.ndimage import gaussian_filter1d


# Function to load and process the .asc file
def load_and_process_asc_file(file):
    content = file.getvalue().decode("utf-8")
    lines = content.split('\n')

    # Find the start of the data
    data_start = 0
    for i, line in enumerate(lines):
        if line.startswith("Messzeit[s]"):
            data_start = i + 1
            break

    # Extract header and data
    header = lines[data_start - 1].split('\t')
    data = [line.split('\t') for line in lines[data_start:] if line.strip()]

    # Rename duplicate columns
    new_header = []
    seen = {}
    for i, item in enumerate(header):
        if item in seen:
            seen[item] += 1
            new_header.append(f"{item}_{seen[item]}")
        else:
            seen[item] = 0
            new_header.append(item)

    df = pd.DataFrame(data, columns=new_header)

    # Convert columns to appropriate types
    for col in df.columns:
        try:
            df[col] = df[col].apply(lambda x: x.replace(',', '.') if isinstance(x, str) else x)
            df[col] = pd.to_numeric(df[col], errors='coerce')
        except Exception as e:
            print(f"Error processing column {col}: {str(e)}")

    return df


# Function to apply different smoothing techniques
def apply_smoothing(data, method='savgol', window_length=21, poly_order=3, sigma=2):
    if window_length >= len(data):
        window_length = len(data) - 1
    if window_length % 2 == 0:
        window_length -= 1

    if method == 'savgol':
        return savgol_filter(data, window_length, poly_order)
    elif method == 'mean':
        return data.rolling(window=window_length, center=True).mean()
    elif method == 'gaussian':
        return gaussian_filter1d(data, sigma=sigma)
    elif method == 'all':
        mean_smoothed = data.rolling(window=window_length, center=True).mean()
        savgol_smoothed = savgol_filter(data, window_length, poly_order)
        gaussian_smoothed = gaussian_filter1d(data, sigma=sigma)
        return mean_smoothed, savgol_smoothed, gaussian_smoothed


# Function to plot data using Plotly with smoothing and zoom options
def plot_data(df, x_column, y_column, smoothing_params):
    x_data = df[x_column]
    y_data = df[y_column]

    # Create Plotly figure
    fig = go.Figure()

    # Plot original data
    fig.add_trace(go.Scatter(x=x_data, y=y_data, mode='lines', name='Original Data', line=dict(color='lightgray', width=2)))

    # Apply smoothing if requested
    if smoothing_params['apply']:
        try:
            if smoothing_params['method'] == 'all':
                y_mean, y_savgol, y_gaussian = apply_smoothing(
                    y_data,
                    method='all',
                    window_length=smoothing_params['window_length'],
                    poly_order=smoothing_params['poly_order'],
                    sigma=smoothing_params['sigma']
                )
                fig.add_trace(go.Scatter(x=x_data, y=y_mean, mode='lines', name='Mean Line', line=dict(color='red', width=2)))
                fig.add_trace(go.Scatter(x=x_data, y=y_savgol, mode='lines', name='Savitzky-Golay', line=dict(color='blue', width=2)))
                fig.add_trace(go.Scatter(x=x_data, y=y_gaussian, mode='lines', name='Gaussian', line=dict(color='green', width=2)))
            else:
                y_smoothed = apply_smoothing(
                    y_data,
                    method=smoothing_params['method'],
                    window_length=smoothing_params['window_length'],
                    poly_order=smoothing_params['poly_order'],
                    sigma=smoothing_params['sigma']
                )
                if smoothing_params['method'] == 'mean':
                    fig.add_trace(go.Scatter(x=x_data, y=y_smoothed, mode='lines', name='Mean Line', line=dict(color='red', width=2)))
                elif smoothing_params['method'] == 'gaussian':
                    fig.add_trace(go.Scatter(x=x_data, y=y_smoothed, mode='lines', name='Gaussian', line=dict(color='green', width=2)))
                else:
                    fig.add_trace(go.Scatter(x=x_data, y=y_smoothed, mode='lines', name='Savitzky-Golay', line=dict(color='blue', width=2)))
        except Exception as e:
            print(f"Smoothing error: {str(e)}")

    # Update layout for better zooming and interactivity
    fig.update_layout(
        title=f'{y_column} vs {x_column}',
        xaxis_title=x_column,
        yaxis_title=y_column,
        showlegend=True,
        hovermode='x',
        margin=dict(l=0, r=0, t=40, b=40),
        height=600,
    )

    return fig
