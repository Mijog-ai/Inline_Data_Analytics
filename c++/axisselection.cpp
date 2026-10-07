#include "axisselection.h"
#include "mainwindow.h"
#include <QVBoxLayout>
#include <QLabel>
#include <QEvent>

AxisSelection::AxisSelection(QWidget* parent)
    : QGroupBox(parent)
{
    setupUi();
}

void AxisSelection::setupUi()
{
    auto* layout = new QVBoxLayout(this);

    // X-axis selection
    xLabel = new QLabel(this);
    xLabel->setStyleSheet("font-weight: bold;");
    layout->addWidget(xLabel);

    xCombo = new QComboBox(this);
    layout->addWidget(xCombo);

    // Y-axis selection
    yLabel = new QLabel(this);
    yLabel->setStyleSheet("font-weight: bold;");
    layout->addWidget(yLabel);

    yList = new QListWidget(this);
    yList->setSelectionMode(QAbstractItemView::MultiSelection);
    yList->setMaximumHeight(120);
    layout->addWidget(yList);

    setLayout(layout);
    retranslateUi();

    // Connect signals
    connect(xCombo, QOverload<int>::of(&QComboBox::currentIndexChanged),
            this, &AxisSelection::onSelectionChanged);
    connect(yList, &QListWidget::itemSelectionChanged,
            this, &AxisSelection::onYSelectionChanged);
}

void AxisSelection::updateOptions(const QStringList& columns)
{
    // Block signals to avoid triggering plot updates during population
    xCombo->blockSignals(true);
    yList->blockSignals(true);

    xCombo->clear();
    yList->clear();

    xCombo->addItems(columns);
    yList->addItems(columns);

    // Auto-select first column for X if available
    if (!columns.isEmpty()) {
        xCombo->setCurrentIndex(0);
    }

    // Auto-select second column for Y if available
    if (columns.size() > 1) {
        yList->item(1)->setSelected(true);
    }

    xCombo->blockSignals(false);
    yList->blockSignals(false);

    // Trigger initial plot
    onSelectionChanged();
}

void AxisSelection::reset()
{
    xCombo->blockSignals(true);
    yList->blockSignals(true);

    xCombo->clear();
    yList->clear();

    xCombo->blockSignals(false);
    yList->blockSignals(false);
}

QString AxisSelection::xColumn() const
{
    return xCombo->currentText();
}

QStringList AxisSelection::yColumns() const
{
    QStringList selected;
    for (auto* item : yList->selectedItems()) {
        selected.append(item->text());
    }
    return selected;
}

void AxisSelection::onSelectionChanged()
{
    // Find MainWindow parent and call updatePlot
    auto* mainWin = qobject_cast<MainWindow*>(window());
    if (mainWin) {
        mainWin->updatePlot();
    }
}

void AxisSelection::onYSelectionChanged()
{
    limitYSelection();
    onSelectionChanged();
}

void AxisSelection::limitYSelection()
{
    QList<QListWidgetItem*> selected = yList->selectedItems();
    if (selected.size() > MAX_Y_COLUMNS) {
        // Deselect the earliest selected items beyond the limit
        yList->blockSignals(true);
        for (int i = 0; i < selected.size() - MAX_Y_COLUMNS; ++i) {
            selected[i]->setSelected(false);
        }
        yList->blockSignals(false);
    }
}

void AxisSelection::changeEvent(QEvent* event)
{
    if (event->type() == QEvent::LanguageChange)
        retranslateUi();
    QGroupBox::changeEvent(event);
}

void AxisSelection::retranslateUi()
{
    setTitle(tr("Axis Selection"));
    xLabel->setText(tr("X-Axis Column:"));
    xCombo->setToolTip(tr("Select X-axis column"));
    yLabel->setText(tr("Y-Axis Columns (max 3):"));
    yList->setToolTip(tr("Select up to 3 Y-axis columns"));
}
