#include "curvefittingwidget.h"
#include "mainwindow.h"
#include "leftpanel.h"
#include "rightpanel.h"
#include "axisselection.h"
#include "plotarea.h"
#include "curvefit.h"
#include <QFormLayout>
#include <QMessageBox>

CurveFittingWidget::CurveFittingWidget(QWidget* parent)
    : QGroupBox("Curve Fitting", parent)
{
    setupUi();
}

void CurveFittingWidget::setupUi()
{
    auto* layout = new QVBoxLayout(this);

    // Fit type selection
    auto* typeLabel = new QLabel("Fit Type:", this);
    typeLabel->setStyleSheet("font-weight: bold;");
    layout->addWidget(typeLabel);

    fitType = new QComboBox(this);
    fitType->addItems({"Polynomial", "Exponential"});
    fitType->setToolTip("Select curve fitting method");
    layout->addWidget(fitType);

    // Polynomial degree
    auto* degreeLayout = new QHBoxLayout();
    auto* degreeLabel = new QLabel("Polynomial Degree:", this);
    degreeSpinbox = new QSpinBox(this);
    degreeSpinbox->setRange(1, 15);
    degreeSpinbox->setValue(1);
    degreeSpinbox->setToolTip("Degree of polynomial (1=linear, 2=quadratic, etc.)");
    degreeLayout->addWidget(degreeLabel);
    degreeLayout->addWidget(degreeSpinbox);
    layout->addLayout(degreeLayout);

    // Buttons
    auto* buttonLayout = new QHBoxLayout();

    applyFitButton = new QPushButton("Apply Fit", this);
    applyFitButton->setStyleSheet(R"(
        QPushButton {
            background-color: #27ae60;
            color: white;
            border: none;
            padding: 5px 15px;
            border-radius: 3px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #229954;
        }
        QPushButton:pressed {
            background-color: #1e8449;
        }
    )");

    removeFitButton = new QPushButton("Remove Fit", this);
    removeFitButton->setStyleSheet(R"(
        QPushButton {
            background-color: #e74c3c;
            color: white;
            border: none;
            padding: 5px 15px;
            border-radius: 3px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #cb4335;
        }
        QPushButton:pressed {
            background-color: #b03a2e;
        }
    )");

    buttonLayout->addWidget(applyFitButton);
    buttonLayout->addWidget(removeFitButton);
    layout->addLayout(buttonLayout);

    setLayout(layout);

    // Connections
    connect(fitType, QOverload<int>::of(&QComboBox::currentIndexChanged),
            this, &CurveFittingWidget::onFitTypeChanged);
    connect(applyFitButton, &QPushButton::clicked, this, &CurveFittingWidget::onApplyFit);
    connect(removeFitButton, &QPushButton::clicked, this, &CurveFittingWidget::onRemoveFit);

    // Initial state: degree enabled for polynomial
    onFitTypeChanged(0);
}

void CurveFittingWidget::onFitTypeChanged(int index)
{
    // Enable degree spinbox only for polynomial fit
    degreeSpinbox->setEnabled(index == 0); // 0 = Polynomial
}

void CurveFittingWidget::onApplyFit()
{
    auto* mainWin = qobject_cast<MainWindow*>(window());
    if (!mainWin)
        return;

    if (mainWin->filteredDf.isEmpty()) {
        QMessageBox::warning(this, "No Data", "Please load data before applying curve fitting.");
        return;
    }

    // Get axis selection
    QString xCol = mainWin->leftPanel->axisSelection->xColumn();
    QStringList yCols = mainWin->leftPanel->axisSelection->yColumns();

    if (xCol.isEmpty() || yCols.isEmpty()) {
        QMessageBox::warning(this, "No Selection", "Please select X and Y axis columns first.");
        return;
    }

    // Fit the currently selected partition / branch only.
    DataFrame subset = mainWin->currentSubset();

    // Use first Y column for curve fitting
    QString yCol = yCols.first();
    QVector<double> xData = subset.column(xCol);
    QVector<double> yData = subset.column(yCol);

    if (xData.isEmpty() || yData.isEmpty()) {
        QMessageBox::warning(this, "No Data", "Selected columns contain no data.");
        return;
    }

    QString selectedType = fitType->currentText();
    CurveFit::FitResult result;

    if (selectedType == "Polynomial") {
        int degree = degreeSpinbox->value();

        // Warning for high degrees
        if (degree > 9) {
            auto reply = QMessageBox::warning(this, "High Degree Warning",
                QString("Polynomial degree %1 may cause numerical instability and overfitting. "
                        "Continue?").arg(degree),
                QMessageBox::Yes | QMessageBox::No, QMessageBox::No);
            if (reply == QMessageBox::No)
                return;
        }

        result = CurveFit::polynomialFit(xData, yData, degree);
    } else {
        // Exponential fit
        result = CurveFit::exponentialFit(xData, yData);
    }

    // Apply to plot area
    mainWin->rightPanel->plotArea->applyCurveFitting(
        xData, yData, result.fitFunction, result.equation, selectedType, xCol, yCol);

    // Show result with R-squared
    QMessageBox::information(this, "Fit Applied",
        QString("Applied %1 fit:\n\n%2\n\nR-squared: %3")
            .arg(selectedType)
            .arg(result.equation)
            .arg(result.rSquared, 0, 'f', 4));
}

void CurveFittingWidget::onRemoveFit()
{
    auto* mainWin = qobject_cast<MainWindow*>(window());
    if (mainWin) {
        mainWin->rightPanel->plotArea->removeCurveFitting();
    }
}

void CurveFittingWidget::reset()
{
    fitType->setCurrentIndex(0);
    degreeSpinbox->setValue(1);
}
