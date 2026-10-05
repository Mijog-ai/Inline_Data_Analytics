#include "datafilter.h"
#include "mainwindow.h"
#include <QFormLayout>
#include <QMessageBox>
#include <limits>

DataFilter::DataFilter(QWidget* parent)
    : QGroupBox("Data Filter", parent)
{
    setupUi();
}

void DataFilter::setupUi()
{
    auto* layout = new QVBoxLayout(this);

    // Filter column selection
    auto* columnLabel = new QLabel("Filter Column:", this);
    columnLabel->setStyleSheet("font-weight: bold;");
    layout->addWidget(columnLabel);

    filterColumn = new QComboBox(this);
    filterColumn->setToolTip("Select column to filter");
    layout->addWidget(filterColumn);

    // Min/Max value inputs
    auto* rangeLayout = new QFormLayout();

    minValue = new QLineEdit(this);
    minValue->setPlaceholderText("Minimum value");
    minValue->setToolTip("Enter minimum value (leave empty for no lower bound)");
    rangeLayout->addRow("Min Value:", minValue);

    maxValue = new QLineEdit(this);
    maxValue->setPlaceholderText("Maximum value");
    maxValue->setToolTip("Enter maximum value (leave empty for no upper bound)");
    rangeLayout->addRow("Max Value:", maxValue);

    layout->addLayout(rangeLayout);

    // Apply button
    applyFilter = new QPushButton("Apply Filter", this);
    applyFilter->setToolTip("Apply the data filter");
    applyFilter->setStyleSheet(R"(
        QPushButton {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 5px 15px;
            border-radius: 3px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #2980b9;
        }
        QPushButton:pressed {
            background-color: #2471a3;
        }
    )");
    layout->addWidget(applyFilter);

    setLayout(layout);

    connect(applyFilter, &QPushButton::clicked, this, &DataFilter::onApplyClicked);
}

void DataFilter::updateColumns(const QStringList& columns)
{
    filterColumn->blockSignals(true);
    filterColumn->clear();
    filterColumn->addItems(columns);
    filterColumn->blockSignals(false);
}

void DataFilter::setFilter(const QString& column, const QString& minVal, const QString& maxVal)
{
    int index = filterColumn->findText(column);
    if (index >= 0)
        filterColumn->setCurrentIndex(index);
    minValue->setText(minVal);
    maxValue->setText(maxVal);
}

void DataFilter::reset()
{
    filterColumn->blockSignals(true);
    filterColumn->clear();
    filterColumn->blockSignals(false);
    minValue->clear();
    maxValue->clear();
}

void DataFilter::onApplyClicked()
{
    QString column = filterColumn->currentText();
    if (column.isEmpty())
        return;

    bool minOk = true, maxOk = true;
    double minVal = -std::numeric_limits<double>::infinity();
    double maxVal = std::numeric_limits<double>::infinity();

    if (!minValue->text().trimmed().isEmpty()) {
        minVal = minValue->text().toDouble(&minOk);
        if (!minOk) {
            QMessageBox::warning(this, "Invalid Input", "Minimum value is not a valid number.");
            return;
        }
    }

    if (!maxValue->text().trimmed().isEmpty()) {
        maxVal = maxValue->text().toDouble(&maxOk);
        if (!maxOk) {
            QMessageBox::warning(this, "Invalid Input", "Maximum value is not a valid number.");
            return;
        }
    }

    if (minVal > maxVal) {
        QMessageBox::warning(this, "Invalid Range", "Minimum value cannot be greater than maximum value.");
        return;
    }

    // Find MainWindow parent and apply filter
    auto* mainWin = qobject_cast<MainWindow*>(window());
    if (mainWin) {
        mainWin->applyDataFilter(column, minVal, maxVal);
    }
}
