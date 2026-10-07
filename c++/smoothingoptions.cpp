#include "smoothingoptions.h"
#include <QFrame>
#include <QFont>
#include <QEvent>

SmoothingOptions::SmoothingOptions(QWidget* parent)
    : QGroupBox(parent)
{
    setStyleSheet(R"(
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
    )");
    setupUi();
    connectSignals();
}

void SmoothingOptions::setupUi()
{
    auto* mainLayout = new QVBoxLayout(this);

    // Enable/Disable smoothing
    auto* enableLayout = new QHBoxLayout();
    smoothCheck = new QCheckBox(this);
    QFont boldFont("Arial", 10, QFont::Bold);
    smoothCheck->setFont(boldFont);
    enableLayout->addWidget(smoothCheck);
    enableLayout->addStretch();
    mainLayout->addLayout(enableLayout);

    // Separator
    auto* line1 = new QFrame(this);
    line1->setFrameShape(QFrame::HLine);
    line1->setFrameShadow(QFrame::Sunken);
    mainLayout->addWidget(line1);

    // Method selection
    auto* methodLayout = new QVBoxLayout();
    methodLabel = new QLabel(this);
    methodLabel->setFont(QFont("Arial", 9, QFont::Bold));
    methodLayout->addWidget(methodLabel);

    smoothMethod = new QComboBox(this);
    smoothMethod->addItems({
        "Moving Average",
        "Savitzky-Golay",
        "Gaussian Filter",
        "Exponential Moving Avg",
        "Median Filter",
        "Lowess (Local Regression)"
    });
    methodLayout->addWidget(smoothMethod);

    methodDescription = new QLabel(this);
    methodDescription->setWordWrap(true);
    methodDescription->setStyleSheet("color: #7f8c8d; font-size: 8pt; font-style: italic;");
    methodLayout->addWidget(methodDescription);
    mainLayout->addLayout(methodLayout);

    // Separator
    auto* line2 = new QFrame(this);
    line2->setFrameShape(QFrame::HLine);
    line2->setFrameShadow(QFrame::Sunken);
    mainLayout->addWidget(line2);

    // Parameters form
    paramsLayout = new QFormLayout();

    // Row 0: Window Size (with slider)
    windowContainer = new QVBoxLayout();
    auto* windowHeader = new QHBoxLayout();
    windowLabel = new QLabel(this);
    windowValueLabel = new QLabel("51", this);
    windowValueLabel->setStyleSheet("color: #3498db; font-weight: bold;");
    windowHeader->addWidget(windowLabel);
    windowHeader->addStretch();
    windowHeader->addWidget(windowValueLabel);
    windowContainer->addLayout(windowHeader);

    windowSlider = new QSlider(Qt::Horizontal, this);
    windowSlider->setRange(3, 501);
    windowSlider->setValue(51);
    windowSlider->setSingleStep(2);
    windowSlider->setPageStep(10);
    windowSlider->setTickPosition(QSlider::TicksBelow);
    windowSlider->setTickInterval(50);
    windowContainer->addWidget(windowSlider);
    paramsLayout->addRow(windowContainer);

    // Row 1: Polynomial Order
    polyOrder = new QSpinBox(this);
    polyOrder->setRange(1, 10);
    polyOrder->setValue(3);
    polyOrderLabel = new QLabel(this);
    paramsLayout->addRow(polyOrderLabel, polyOrder);

    // Row 2: Gaussian Sigma (with slider)
    sigmaContainer = new QVBoxLayout();
    auto* sigmaHeader = new QHBoxLayout();
    sigmaLabel = new QLabel(this);
    sigmaValueLabel = new QLabel("2.0", this);
    sigmaValueLabel->setStyleSheet("color: #3498db; font-weight: bold;");
    sigmaHeader->addWidget(sigmaLabel);
    sigmaHeader->addStretch();
    sigmaHeader->addWidget(sigmaValueLabel);
    sigmaContainer->addLayout(sigmaHeader);

    sigmaSlider = new QSlider(Qt::Horizontal, this);
    sigmaSlider->setRange(1, 100);
    sigmaSlider->setValue(20);
    sigmaSlider->setSingleStep(1);
    sigmaContainer->addWidget(sigmaSlider);
    paramsLayout->addRow(sigmaContainer);

    // Row 3: Alpha (EMA)
    alpha = new QDoubleSpinBox(this);
    alpha->setRange(0.01, 1.0);
    alpha->setValue(0.3);
    alpha->setSingleStep(0.05);
    alpha->setDecimals(2);
    alphaLabel = new QLabel(this);
    paramsLayout->addRow(alphaLabel, alpha);

    // Row 4: Lowess Fraction
    lowessFrac = new QDoubleSpinBox(this);
    lowessFrac->setRange(0.01, 1.0);
    lowessFrac->setValue(0.1);
    lowessFrac->setSingleStep(0.05);
    lowessFrac->setDecimals(2);
    lowessFracLabel = new QLabel(this);
    paramsLayout->addRow(lowessFracLabel, lowessFrac);

    mainLayout->addLayout(paramsLayout);

    // Separator
    auto* line3 = new QFrame(this);
    line3->setFrameShape(QFrame::HLine);
    line3->setFrameShadow(QFrame::Sunken);
    mainLayout->addWidget(line3);

    // Quick presets
    auto* presetLayout = new QHBoxLayout();
    presetLabel = new QLabel(this);
    presetLabel->setFont(QFont("Arial", 9, QFont::Bold));
    presetLayout->addWidget(presetLabel);

    lightButton = new QPushButton(this);
    mediumButton = new QPushButton(this);
    heavyButton = new QPushButton(this);

    presetLayout->addWidget(lightButton);
    presetLayout->addWidget(mediumButton);
    presetLayout->addWidget(heavyButton);
    presetLayout->addStretch();
    mainLayout->addLayout(presetLayout);

    setLayout(mainLayout);
    retranslateUi();

    // Initial state
    updateMethodDescription();
    updateParameterVisibility();
    onSmoothingToggled(Qt::Unchecked);
}

void SmoothingOptions::connectSignals()
{
    connect(smoothCheck, &QCheckBox::stateChanged, this, &SmoothingOptions::onSmoothingToggled);
    connect(smoothMethod, QOverload<int>::of(&QComboBox::currentIndexChanged),
            this, &SmoothingOptions::updateMethodDescription);
    connect(smoothMethod, QOverload<int>::of(&QComboBox::currentIndexChanged),
            this, &SmoothingOptions::updateParameterVisibility);

    // Emit paramsChanged when any parameter changes
    connect(smoothCheck, &QCheckBox::stateChanged, this, &SmoothingOptions::paramsChanged);
    connect(smoothMethod, QOverload<int>::of(&QComboBox::currentIndexChanged),
            this, &SmoothingOptions::paramsChanged);
    connect(windowSlider, &QSlider::valueChanged, this, &SmoothingOptions::paramsChanged);
    connect(windowSlider, &QSlider::valueChanged, this, &SmoothingOptions::updateWindowLabel);
    connect(polyOrder, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &SmoothingOptions::paramsChanged);
    connect(sigmaSlider, &QSlider::valueChanged, this, &SmoothingOptions::paramsChanged);
    connect(sigmaSlider, &QSlider::valueChanged, this, &SmoothingOptions::updateSigmaLabel);
    connect(alpha, QOverload<double>::of(&QDoubleSpinBox::valueChanged),
            this, &SmoothingOptions::paramsChanged);
    connect(lowessFrac, QOverload<double>::of(&QDoubleSpinBox::valueChanged),
            this, &SmoothingOptions::paramsChanged);

    // Preset buttons
    connect(lightButton, &QPushButton::clicked, this, [this]() { applyPreset("light"); });
    connect(mediumButton, &QPushButton::clicked, this, [this]() { applyPreset("medium"); });
    connect(heavyButton, &QPushButton::clicked, this, [this]() { applyPreset("heavy"); });
}

void SmoothingOptions::updateWindowLabel(int value)
{
    // Ensure odd number
    if (value % 2 == 0) {
        value += 1;
        windowSlider->blockSignals(true);
        windowSlider->setValue(value);
        windowSlider->blockSignals(false);
    }
    windowValueLabel->setText(QString::number(value));
}

void SmoothingOptions::updateSigmaLabel(int value)
{
    double sigmaVal = value / 10.0;
    sigmaValueLabel->setText(QString::number(sigmaVal, 'f', 1));
}

void SmoothingOptions::onSmoothingToggled(int state)
{
    bool enabled = (state != Qt::Unchecked);
    smoothMethod->setEnabled(enabled);
    windowSlider->setEnabled(enabled);
    polyOrder->setEnabled(enabled);
    sigmaSlider->setEnabled(enabled);
    alpha->setEnabled(enabled);
    lowessFrac->setEnabled(enabled);
    lightButton->setEnabled(enabled);
    mediumButton->setEnabled(enabled);
    heavyButton->setEnabled(enabled);
}

void SmoothingOptions::updateMethodDescription()
{
    // Keys match the (untranslated) combo item text; descriptions are translated.
    const QMap<QString, QString> descriptions = {
        {"Moving Average", tr("Simple average over window. Fast, good for uniform noise.")},
        {"Savitzky-Golay", tr("Polynomial smoothing. Preserves peaks and features.")},
        {"Gaussian Filter", tr("Gaussian kernel smoothing. Natural, bell-curved weights.")},
        {"Exponential Moving Avg", tr("Weighted average favoring recent data. Good for trends.")},
        {"Median Filter", tr("Replaces with median value. Excellent for spike removal.")},
        {"Lowess (Local Regression)", tr("Local weighted regression. Adaptive to data.")}
    };

    QString method = smoothMethod->currentText();
    methodDescription->setText(descriptions.value(method, QString()));
}

void SmoothingOptions::updateParameterVisibility()
{
    hideAllParams();

    QString method = smoothMethod->currentText();

    if (method == "Moving Average") {
        showParam("window");
    } else if (method == "Savitzky-Golay") {
        showParam("window");
        showParam("poly_order");
    } else if (method == "Gaussian Filter") {
        showParam("sigma");
    } else if (method == "Exponential Moving Avg") {
        showParam("alpha");
    } else if (method == "Median Filter") {
        showParam("window");
    } else if (method == "Lowess (Local Regression)") {
        showParam("lowess_frac");
    }
}

void SmoothingOptions::hideAllParams()
{
    for (int i = 0; i < paramsLayout->rowCount(); ++i) {
        QLayoutItem* labelItem = paramsLayout->itemAt(i, QFormLayout::LabelRole);
        QLayoutItem* fieldItem = paramsLayout->itemAt(i, QFormLayout::FieldRole);

        if (labelItem && labelItem->widget())
            labelItem->widget()->hide();

        if (fieldItem) {
            if (fieldItem->widget()) {
                fieldItem->widget()->hide();
            } else if (fieldItem->layout()) {
                setLayoutVisible(fieldItem->layout(), false);
            }
        }
    }
}

void SmoothingOptions::showParam(const QString& paramName)
{
    static const QMap<QString, int> paramMap = {
        {"window", WindowRow},
        {"poly_order", PolyOrderRow},
        {"sigma", SigmaRow},
        {"alpha", AlphaRow},
        {"lowess_frac", LowessFracRow}
    };

    if (!paramMap.contains(paramName))
        return;

    int row = paramMap[paramName];
    QLayoutItem* labelItem = paramsLayout->itemAt(row, QFormLayout::LabelRole);
    QLayoutItem* fieldItem = paramsLayout->itemAt(row, QFormLayout::FieldRole);

    if (labelItem && labelItem->widget())
        labelItem->widget()->show();

    if (fieldItem) {
        if (fieldItem->widget()) {
            fieldItem->widget()->show();
        } else if (fieldItem->layout()) {
            setLayoutVisible(fieldItem->layout(), true);
        }
    }
}

void SmoothingOptions::setLayoutVisible(QLayout* layout, bool visible)
{
    for (int i = 0; i < layout->count(); ++i) {
        QLayoutItem* item = layout->itemAt(i);
        if (item->widget()) {
            item->widget()->setVisible(visible);
        } else if (item->layout()) {
            setLayoutVisible(item->layout(), visible);
        }
    }
}

void SmoothingOptions::applyPreset(const QString& preset)
{
    if (preset == "light") {
        windowSlider->setValue(21);
        sigmaSlider->setValue(10);
        alpha->setValue(0.5);
        lowessFrac->setValue(0.05);
    } else if (preset == "medium") {
        windowSlider->setValue(51);
        sigmaSlider->setValue(20);
        alpha->setValue(0.3);
        lowessFrac->setValue(0.1);
    } else if (preset == "heavy") {
        windowSlider->setValue(101);
        sigmaSlider->setValue(40);
        alpha->setValue(0.15);
        lowessFrac->setValue(0.2);
    }
}

QVariantMap SmoothingOptions::getParams() const
{
    int windowVal = windowSlider->value();
    if (windowVal % 2 == 0)
        windowVal += 1;

    QString methodKey = smoothMethod->currentText()
        .toLower()
        .replace(' ', '_')
        .replace('(', "")
        .replace(')', "");

    QVariantMap params;
    params["apply"] = smoothCheck->isChecked();
    params["method"] = methodKey;
    params["window_length"] = windowVal;
    params["poly_order"] = polyOrder->value();
    params["sigma"] = sigmaSlider->value() / 10.0;
    params["alpha"] = alpha->value();
    params["lowess_frac"] = lowessFrac->value();
    return params;
}

void SmoothingOptions::setParams(const QVariantMap& params)
{
    static const QMap<QString, QString> methodMap = {
        {"moving_average", "Moving Average"},
        {"mean_line", "Moving Average"},
        {"savitzky-golay", "Savitzky-Golay"},
        {"gaussian_filter", "Gaussian Filter"},
        {"exponential_moving_avg", "Exponential Moving Avg"},
        {"median_filter", "Median Filter"},
        {"lowess_local_regression", "Lowess (Local Regression)"}
    };

    smoothCheck->setChecked(params.value("apply", false).toBool());

    QString methodKey = params.value("method", "moving_average").toString();
    QString methodText = methodMap.value(methodKey, "Moving Average");
    int index = smoothMethod->findText(methodText);
    if (index >= 0)
        smoothMethod->setCurrentIndex(index);

    windowSlider->setValue(params.value("window_length", 51).toInt());
    polyOrder->setValue(params.value("poly_order", 3).toInt());
    sigmaSlider->setValue(static_cast<int>(params.value("sigma", 2.0).toDouble() * 10));
    alpha->setValue(params.value("alpha", 0.3).toDouble());
    lowessFrac->setValue(params.value("lowess_frac", 0.1).toDouble());
}

void SmoothingOptions::reset()
{
    smoothCheck->setChecked(false);
    smoothMethod->setCurrentIndex(0);
    windowSlider->setValue(51);
    polyOrder->setValue(3);
    sigmaSlider->setValue(20);
    alpha->setValue(0.3);
    lowessFrac->setValue(0.1);
}

void SmoothingOptions::changeEvent(QEvent* event)
{
    if (event->type() == QEvent::LanguageChange)
        retranslateUi();
    QGroupBox::changeEvent(event);
}

void SmoothingOptions::retranslateUi()
{
    setTitle(tr("Advanced Smoothing"));
    smoothCheck->setText(tr("Enable Smoothing"));
    methodLabel->setText(tr("Smoothing Algorithm:"));
    smoothMethod->setToolTip(tr("Select smoothing algorithm"));
    windowLabel->setText(tr("Window Size:"));
    polyOrderLabel->setText(tr("Polynomial Order:"));
    polyOrder->setToolTip(tr("Order of polynomial for Savitzky-Golay filter"));
    sigmaLabel->setText(tr("Gaussian Sigma:"));
    alphaLabel->setText(tr("Alpha (EMA):"));
    alpha->setToolTip(tr("Smoothing factor (0.01-1.0). Higher = more responsive"));
    lowessFracLabel->setText(tr("Lowess Fraction:"));
    lowessFrac->setToolTip(tr("Fraction of data to use (0.01-1.0)"));
    presetLabel->setText(tr("Quick Presets:"));
    lightButton->setText(tr("Light"));
    lightButton->setToolTip(tr("Light smoothing"));
    mediumButton->setText(tr("Medium"));
    mediumButton->setToolTip(tr("Medium smoothing"));
    heavyButton->setText(tr("Heavy"));
    heavyButton->setToolTip(tr("Heavy smoothing"));
    updateMethodDescription();
}
