import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
from scipy.ndimage import gaussian_filter1d
from nptdms import TdmsFile
import logging
import io
import chardet

import re


def load_and_process_asc_file(file_name):
    content = ""
    try:
        # Detect file encoding
        with open(file_name, 'rb') as file:
            raw_data = file.read()
        result = chardet.detect(raw_data)
        file_encoding = result['encoding']

        # Try to read the file with the detected encoding
        try:
            with open(file_name, 'r', encoding=file_encoding) as file:
                content = file.read()
        except UnicodeDecodeError:
            # If that fails, try with 'latin-1' encoding
            with open(file_name, 'r', encoding='latin-1') as file:
                content = file.read()

        lines = content.split('\n')

        # Find the start of the data
        data_start = 0
        for i, line in enumerate(lines):
            # Check if the line contains tab-separated values and starts with a number-like string
            if '\t' in line and re.match(r'^[\d,.]+\t', line.strip()):
                data_start = i
                break

        if data_start == 0:
            raise ValueError("Could not find the start of data in the file.")

        # Extract header and data
        header = lines[data_start - 1].split('\t')
        data = [line.split('\t') for line in lines[data_start:] if line.strip()]

        # Ensure all data rows have the same number of columns as the header
        max_columns = len(header)
        data = [row for row in data if len(row) == max_columns]

        # Rename duplicate columns
        new_header = []
        seen = {}
        for i, item in enumerate(header):
            item = item.strip()  # Remove leading/trailing whitespace
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

        logging.info(f"Successfully loaded ASC file. Shape: {df.shape}")
        logging.info(f"Columns: {df.columns.tolist()}")
        return df

    except Exception as e:
        logging.error(f"Error loading ASC file: {str(e)}")
        if content:
            lines = content.split('\n')[:10]
            logging.error(f"File content (first 10 lines): {lines}")
        else:
            logging.error("Unable to read file content")
        raise


def load_and_process_csv_file(file_name):
    """Load CSV file with automatic encoding detection."""
    try:
        # Try to detect the encoding first
        with open(file_name, 'rb') as file:
            raw_data = file.read()
        result = chardet.detect(raw_data)
        detected_encoding = result['encoding']

        logging.info(f"Detected CSV encoding: {detected_encoding}")

        # List of encodings to try in order
        encodings_to_try = [
            detected_encoding,  # Try detected encoding first
            'utf-8',
            'latin-1',
            'iso-8859-1',
            'cp1252',
            'windows-1252',
        ]

        # Remove None and duplicates
        encodings_to_try = list(dict.fromkeys([e for e in encodings_to_try if e]))

        # Try each encoding
        for encoding in encodings_to_try:
            try:
                logging.info(f"Trying to load CSV with encoding: {encoding}")
                df = pd.read_csv(file_name, encoding=encoding)
                logging.info(f"Successfully loaded CSV with {encoding} encoding. Shape: {df.shape}")
                return df
            except UnicodeDecodeError:
                logging.warning(f"Failed to load with {encoding} encoding")
                continue
            except Exception as e:
                logging.warning(f"Error with {encoding} encoding: {str(e)}")
                continue

        # If all encodings fail, try with errors='ignore'
        logging.warning("All encodings failed, trying with errors='ignore'")
        df = pd.read_csv(file_name, encoding='utf-8', errors='ignore')
        logging.info(f"Loaded CSV with error handling. Shape: {df.shape}")
        return df

    except Exception as e:
        logging.error(f"Error loading CSV file: {str(e)}")
        raise


def get_excel_sheets(file_name):
    """Get list of sheet names from an Excel file."""
    try:
        excel_file = pd.ExcelFile(file_name)
        return excel_file.sheet_names
    except Exception as e:
        logging.error(f"Error getting Excel sheets: {str(e)}")
        return []


def load_and_process_excel_file(file_name, sheet_name=None):
    """Load Excel file with optional sheet selection."""
    try:
        if sheet_name:
            df = pd.read_excel(file_name, sheet_name=sheet_name)
        else:
            # If no sheet specified, load the first sheet
            df = pd.read_excel(file_name, sheet_name=0)

        logging.info(f"Successfully loaded Excel file. Shape: {df.shape}")
        logging.info(f"Columns: {df.columns.tolist()}")
        return df
    except Exception as e:
        logging.error(f"Error loading Excel file: {str(e)}")
        raise


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


def apply_smoothing(data, method='savgol', window_length=21, poly_order=3, sigma=2,
                    alpha=0.3, cutoff_freq=0.1, filter_order=4, lowess_frac=0.1,
                    spatial_sigma=5.0, range_sigma=2.0):
    """
    Apply various smoothing algorithms to data.

    Parameters:
    -----------
    data : array-like
        Input data to smooth
    method : str
        Smoothing method to use
    window_length : int
        Window size for moving average, Savitzky-Golay, and median filters
    poly_order : int
        Polynomial order for Savitzky-Golay filter
    sigma : float
        Sigma for Gaussian filter
    alpha : float
        Smoothing factor for exponential moving average (0-1)
    cutoff_freq : float
        Cutoff frequency for Butterworth filter (0-0.5)
    filter_order : int
        Order for Butterworth filter
    lowess_frac : float
        Fraction of data for Lowess smoothing (0-1)
    spatial_sigma : float
        Spatial sigma for bilateral filter
    range_sigma : float
        Range sigma for bilateral filter

    Returns:
    --------
    Smoothed data as pandas Series or numpy array
    """
    # Ensure window_length is odd and valid
    if window_length >= len(data):
        window_length = len(data) - 1
    if window_length % 2 == 0:
        window_length -= 1
    if window_length < 3:
        window_length = 3

    try:
        if method == 'moving_average' or method == 'mean_line':
            # Simple moving average
            return data.rolling(window=window_length, center=True, min_periods=1).mean()

        elif method == 'savitzky-golay':
            # Savitzky-Golay filter
            if poly_order >= window_length:
                poly_order = window_length - 1
            return savgol_filter(data, window_length, poly_order)

        elif method == 'gaussian_filter':
            # Gaussian filter
            return gaussian_filter1d(data, sigma=sigma)

        elif method == 'exponential_moving_avg':
            # Exponential moving average
            return data.ewm(alpha=alpha, adjust=False).mean()

        elif method == 'median_filter':
            # Median filter (robust to outliers)
            from scipy.ndimage import median_filter
            return median_filter(data, size=window_length)

        elif method == 'lowess_local_regression':
            # Lowess (Locally Weighted Scatterplot Smoothing)
            try:
                from statsmodels.nonparametric.smoothers_lowess import lowess
                # Create x values (indices)
                x = np.arange(len(data))
                # Apply lowess
                smoothed = lowess(data, x, frac=lowess_frac, return_sorted=False)
                return smoothed
            except ImportError:
                logging.warning("statsmodels not installed. Falling back to moving average.")
                return data.rolling(window=window_length, center=True, min_periods=1).mean()

        # elif method == 'butterworth_filter':
        #     # Butterworth low-pass filter
        #     try:
        #         from scipy.signal import butter, filtfilt
        #         # Design filter
        #         b, a = butter(filter_order, cutoff_freq, btype='low', analog=False)
        #         # Apply filter (zero-phase filtering)
        #         smoothed = filtfilt(b, a, data)
        #         return smoothed
        #     except Exception as e:
        #         logging.warning(f"Butterworth filter failed: {e}. Falling back to Gaussian.")
        #         return gaussian_filter1d(data, sigma=sigma)
        #
        # elif method == 'bilateral_filter':
        #     # Bilateral filter (edge-preserving)
        #     try:
        #         # Simple implementation of bilateral filter for 1D data
        #         smoothed = np.zeros_like(data)
        #         for i in range(len(data)):
        #             # Define neighborhood
        #             w_start = max(0, i - window_length // 2)
        #             w_end = min(len(data), i + window_length // 2 + 1)
        #
        #             # Get neighborhood data
        #             neighborhood = data[w_start:w_end]
        #             positions = np.arange(w_start, w_end)
        #
        #             # Calculate spatial weights (distance from center)
        #             spatial_weights = np.exp(-((positions - i) ** 2) / (2 * spatial_sigma ** 2))
        #
        #             # Calculate range weights (intensity difference)
        #             range_weights = np.exp(-((neighborhood - data[i]) ** 2) / (2 * range_sigma ** 2))
        #
        #             # Combined weights
        #             weights = spatial_weights * range_weights
        #             weights /= weights.sum()
        #
        #             # Weighted average
        #             smoothed[i] = np.sum(neighborhood * weights)
        #
        #         return smoothed
        #     except Exception as e:
        #         logging.warning(f"Bilateral filter failed: {e}. Falling back to Gaussian.")
        #         return gaussian_filter1d(data, sigma=sigma)
        #
        else:
            # Default to moving average
            logging.warning(f"Unknown smoothing method: {method}. Using moving average.")
            return data.rolling(window=window_length, center=True, min_periods=1).mean()

    except Exception as e:
        logging.error(f"Error in smoothing: {e}. Returning original data.")
        return data