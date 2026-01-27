# # curve_fitting.py
#
# from PyQt5.QtWidgets import QGroupBox, QFormLayout, QPushButton, QMessageBox, QComboBox
# import numpy as np
# from scipy import stats
# from scipy.optimize import curve_fit
# import logging
#
#
# class CurveFitting(QGroupBox):
#     def __init__(self, parent):
#         super().__init__("Curve Fitting", parent)
#         self.layout = QFormLayout()
#         self.setup_ui()
#
#     def setup_ui(self):
#         self.fit_type = QComboBox()
#         self.fit_type.addItems(['Linear', 'Quadratic', 'Cubic', 'Quartic', 'Quintic','Sextic', 'Septic', 'Octic', 'Nonic','Exponential'])
#         self.layout.addRow("Fit Type:", self.fit_type)
#
#         self.apply_fit_button = QPushButton("Apply Fit")
#         self.apply_fit_button.clicked.connect(self.apply_fit)
#         self.layout.addRow(self.apply_fit_button)
#
#         self.remove_fit_button = QPushButton("Remove Fit")
#         self.remove_fit_button.clicked.connect(self.remove_fit)
#         self.layout.addRow(self.remove_fit_button)
#
#         self.setLayout(self.layout)
#
#     def apply_fit(self):
#         logging.info("Starting curve fitting process")
#         main_window = self.window()
#
#         try:
#             # Check if data is available
#             if main_window.filtered_df is None or main_window.filtered_df.empty:
#                 raise ValueError("No data available for fitting")
#
#             # Get selected columns
#             x_column = main_window.left_panel.axis_selection.x_combo.currentText()
#             y_items = main_window.left_panel.axis_selection.y_list.selectedItems()
#
#             if not y_items:
#                 raise ValueError("No Y-axis selected")
#
#             y_column = y_items[0].text()
#
#             logging.info(f"Selected columns - X: {x_column}, Y: {y_column}")
#
#             # Get data
#             x_data = main_window.filtered_df[x_column].values
#             y_data = main_window.filtered_df[y_column].values
#
#             # Remove any NaN or infinite values
#             mask = np.isfinite(x_data) & np.isfinite(y_data)
#             x_data = x_data[mask]
#             y_data = y_data[mask]
#
#             if len(x_data) == 0 or len(y_data) == 0:
#                 raise ValueError("No valid data points for fitting after removing NaN/inf values")
#
#             fit_type = self.fit_type.currentText()
#
#             if fit_type == 'Linear':
#                 slope, intercept, r_value, p_value, std_err = stats.linregress(x_data, y_data)
#                 fit_func = lambda x: slope * x + intercept
#                 equation = f"y = {slope:.4f}x + {intercept:.4f}"
#                 r_squared = r_value ** 2
#             elif fit_type == 'Quadratic':
#                 popt, _ = curve_fit(self.quadratic_func, x_data, y_data)
#                 fit_func = lambda x: self.quadratic_func(x, *popt)
#                 equation = f"y = {popt[0]:.4f}x^2 + {popt[1]:.4f}x + {popt[2]:.4f}"
#                 r_squared = self.calculate_r_squared(y_data, fit_func(x_data))
#             elif fit_type == 'Cubic':
#                 popt, _ = curve_fit(self.cubic_func, x_data, y_data)
#                 fit_func = lambda x: self.cubic_func(x, *popt)
#                 equation = f"y = {popt[0]:.4f}x^3 + {popt[1]:.4f}x^2 + {popt[2]:.4f}x + {popt[3]:.4f}"
#                 r_squared = self.calculate_r_squared(y_data, fit_func(x_data))
#             elif fit_type == 'Quartic':
#                 popt, _ = curve_fit(self.quartic_func, x_data, y_data)
#                 fit_func = lambda x: self.quartic_func(x, *popt)
#                 equation = f"y = {popt[0]:.4f}x^4 + {popt[1]:.4f}x^3 + {popt[2]:.4f}x^2 + {popt[3]:.4f}x + {popt[4]:.4f}"
#                 r_squared = self.calculate_r_squared(y_data, fit_func(x_data))
#             elif fit_type == 'Quintic':
#                 popt, _ = curve_fit(self.quintic_func, x_data, y_data)
#                 fit_func = lambda x: self.quintic_func(x, *popt)
#                 equation = f"y = {popt[0]:.4f}x^5 + {popt[1]:.4f}x^4 + {popt[2]:.4f}x^3 + {popt[3]:.4f}x^2 + {popt[4]:.4f}x + {popt[5]:.4f}"
#                 r_squared = self.calculate_r_squared(y_data, fit_func(x_data))
#             elif fit_type == 'Exponential':
#                 popt, _ = curve_fit(self.exponential_func, x_data, y_data, p0=[1, 0.1])
#                 fit_func = lambda x: self.exponential_func(x, *popt)
#                 equation = f"y = {popt[0]:.4f} * e^({popt[1]:.4f}x)"
#                 r_squared = self.calculate_r_squared(y_data, fit_func(x_data)),
#             elif fit_type == 'Sextic':
#                 popt, _ = curve_fit(self.sextic_func, x_data, y_data)
#                 fit_func = lambda x: self.sextic_func(x, *popt)
#                 equation = f"y = {popt[0]:.4f}x^6 + {popt[1]:.4f}x^5 + {popt[2]:.4f}x^4 + {popt[3]:.4f}x^3 + {popt[4]:.4f}x^2 + {popt[5]:.4f}x + {popt[6]:.4f}"
#                 r_squared = self.calculate_r_squared(y_data, fit_func(x_data))
#             elif fit_type == 'Septic':
#                 popt, _ = curve_fit(self.septic_func, x_data, y_data)
#                 fit_func = lambda x: self.septic_func(x, *popt)
#                 equation = f"y = {popt[0]:.4f}x^7 + {popt[1]:.4f}x^6 + {popt[2]:.4f}x^5 + {popt[3]:.4f}x^4 + {popt[4]:.4f}x^3 + {popt[5]:.4f}x^2 + {popt[6]:.4f}x + {popt[7]:.4f}"
#                 r_squared = self.calculate_r_squared(y_data, fit_func(x_data))
#             elif fit_type == 'Octic':
#                 popt, _ = curve_fit(self.octic_func, x_data, y_data)
#                 fit_func = lambda x: self.octic_func(x, *popt)
#                 equation = f"y = {popt[0]:.4f}x^8 + {popt[1]:.4f}x^7 + {popt[2]:.4f}x^6 + {popt[3]:.4f}x^5 + {popt[4]:.4f}x^4 + {popt[3]:.4f}x^3 + {popt[6]:.4f}x^2 + {popt[7]:.4f}x + {popt[8]:.4f}"
#                 r_squared = self.calculate_r_squared(y_data, fit_func(x_data))
#             elif fit_type == 'Nonic':
#                 popt, _ = curve_fit(self.nonic_func, x_data, y_data)
#                 fit_func = lambda x: self.nonic_func(x, *popt)
#                 equation = f"y = {popt[0]:.4f}x^9 + {popt[1]:.4f}x^8 + {popt[2]:.4f}x^7 + {popt[3]:.4f}x^6 + {popt[4]:.4f}x^5 + {popt[5]:.4f}x^4 + {popt[6]:.4f}x^3 + {popt[7]:.4f}x^2 + {popt[8]:.4f}x + {popt[9]:.4f}"
#                 r_squared = self.calculate_r_squared(y_data, fit_func(x_data))
#
#             logging.info(f"{fit_type} fit successful. Equation: {equation}")
#
#             # Plot the results
#             main_window.right_panel.plot_area.apply_curve_fitting(x_data, y_data, fit_func, equation, fit_type, x_column, y_column)
#
#             QMessageBox.information(self, "Fit Applied",
#                                     f"Applied {fit_type} fit:\n{equation}\nR-squared: {r_squared:.4f}")
#
#         except Exception as e:
#             logging.exception(f"Error during curve fitting: {str(e)}")
#             QMessageBox.warning(self, "Fit Error", f"Error applying fit: {str(e)}")
#
#     def remove_fit(self):
#         """Remove all curve fits from the plot"""
#         logging.info("Removing curve fits")
#         main_window = self.window()
#
#         try:
#             # Call the plot area's remove_curve_fitting method
#             main_window.right_panel.plot_area.remove_curve_fitting()
#
#             QMessageBox.information(self, "Fit Removed", "All curve fits have been removed from the plot.")
#
#         except Exception as e:
#             logging.exception(f"Error removing curve fit: {str(e)}")
#             QMessageBox.warning(self, "Remove Fit Error", f"Error removing fit: {str(e)}")
#
#     @staticmethod
#     def quadratic_func(x, a, b, c):
#         return a * x ** 2 + b * x + c
#
#     @staticmethod
#     def cubic_func(x, a, b, c, d):
#         return a * x ** 3 + b * x ** 2 + c * x + d
#
#     @staticmethod
#     def quartic_func(x, a, b, c, d, e):
#         return a * x ** 4 + b * x ** 3 + c * x ** 2 + d * x + e
#
#     @staticmethod
#     def quintic_func(x, a, b, c, d, e, f):
#         return a * x ** 5 + b * x ** 4 + c * x ** 3 + d * x ** 2 + e * x + f
#
#     @staticmethod
#     def exponential_func(x, a, b):
#         return a * np.exp(b * x)
#
#     @staticmethod
#     def sextic_func(x, a, b, c, d, e, f, g):
#         return a * x ** 6 + b * x ** 5 + c * x ** 4 + d * x ** 3 + e * x ** 2 + f * x + g
#
#     @staticmethod
#     def septic_func(x, a, b, c, d, e, f, g, h):
#         return a * x ** 7 + b * x ** 6 + c * x ** 5 + d * x ** 4 + e * x ** 3 + f * x ** 2 + g * x + h
#
#     @staticmethod
#     def octic_func(x, a, b, c, d, e, f, g, h, i):
#         return a * x ** 8 + b * x ** 7 + c * x ** 6 + d * x ** 5 + e * x ** 4 + f * x ** 3 + g * x ** 2 + h * x + i
#
#     @staticmethod
#     def nonic_func(x, a, b, c, d, e, f, g, h, i, j):
#         return a * x ** 9 + b * x ** 8 + c * x ** 7 + d * x ** 6 + e * x ** 5 + f * x ** 4 + g * x ** 3 + h * x ** 2 + i * x + j
#
#     @staticmethod
#     # FIXED CODE:
#     def calculate_r_squared(y_true, y_pred):
#         """
#         Calculate R-squared (coefficient of determination).
#
#         Parameters:
#         -----------
#         y_true : array-like
#             True values
#         y_pred : array-like
#             Predicted values
#
#         Returns:
#         --------
#         float : R-squared value, or 0.0 if undefined
#         """
#         ss_res = np.sum((y_true - y_pred) ** 2)
#         ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
#
#         # Handle edge cases
#         if ss_tot == 0:
#             # All y values are identical, RÂ² is undefined
#             # Return 1.0 if perfect fit, 0.0 otherwise
#             if ss_res == 0:
#                 return 1.0
#             else:
#                 return 0.0
#
#         r_squared = 1 - (ss_res / ss_tot)
#
#         # Clip to valid range (can be negative for poor fits)
#         # Return as-is for diagnostic purposes, or clip to [0, 1] if needed
#         return r_squared
#
#     def reset(self):
#         self.fit_type.setCurrentIndex(0)


# curve_fitting.py

from PyQt5.QtWidgets import QGroupBox, QFormLayout, QPushButton, QMessageBox, QComboBox, QSpinBox
import numpy as np
from scipy.optimize import curve_fit
import logging


class CurveFitting(QGroupBox):
    def __init__(self, parent):
        super().__init__("Curve Fitting", parent)
        self.layout = QFormLayout()
        self.setup_ui()

    def setup_ui(self):
        self.fit_type = QComboBox()
        self.fit_type.addItems(['Polynomial', 'Exponential'])
        self.fit_type.currentTextChanged.connect(self.on_fit_type_changed)
        self.layout.addRow("Fit Type:", self.fit_type)

        # Polynomial degree selector
        self.degree_spinbox = QSpinBox()
        self.degree_spinbox.setMinimum(1)
        self.degree_spinbox.setMaximum(15)  # Allow up to 20
        self.degree_spinbox.setValue(1)
        self.degree_spinbox.setToolTip("Degrees above 9 may cause overfitting and numerical instability")
        self.layout.addRow("Polynomial Degree:", self.degree_spinbox)

        self.apply_fit_button = QPushButton("Apply Fit")
        self.apply_fit_button.clicked.connect(self.apply_fit)
        self.layout.addRow(self.apply_fit_button)

        self.remove_fit_button = QPushButton("Remove Fit")
        self.remove_fit_button.clicked.connect(self.remove_fit)
        self.layout.addRow(self.remove_fit_button)

        self.setLayout(self.layout)

    def on_fit_type_changed(self, fit_type):
        """Enable/disable degree selector based on fit type"""
        self.degree_spinbox.setEnabled(fit_type == 'Polynomial')

    def apply_fit(self):
        logging.info("Starting curve fitting process")
        main_window = self.window()

        try:
            # Check if data is available
            if main_window.filtered_df is None or main_window.filtered_df.empty:
                raise ValueError("No data available for fitting")

            # Get selected columns
            x_column = main_window.left_panel.axis_selection.x_combo.currentText()
            y_items = main_window.left_panel.axis_selection.y_list.selectedItems()

            if not y_items:
                raise ValueError("No Y-axis selected")

            y_column = y_items[0].text()

            logging.info(f"Selected columns - X: {x_column}, Y: {y_column}")

            # Get data
            x_data = main_window.filtered_df[x_column].values
            y_data = main_window.filtered_df[y_column].values

            # Remove any NaN or infinite values
            mask = np.isfinite(x_data) & np.isfinite(y_data)
            x_data = x_data[mask]
            y_data = y_data[mask]

            if len(x_data) == 0 or len(y_data) == 0:
                raise ValueError("No valid data points for fitting after removing NaN/inf values")

            fit_type = self.fit_type.currentText()

            if fit_type == 'Polynomial':
                degree = self.degree_spinbox.value()

                # Check if we have enough data points
                if len(x_data) <= degree:
                    raise ValueError(f"Not enough data points for degree {degree} polynomial. "
                                     f"Need at least {degree + 1} points, but only have {len(x_data)} points.")

                # Warning for high-degree polynomials
                if degree > 9:
                    reply = QMessageBox.question(
                        self,
                        "High Degree Warning",
                        f"Degree {degree} polynomial may cause overfitting and numerical instability.\n\n"
                        f"This can result in:\n"
                        f"• Wild oscillations in the fitted curve\n"
                        f"• Unreliable predictions\n"
                        f"• Extreme coefficient values\n\n"
                        f"Consider using a lower degree (1-9) for more stable results.\n\n"
                        f"Continue anyway?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    if reply == QMessageBox.No:
                        logging.info(f"User cancelled degree {degree} polynomial fit")
                        return

                # Fit polynomial using numpy
                try:
                    coeffs = np.polyfit(x_data, y_data, degree)
                    fit_func = np.poly1d(coeffs)
                except np.RankWarning:
                    logging.warning(f"Polynomial fit may be poorly conditioned for degree {degree}")
                    QMessageBox.warning(
                        self,
                        "Fitting Warning",
                        f"The polynomial fit for degree {degree} may be poorly conditioned.\n"
                        f"Results might be unreliable. Consider using a lower degree."
                    )
                    coeffs = np.polyfit(x_data, y_data, degree)
                    fit_func = np.poly1d(coeffs)

                # Generate equation string
                equation = self.generate_polynomial_equation(coeffs, degree)

                # Calculate R-squared
                y_pred = fit_func(x_data)
                r_squared = self.calculate_r_squared(y_data, y_pred)

                fit_type_name = f"Polynomial (degree {degree})"

            elif fit_type == 'Exponential':
                try:
                    popt, _ = curve_fit(self.exponential_func, x_data, y_data, p0=[1, 0.1])
                    fit_func = lambda x: self.exponential_func(x, *popt)
                    equation = f"y = {popt[0]:.4f} * e^({popt[1]:.4f}x)"
                    r_squared = self.calculate_r_squared(y_data, fit_func(x_data))
                    fit_type_name = "Exponential"
                except RuntimeError as e:
                    raise ValueError(
                        f"Exponential fit failed. The data may not follow an exponential pattern. Error: {str(e)}")

            logging.info(f"{fit_type_name} fit successful. Equation: {equation}, R²: {r_squared:.4f}")

            # Plot the results
            main_window.right_panel.plot_area.apply_curve_fitting(
                x_data, y_data, fit_func, equation, fit_type_name, x_column, y_column
            )

            QMessageBox.information(self, "Fit Applied",
                                    f"Applied {fit_type_name} fit:\n\n{equation}\n\nR-squared: {r_squared:.4f}")

        except Exception as e:
            logging.exception(f"Error during curve fitting: {str(e)}")
            QMessageBox.warning(self, "Fit Error", f"Error applying fit:\n\n{str(e)}")

    def remove_fit(self):
        """Remove all curve fits from the plot"""
        logging.info("Removing curve fits")
        main_window = self.window()

        try:
            # Call the plot area's remove_curve_fitting method
            main_window.right_panel.plot_area.remove_curve_fitting()

            QMessageBox.information(self, "Fit Removed", "All curve fits have been removed from the plot.")

        except Exception as e:
            logging.exception(f"Error removing curve fit: {str(e)}")
            QMessageBox.warning(self, "Remove Fit Error", f"Error removing fit: {str(e)}")

    @staticmethod
    def generate_polynomial_equation(coeffs, degree):
        """
        Generate a readable polynomial equation string.

        Parameters:
        -----------
        coeffs : array-like
            Polynomial coefficients from highest to lowest degree
        degree : int
            Degree of the polynomial

        Returns:
        --------
        str : Formatted equation string
        """
        terms = []
        for i, coeff in enumerate(coeffs):
            power = degree - i

            # Skip very small coefficients (near zero)
            if abs(coeff) < 1e-10:
                continue

            # Format the coefficient
            coeff_str = f"{coeff:.4f}"

            # Build term based on power
            if power == 0:
                terms.append(coeff_str)
            elif power == 1:
                if coeff >= 0:
                    terms.append(f"{coeff_str}x")
                else:
                    terms.append(f"{coeff_str}x")
            else:
                if coeff >= 0:
                    terms.append(f"{coeff_str}x^{power}")
                else:
                    terms.append(f"{coeff_str}x^{power}")

        if not terms:
            return "y = 0"

        # Join terms
        equation = "y = " + terms[0]
        for term in terms[1:]:
            if term.startswith('-'):
                equation += f" - {term[1:]}"
            else:
                equation += f" + {term}"

        return equation

    @staticmethod
    def exponential_func(x, a, b):
        """Exponential function: y = a * e^(bx)"""
        return a * np.exp(b * x)

    @staticmethod
    def calculate_r_squared(y_true, y_pred):
        """
        Calculate R-squared (coefficient of determination).

        Parameters:
        -----------
        y_true : array-like
            True values
        y_pred : array-like
            Predicted values

        Returns:
        --------
        float : R-squared value, or 0.0 if undefined
        """
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)

        # Handle edge cases
        if ss_tot == 0:
            # All y values are identical, R² is undefined
            # Return 1.0 if perfect fit, 0.0 otherwise
            if ss_res == 0:
                return 1.0
            else:
                return 0.0

        r_squared = 1 - (ss_res / ss_tot)

        # Return as-is (can be negative for poor fits, which is diagnostic)
        return r_squared

    def reset(self):
        """Reset the curve fitting controls to default values"""
        self.fit_type.setCurrentIndex(0)
        self.degree_spinbox.setValue(1)