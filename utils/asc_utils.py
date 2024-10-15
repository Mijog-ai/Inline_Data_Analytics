import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
from scipy.ndimage import gaussian_filter1d
from nptdms import TdmsFile
import logging
import io
import chardet


def load_and_process_asc_file(file_name):
    with open(file_name, 'r') as file:
        content = file.read()

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
        df[col] = df[col].apply(lambda x: x.replace(',', '.') if isinstance(x, str) else x)
        df[col] = pd.to_numeric(df[col], errors='coerce')

    return df


def load_and_process_csv_file(file_name):
    return pd.read_csv(file_name)

def load_and_process_tdms_file(file_name):
    with TdmsFile.open(file_name) as tdms_file:
        # Get all groups in the file
        groups = tdms_file.groups()

        # Create a dictionary to store data from all groups
        data_dict = {}

        for group in groups:
            for channel in group.channels():
                channel_name = f"{group.name}/{channel.name}"
                data = channel[:]
                data_dict[channel_name] = data

        # Find the maximum length of data
    max_length = max(len(data) for data in data_dict.values())

    # Pad shorter arrays with NaN
    for key in data_dict:
        if len(data_dict[key]) < max_length:
            pad_length = max_length - len(data_dict[key])
            data_dict[key] = np.pad(data_dict[key], (0, pad_length), 'constant', constant_values=np.nan)

    # Create DataFrame
    df = pd.DataFrame(data_dict)
    return df

def apply_smoothing(data, method='savgol', window_length=21, poly_order=3, sigma=2):
    if window_length >= len(data):
        window_length = len(data) - 1
    if window_length % 2 == 0:
        window_length -= 1

    if method == 'mean_line':
        return data.rolling(window=window_length, center=True).mean()
    elif method == 'savitzky-golay':
        return savgol_filter(data, window_length, poly_order)
    elif method == 'gaussian_filter':
        return gaussian_filter1d(data, sigma=sigma)