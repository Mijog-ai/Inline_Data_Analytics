# Inline Data Analytics Tool - User Manual

## Table of Contents
1. [Getting Started](#getting-started)
2. [Loading Data](#loading-data)
3. [Data Visualization](#data-visualization)
4. [Data Filtering](#data-filtering)
5. [Smoothing Options](#smoothing-options)
6. [Curve Fitting](#curve-fitting)
7. [Statistics](#statistics)
8. [Comments & Annotations](#comments--annotations)
9. [Interactive Plot Features](#interactive-plot-features)
10. [Session Management](#session-management)
11. [Export Options](#export-options)

---

## Getting Started

The Inline Data Analytics Tool is a desktop application for comprehensive data analysis and visualization. It supports multiple file formats and provides advanced signal processing, curve fitting, and interactive plotting capabilities.

### System Requirements
- Python 3.x
- PyQt5
- PyQtGraph
- Pandas, NumPy, SciPy
- Matplotlib

### Launching the Application
Run the application using:
```bash
python main.py
```

---

## Loading Data

### Supported File Formats
- **ASC** - ASCII text files
- **CSV** - Comma-separated values
- **TDMS** - National Instruments Technical Data Management Streaming
- **Excel** - XLS and XLSX formats

### How to Load Files

**Method 1: File Menu**
1. Click **File** → **Open**
2. Select your data file
3. For Excel files with multiple sheets, a dialog will appear to select the desired sheet

**Method 2: Drag & Drop**
- Simply drag and drop a data file onto the application window

### Features
- Automatic character encoding detection for international files
- Multi-sheet Excel support with selection dialog
- Automatic data parsing and column detection

---

## Data Visualization

### Axis Selection

**X-Axis Selection:**
- Select the column to use as the X-axis from the dropdown in the left panel

**Y-Axis Selection:**
- Up to **3 Y-axes** can be plotted simultaneously
- Y1, Y2, and Y3 dropdowns allow multi-axis plotting
- All Y-axes share the same synchronized X-axis

### Auto-Plotting
- Plots automatically update when axis selections change
- No manual "Plot" button required - visualization is instant

### Color Coding
- Each data series is assigned a distinct color from a 10-color palette
- Colors help distinguish multiple plots on the same graph

---

## Data Filtering

### Applying Filters

1. **Select Filter Column:** Choose the data column to filter in the Data Filter section
2. **Set Min Value:** Enter the minimum value for the range
3. **Set Max Value:** Enter the maximum value for the range
4. **Click "Apply Filter":** Data outside the specified range will be excluded

### Features
- Filter any column in your dataset
- Multiple filters can be applied sequentially
- Real-time plot and statistics updates after filtering
- Filter settings are preserved in session files

### Resetting Filters
- Reload the original data file to remove all filters
- Or use **File** → **New** to start a fresh session

---

## Smoothing Options

### Available Smoothing Algorithms

1. **Moving Average**
   - Simple rolling window smoothing
   - Parameter: Window Size (3-100 points)

2. **Savitzky-Golay**
   - Polynomial-based smoothing that preserves peaks
   - Parameters: Window Size, Polynomial Order

3. **Gaussian Filter**
   - Kernel-based smoothing with configurable spread
   - Parameters: Window Size, Sigma

4. **Exponential Moving Average**
   - Weighted smoothing emphasizing recent data
   - Parameter: Alpha (0.0-1.0)

5. **Median Filter**
   - Robust to outliers and noise spikes
   - Parameter: Window Size

6. **LOWESS** (Locally Weighted Scatterplot Smoothing)
   - Non-parametric local regression smoothing
   - Parameter: Fraction (0.0-1.0)

### Applying Smoothing

1. Select the desired smoothing algorithm from the dropdown
2. Adjust parameters (window size, polynomial order, sigma, etc.)
3. Click **"Apply Smoothing"**
4. The plot updates to show the smoothed data

### Toggling Between Original and Smoothed Data
- Use the **"Show Original Data"** button to switch between smoothed and original data views

---

## Curve Fitting

### Supported Fit Types

**Polynomial Fitting:**
- Degrees 1 through 9 available
- Degree 1: Linear fit
- Degree 2: Quadratic fit
- Degrees 3-9: Higher-order polynomial fits

**Exponential Fitting:**
- Exponential curve fitting with automatic parameter estimation

### Performing Curve Fitting

1. **Select Fit Type:** Choose polynomial degree or exponential from the dropdown
2. **Click "Fit Curve":** The application calculates the best-fit curve
3. **View Results:** The fitted curve appears on the plot with:
   - Curve equation in the legend
   - R-squared (R²) goodness-of-fit metric
   - Optional highlighting for visual emphasis

### Curve Fit Features
- **Fit Equation Labels:** Mathematical equations displayed in the legend
- **Highlight Support:** Visual highlighting of fitted curves for emphasis
- **Remove Fit Button:** Click **"Remove Fit"** to clear all curve fits from the plot
- **R² Calculation:** Automatic goodness-of-fit metrics

---

## Statistics

### Automatic Calculation
The application automatically calculates and displays descriptive statistics for all visible data:

- **Mean:** Average value
- **Median:** Middle value in sorted data
- **Max:** Maximum value
- **Min:** Minimum value
- **Standard Deviation:** Measure of data spread

### Features
- Statistics update automatically when data is filtered or plotted
- Displayed in an organized table in the right panel
- Optimized with caching to avoid redundant calculations
- Statistics reflect the currently filtered/displayed data

---

## Comments & Annotations

### Adding Comments

1. Locate the **Comment Box** in the right panel
2. Type your notes, observations, or analysis documentation
3. Comments are automatically saved with your session

### Uses
- Document analysis findings
- Add notes for future reference
- Record observations about the data
- Comments are included when exporting to Excel

---

## Interactive Plot Features

### Cursor Mode
- **Toggle Cursor:** Enable/disable crosshair cursor
- **Position Tracking:** See precise X/Y coordinates as you move the cursor

### Legend Display
- Dynamic legend showing:
  - Plot variable names
  - Curve fit equations
  - R² values for fitted curves

### Text Insertion
- Add custom text annotations directly to plots
- Useful for labeling specific features or events

### Point Highlighting
- Click on the plot to highlight specific data points
- Visual emphasis for important data features

### Zoom Region Mode
- Define custom zoom areas by selecting regions on the plot
- Zoom in to examine specific data ranges in detail

### Original Data Toggle
- Switch between smoothed and original data display
- Button: **"Show Original Data"**

---

## Session Management

### Saving Sessions

1. Click **File** → **Save Session**
2. Choose a location and filename
3. Session files are saved with `.inlingh` extension

**What's Saved:**
- All loaded data and filtered data
- Axis selections (X, Y1, Y2, Y3)
- Smoothing parameters and settings
- Curve fit configurations
- Comments and annotations
- Filter settings
- Plot configuration

### Loading Sessions

1. Click **File** → **Load Session**
2. Select a previously saved `.inlingh` file
3. The entire analysis state is restored exactly as it was saved

### Starting a New Session

1. Click **File** → **New**
2. If there are unsaved changes, you'll be prompted to save
3. All data and settings are cleared for a fresh start

---

## Export Options

### Export Data

**CSV Format:**
1. Click **File** → **Export to CSV**
2. Choose filename and location
3. Filtered data is exported in CSV format

**Excel Format:**
1. Click **File** → **Export to Excel**
2. Choose filename and location
3. Excel file includes multiple sheets:
   - **Data Sheet:** Your filtered/processed data
   - **Statistics Sheet:** Calculated statistics
   - **Plot Configuration:** Axis selections and settings
   - **Comments Sheet:** Your annotations and notes

### Export Plots

**PNG Format:**
1. Click **File** → **Save Plot as PNG**
2. High-resolution image suitable for presentations

**PDF Format:**
1. Click **File** → **Save Plot as PDF**
2. Vector-based format ideal for publications

---

## Keyboard Shortcuts & Tips

### Best Practices
- Always save your session before closing to preserve your analysis
- Use descriptive filenames for sessions to easily identify different analyses
- Apply filters before smoothing for best results
- Check R² values to assess curve fit quality (closer to 1.0 is better)
- Export to Excel for comprehensive documentation including metadata

### Logging
- Application logs are saved to `app.log` in the application directory
- Useful for troubleshooting issues or reviewing operation history

---

## Troubleshooting

### Common Issues

**File Won't Load:**
- Ensure the file format is supported (ASC, CSV, TDMS, Excel)
- Check that the file isn't corrupted or password-protected
- Verify file encoding (application auto-detects most encodings)

**Plot Doesn't Appear:**
- Ensure both X-axis and at least one Y-axis are selected
- Check that the data contains valid numeric values
- Verify that filters haven't excluded all data

**Smoothing Not Working:**
- Ensure window size is appropriate for your data (not larger than data length)
- For Savitzky-Golay, polynomial order must be less than window size
- Check that the selected column contains numeric data

**Curve Fitting Fails:**
- Ensure sufficient data points (at least more than polynomial degree)
- Check for NaN or infinite values in the data
- Try a lower polynomial degree for noisy data

---

## Advanced Features

### Multi-Axis Plotting
- Plot up to 3 different Y-axes with independent scales
- All axes share the same X-axis for time-series or synchronized data analysis
- Useful for comparing variables with different units or scales

### Performance Optimization
- PyQtGraph rendering for fast, responsive plotting even with large datasets
- Statistics caching to avoid redundant calculations
- Automatic change detection for efficient updates

### File Format Details

**ASC Files:** Text-based format with automatic delimiter detection
**CSV Files:** Standard comma-separated format with header detection
**TDMS Files:** Binary format from National Instruments data acquisition systems
**Excel Files:** Supports both legacy (.xls) and modern (.xlsx) formats with multi-sheet handling

---

## Support & Documentation

For additional help:
- Check `README.md` for overview and feature summary
- Review `app.log` for detailed operation logs
- Ensure all dependencies are properly installed

---

**Version:** 1.0
**Last Updated:** January 2026
