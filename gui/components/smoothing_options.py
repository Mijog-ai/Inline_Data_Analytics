from PyQt5.QtWidgets import (QGroupBox, QFormLayout, QCheckBox, QComboBox, QSpinBox,
                             QDoubleSpinBox, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
                             QSlider, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


class SmoothingOptions(QGroupBox):
    """Modern and advanced smoothing options with enhanced UI"""

    # Signal emitted when smoothing parameters change
    params_changed = pyqtSignal()

    def __init__(self, parent):
        super().__init__("🎛️ Advanced Smoothing", parent)
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3498db;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        self.layout = QVBoxLayout()
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        # Enable/Disable smoothing
        enable_layout = QHBoxLayout()
        self.smooth_check = QCheckBox("Enable Smoothing")
        self.smooth_check.setFont(QFont("Arial", 10, QFont.Bold))
        enable_layout.addWidget(self.smooth_check)
        enable_layout.addStretch()
        self.layout.addLayout(enable_layout)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        self.layout.addWidget(line)

        # Method selection with descriptions
        method_layout = QVBoxLayout()
        method_label = QLabel("Smoothing Algorithm:")
        method_label.setFont(QFont("Arial", 9, QFont.Bold))
        method_layout.addWidget(method_label)

        self.smooth_method = QComboBox()
        self.smooth_method.addItems([
            'Moving Average',  # Simple and fast
            'Savitzky-Golay',  # Polynomial smoothing
            'Gaussian Filter',  # Gaussian kernel
            'Exponential Moving Avg',  # Weighted recent data
            'Median Filter',  # Robust to outliers
            'Lowess (Local Regression)',  # Non-parametric
            # 'Butterworth Filter',  # Frequency-based
            # 'Bilateral Filter'  # Edge-preserving
        ])
        self.smooth_method.setToolTip("Select smoothing algorithm")
        method_layout.addWidget(self.smooth_method)

        # Method description
        self.method_description = QLabel()
        self.method_description.setWordWrap(True)
        self.method_description.setStyleSheet("color: #7f8c8d; font-size: 8pt; font-style: italic;")
        method_layout.addWidget(self.method_description)
        self.layout.addLayout(method_layout)

        # Separator
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)
        self.layout.addWidget(line2)

        # Parameters form
        self.params_layout = QFormLayout()

        # Window Size (with slider)
        window_container = QVBoxLayout()
        window_header = QHBoxLayout()
        self.window_label = QLabel("Window Size:")
        self.window_value_label = QLabel("51")
        self.window_value_label.setStyleSheet("color: #3498db; font-weight: bold;")
        window_header.addWidget(self.window_label)
        window_header.addStretch()
        window_header.addWidget(self.window_value_label)
        window_container.addLayout(window_header)

        self.window_slider = QSlider(Qt.Horizontal)
        self.window_slider.setRange(3, 501)
        self.window_slider.setValue(51)
        self.window_slider.setSingleStep(2)
        self.window_slider.setPageStep(10)
        self.window_slider.setTickPosition(QSlider.TicksBelow)
        self.window_slider.setTickInterval(50)
        self.window_slider.valueChanged.connect(self.update_window_label)
        window_container.addWidget(self.window_slider)

        self.params_layout.addRow(window_container)

        # Polynomial Order (for Savitzky-Golay)
        self.poly_order = QSpinBox()
        self.poly_order.setRange(1, 10)
        self.poly_order.setValue(3)
        self.poly_order.setToolTip("Order of polynomial for Savitzky-Golay filter")
        self.params_layout.addRow("Polynomial Order:", self.poly_order)

        # Gaussian Sigma (with slider)
        sigma_container = QVBoxLayout()
        sigma_header = QHBoxLayout()
        self.sigma_label = QLabel("Gaussian Sigma:")
        self.sigma_value_label = QLabel("2.0")
        self.sigma_value_label.setStyleSheet("color: #3498db; font-weight: bold;")
        sigma_header.addWidget(self.sigma_label)
        sigma_header.addStretch()
        sigma_header.addWidget(self.sigma_value_label)
        sigma_container.addLayout(sigma_header)

        self.sigma_slider = QSlider(Qt.Horizontal)
        self.sigma_slider.setRange(1, 100)  # Will be divided by 10
        self.sigma_slider.setValue(20)
        self.sigma_slider.setSingleStep(1)
        self.sigma_slider.valueChanged.connect(self.update_sigma_label)
        sigma_container.addWidget(self.sigma_slider)

        self.params_layout.addRow(sigma_container)

        # Alpha (for Exponential Moving Average)
        self.alpha = QDoubleSpinBox()
        self.alpha.setRange(0.01, 1.0)
        self.alpha.setValue(0.3)
        self.alpha.setSingleStep(0.05)
        self.alpha.setDecimals(2)
        self.alpha.setToolTip("Smoothing factor (0.01-1.0). Higher = more responsive")
        self.params_layout.addRow("Alpha (EMA):", self.alpha)

        # Cutoff Frequency (for Butterworth)
        self.cutoff_freq = QDoubleSpinBox()
        self.cutoff_freq.setRange(0.01, 0.5)
        self.cutoff_freq.setValue(0.1)
        self.cutoff_freq.setSingleStep(0.01)
        self.cutoff_freq.setDecimals(3)
        self.cutoff_freq.setToolTip("Cutoff frequency (normalized, 0-0.5)")
        self.params_layout.addRow("Cutoff Frequency:", self.cutoff_freq)

        # Filter Order (for Butterworth)
        self.filter_order = QSpinBox()
        self.filter_order.setRange(1, 10)
        self.filter_order.setValue(4)
        self.filter_order.setToolTip("Order of Butterworth filter")
        self.params_layout.addRow("Filter Order:", self.filter_order)

        # Fraction (for Lowess)
        self.lowess_frac = QDoubleSpinBox()
        self.lowess_frac.setRange(0.01, 1.0)
        self.lowess_frac.setValue(0.1)
        self.lowess_frac.setSingleStep(0.05)
        self.lowess_frac.setDecimals(2)
        self.lowess_frac.setToolTip("Fraction of data to use (0.01-1.0)")
        self.params_layout.addRow("Lowess Fraction:", self.lowess_frac)

        # Spatial Sigma (for Bilateral)
        self.spatial_sigma = QDoubleSpinBox()
        self.spatial_sigma.setRange(0.1, 20.0)
        self.spatial_sigma.setValue(5.0)
        self.spatial_sigma.setSingleStep(0.5)
        self.spatial_sigma.setDecimals(1)
        self.spatial_sigma.setToolTip("Spatial domain sigma")
        self.params_layout.addRow("Spatial Sigma:", self.spatial_sigma)

        # Range Sigma (for Bilateral)
        self.range_sigma = QDoubleSpinBox()
        self.range_sigma.setRange(0.1, 20.0)
        self.range_sigma.setValue(2.0)
        self.range_sigma.setSingleStep(0.5)
        self.range_sigma.setDecimals(1)
        self.range_sigma.setToolTip("Range domain sigma")
        self.params_layout.addRow("Range Sigma:", self.range_sigma)

        self.layout.addLayout(self.params_layout)

        # Separator
        line3 = QFrame()
        line3.setFrameShape(QFrame.HLine)
        line3.setFrameShadow(QFrame.Sunken)
        self.layout.addWidget(line3)

        # Quick presets
        preset_layout = QHBoxLayout()
        preset_label = QLabel("Quick Presets:")
        preset_label.setFont(QFont("Arial", 9, QFont.Bold))
        preset_layout.addWidget(preset_label)

        self.light_button = QPushButton("Light")
        self.light_button.setToolTip("Light smoothing")
        self.light_button.clicked.connect(lambda: self.apply_preset('light'))

        self.medium_button = QPushButton("Medium")
        self.medium_button.setToolTip("Medium smoothing")
        self.medium_button.clicked.connect(lambda: self.apply_preset('medium'))

        self.heavy_button = QPushButton("Heavy")
        self.heavy_button.setToolTip("Heavy smoothing")
        self.heavy_button.clicked.connect(lambda: self.apply_preset('heavy'))

        preset_layout.addWidget(self.light_button)
        preset_layout.addWidget(self.medium_button)
        preset_layout.addWidget(self.heavy_button)
        preset_layout.addStretch()

        self.layout.addLayout(preset_layout)

        self.setLayout(self.layout)

        # Update method description and show/hide relevant parameters
        self.update_method_description()
        self.update_parameter_visibility()

    def connect_signals(self):
        """Connect signals for dynamic updates"""
        self.smooth_check.stateChanged.connect(self.on_smoothing_toggled)
        self.smooth_method.currentIndexChanged.connect(self.update_method_description)
        self.smooth_method.currentIndexChanged.connect(self.update_parameter_visibility)

        # Emit signal when any parameter changes
        self.smooth_check.stateChanged.connect(self.params_changed.emit)
        self.smooth_method.currentIndexChanged.connect(self.params_changed.emit)
        self.window_slider.valueChanged.connect(self.params_changed.emit)
        self.poly_order.valueChanged.connect(self.params_changed.emit)
        self.sigma_slider.valueChanged.connect(self.params_changed.emit)
        self.alpha.valueChanged.connect(self.params_changed.emit)
        self.cutoff_freq.valueChanged.connect(self.params_changed.emit)
        self.filter_order.valueChanged.connect(self.params_changed.emit)
        self.lowess_frac.valueChanged.connect(self.params_changed.emit)
        self.spatial_sigma.valueChanged.connect(self.params_changed.emit)
        self.range_sigma.valueChanged.connect(self.params_changed.emit)

    def update_window_label(self, value):
        """Update window size label"""
        # Ensure odd number
        if value % 2 == 0:
            value += 1
            self.window_slider.setValue(value)
        self.window_value_label.setText(str(value))

    def update_sigma_label(self, value):
        """Update sigma label"""
        sigma_val = value / 10.0
        self.sigma_value_label.setText(f"{sigma_val:.1f}")

    def on_smoothing_toggled(self, state):
        """Enable/disable all controls based on smoothing checkbox"""
        enabled = bool(state)
        self.smooth_method.setEnabled(enabled)
        self.window_slider.setEnabled(enabled)
        self.poly_order.setEnabled(enabled)
        self.sigma_slider.setEnabled(enabled)
        self.alpha.setEnabled(enabled)
        self.cutoff_freq.setEnabled(enabled)
        self.filter_order.setEnabled(enabled)
        self.lowess_frac.setEnabled(enabled)
        self.spatial_sigma.setEnabled(enabled)
        self.range_sigma.setEnabled(enabled)
        self.light_button.setEnabled(enabled)
        self.medium_button.setEnabled(enabled)
        self.heavy_button.setEnabled(enabled)

    def update_method_description(self):
        """Update description based on selected method"""
        descriptions = {
            'Moving Average': 'Simple average over window. Fast, good for uniform noise.',
            'Savitzky-Golay': 'Polynomial smoothing. Preserves peaks and features.',
            'Gaussian Filter': 'Gaussian kernel smoothing. Natural, bell-curved weights.',
            'Exponential Moving Avg': 'Weighted average favoring recent data. Good for trends.',
            'Median Filter': 'Replaces with median value. Excellent for spike removal.',
            'Lowess (Local Regression)': 'Local weighted regression. Adaptive to data.',
            # 'Butterworth Filter': 'Frequency domain filter. Removes high-frequency noise.',
            # 'Bilateral Filter': 'Edge-preserving smoothing. Maintains sharp transitions.'
        }
        method = self.smooth_method.currentText()
        self.method_description.setText(descriptions.get(method, ''))

    def update_parameter_visibility(self):
        """Show/hide parameters based on selected method"""
        method = self.smooth_method.currentText()

        # Hide all first
        self.hide_all_params()

        # Show relevant parameters
        if method == 'Moving Average':
            self.show_param('window')

        elif method == 'Savitzky-Golay':
            self.show_param('window')
            self.show_param('poly_order')

        elif method == 'Gaussian Filter':
            self.show_param('sigma')

        elif method == 'Exponential Moving Avg':
            self.show_param('alpha')

        elif method == 'Median Filter':
            self.show_param('window')

        elif method == 'Lowess (Local Regression)':
            self.show_param('lowess_frac')
        #
        # elif method == 'Butterworth Filter':
        #     self.show_param('cutoff_freq')
        #     self.show_param('filter_order')
        #
        # elif method == 'Bilateral Filter':
        #     self.show_param('spatial_sigma')
        #     self.show_param('range_sigma')

    def hide_all_params(self):
        """Hide all parameter inputs"""
        # Get all widgets in params_layout
        for i in range(self.params_layout.rowCount()):
            label_item = self.params_layout.itemAt(i, QFormLayout.LabelRole)
            field_item = self.params_layout.itemAt(i, QFormLayout.FieldRole)
            if label_item and label_item.widget():
                label_item.widget().hide()
            if field_item:
                if field_item.widget():
                    field_item.widget().hide()
                elif field_item.layout():
                    self.hide_layout(field_item.layout())

    def hide_layout(self, layout):
        """Hide all widgets in a layout"""
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item.widget():
                item.widget().hide()
            elif item.layout():
                self.hide_layout(item.layout())

    def show_param(self, param_name):
        """Show specific parameter input"""
        param_map = {
            'window': 0,
            'poly_order': 1,
            'sigma': 2,
            'alpha': 3,
            'cutoff_freq': 4,
            'filter_order': 5,
            'lowess_frac': 6,
            'spatial_sigma': 7,
            'range_sigma': 8
        }

        if param_name in param_map:
            row = param_map[param_name]
            label_item = self.params_layout.itemAt(row, QFormLayout.LabelRole)
            field_item = self.params_layout.itemAt(row, QFormLayout.FieldRole)

            if label_item and label_item.widget():
                label_item.widget().show()
            if field_item:
                if field_item.widget():
                    field_item.widget().show()
                elif field_item.layout():
                    self.show_layout(field_item.layout())

    def show_layout(self, layout):
        """Show all widgets in a layout"""
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item.widget():
                item.widget().show()
            elif item.layout():
                self.show_layout(item.layout())

    def apply_preset(self, preset_type):
        """Apply quick preset configurations"""
        if preset_type == 'light':
            self.window_slider.setValue(21)
            self.sigma_slider.setValue(10)
            self.alpha.setValue(0.5)
            self.lowess_frac.setValue(0.05)

        elif preset_type == 'medium':
            self.window_slider.setValue(51)
            self.sigma_slider.setValue(20)
            self.alpha.setValue(0.3)
            self.lowess_frac.setValue(0.1)

        elif preset_type == 'heavy':
            self.window_slider.setValue(101)
            self.sigma_slider.setValue(40)
            self.alpha.setValue(0.15)
            self.lowess_frac.setValue(0.2)

    def get_params(self):
        """Get current smoothing parameters"""
        window_val = self.window_slider.value()
        if window_val % 2 == 0:
            window_val += 1

        return {
            'apply': self.smooth_check.isChecked(),
            'method': self.smooth_method.currentText().lower().replace(' ', '_').replace('(', '').replace(')', ''),
            'window_length': window_val,
            'poly_order': self.poly_order.value(),
            'sigma': self.sigma_slider.value() / 10.0,
            'alpha': self.alpha.value(),
            'cutoff_freq': self.cutoff_freq.value(),
            'filter_order': self.filter_order.value(),
            'lowess_frac': self.lowess_frac.value(),
            'spatial_sigma': self.spatial_sigma.value(),
            'range_sigma': self.range_sigma.value()
        }

    def set_params(self, params):
        """Set smoothing parameters"""
        self.smooth_check.setChecked(params.get('apply', False))

        # Map method name to combo box text
        method_map = {
            'moving_average': 'Moving Average',
            'mean_line': 'Moving Average',
            'savitzky-golay': 'Savitzky-Golay',
            'gaussian_filter': 'Gaussian Filter',
            'exponential_moving_avg': 'Exponential Moving Avg',
            'median_filter': 'Median Filter',
            'lowess_local_regression': 'Lowess (Local Regression)',
            # 'butterworth_filter': 'Butterworth Filter',
            # 'bilateral_filter': 'Bilateral Filter'
        }

        method_key = params.get('method', 'moving_average')
        method_text = method_map.get(method_key, 'Moving Average')
        index = self.smooth_method.findText(method_text)
        if index >= 0:
            self.smooth_method.setCurrentIndex(index)

        self.window_slider.setValue(params.get('window_length', 51))
        self.poly_order.setValue(params.get('poly_order', 3))
        self.sigma_slider.setValue(int(params.get('sigma', 2.0) * 10))
        self.alpha.setValue(params.get('alpha', 0.3))
        self.cutoff_freq.setValue(params.get('cutoff_freq', 0.1))
        self.filter_order.setValue(params.get('filter_order', 4))
        self.lowess_frac.setValue(params.get('lowess_frac', 0.1))
        self.spatial_sigma.setValue(params.get('spatial_sigma', 5.0))
        self.range_sigma.setValue(params.get('range_sigma', 2.0))

    def reset(self):
        """Reset to default values"""
        self.smooth_check.setChecked(False)
        self.smooth_method.setCurrentIndex(0)
        self.window_slider.setValue(51)
        self.poly_order.setValue(3)
        self.sigma_slider.setValue(20)
        self.alpha.setValue(0.3)
        self.cutoff_freq.setValue(0.1)
        self.filter_order.setValue(4)
        self.lowess_frac.setValue(0.1)
        self.spatial_sigma.setValue(5.0)
        self.range_sigma.setValue(2.0)

    def clear(self):
        """Clear (same as reset for this component)"""
        self.reset()