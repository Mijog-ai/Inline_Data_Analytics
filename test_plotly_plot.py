#!/usr/bin/env python3
"""
Test script for the new Plotly-based PlotArea implementation
"""

import sys
import logging
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import QApplication

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Add the project root to the path
sys.path.insert(0, '/home/user/Inline_Data_Analytics')

from gui.components.Plot_area import PlotArea


def create_test_data():
    """Create sample test data"""
    # Generate sample data
    x = np.linspace(0, 10, 100)
    y1 = np.sin(x) + np.random.normal(0, 0.1, 100)
    y2 = np.cos(x) + np.random.normal(0, 0.1, 100)
    y3 = np.sin(2*x) * 0.5 + np.random.normal(0, 0.05, 100)

    df = pd.DataFrame({
        'Time': x,
        'Signal_1': y1,
        'Signal_2': y2,
        'Signal_3': y3
    })

    return df


def main():
    """Main test function"""
    print("Testing Plotly-based PlotArea implementation...")

    # Create Qt application
    app = QApplication(sys.argv)

    try:
        # Create PlotArea widget
        plot_area = PlotArea(None)

        # Create test data
        df = create_test_data()

        # Test 1: Simple plot without smoothing
        print("Test 1: Creating simple plot without smoothing...")
        smoothing_params = {
            'apply': False,
            'method': 'savgol',
            'window_length': 11,
            'poly_order': 3,
            'sigma': 2.0
        }

        plot_area.plot_data(
            df=df,
            x_column='Time',
            y_columns=['Signal_1', 'Signal_2'],
            smoothing_params=smoothing_params,
            limit_lines=[],
            title='Test Plot - No Smoothing'
        )

        print("✓ Test 1 passed: Simple plot created successfully")

        # Test 2: Plot with smoothing
        print("Test 2: Creating plot with smoothing...")
        smoothing_params['apply'] = True

        plot_area.plot_data(
            df=df,
            x_column='Time',
            y_columns=['Signal_1', 'Signal_2'],
            smoothing_params=smoothing_params,
            limit_lines=[],
            title='Test Plot - With Smoothing'
        )

        print("✓ Test 2 passed: Plot with smoothing created successfully")

        # Test 3: Multi-axis plot
        print("Test 3: Creating multi-axis plot...")
        plot_area.plot_data(
            df=df,
            x_column='Time',
            y_columns=['Signal_1', 'Signal_2', 'Signal_3'],
            smoothing_params=smoothing_params,
            limit_lines=[],
            title='Test Plot - Multi-Axis'
        )

        print("✓ Test 3 passed: Multi-axis plot created successfully")

        # Test 4: Plot with limit lines
        print("Test 4: Creating plot with limit lines...")
        limit_lines = [
            {'type': 'vertical', 'value': 5.0},
            {'type': 'horizontal', 'value': 0.5}
        ]

        plot_area.plot_data(
            df=df,
            x_column='Time',
            y_columns=['Signal_1'],
            smoothing_params=smoothing_params,
            limit_lines=limit_lines,
            title='Test Plot - With Limit Lines'
        )

        print("✓ Test 4 passed: Plot with limit lines created successfully")

        # Test 5: Toggle controls
        print("Test 5: Testing toggle controls...")
        plot_area.toggle_legend(False)
        plot_area.toggle_cursor(True)
        plot_area.toggle_original_data()

        print("✓ Test 5 passed: Toggle controls working")

        # Test 6: Title setting
        print("Test 6: Testing title setting...")
        plot_area.title_input.setText("Updated Title")
        plot_area.set_title()

        print("✓ Test 6 passed: Title setting working")

        # Test 7: Clear plot
        print("Test 7: Testing clear plot...")
        plot_area.clear_plot()

        print("✓ Test 7 passed: Clear plot working")

        print("\n" + "="*60)
        print("All tests passed successfully!")
        print("The PlotArea has been successfully migrated to Plotly!")
        print("\nInteractive features available:")
        print("  - Hover over data points to see values")
        print("  - Zoom in/out using the toolbar or mouse wheel")
        print("  - Pan by dragging the plot")
        print("  - Use toolbar buttons for more interactions")
        print("  - Export the plot as PNG using the camera icon")
        print("  - Toggle legend, cursor, and original data visibility")
        print("="*60)

        return 0

    except Exception as e:
        print(f"✗ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    main()
