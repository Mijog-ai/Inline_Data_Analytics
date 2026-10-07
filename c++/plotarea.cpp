#include "plotarea.h"
#include "smoothing.h"
#include "commentbox.h"
#include "flowlayout.h"

#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QPen>
#include <QPainter>
#include <QMouseEvent>
#include <QWheelEvent>
#include <QGraphicsSceneMouseEvent>
#include <QFileDialog>
#include <QMessageBox>
#include <QInputDialog>
#include <QApplication>
#include <QtCharts/QChart>
#include <QtCharts/QChartView>
#include <QtCharts/QLineSeries>
#include <QtCharts/QValueAxis>

#include <cmath>
#include <algorithm>
#include <limits>

// --- EditableTextItem ---

EditableTextItem::EditableTextItem(const QString& text, QGraphicsItem* parent)
    : QGraphicsTextItem(text, parent)
{
    setFlags(QGraphicsItem::ItemIsMovable | QGraphicsItem::ItemIsSelectable
             | QGraphicsItem::ItemSendsGeometryChanges);

    QFont f("Arial", 9);
    setFont(f);
    setDefaultTextColor(Qt::black);
}

void EditableTextItem::mouseDoubleClickEvent(QGraphicsSceneMouseEvent* event)
{
    if (plotArea)
        plotArea->editTextItem(this);
    event->accept();
}

void EditableTextItem::mousePressEvent(QGraphicsSceneMouseEvent* event)
{
    if (event->button() == Qt::RightButton) {
        if (plotArea)
            plotArea->removeTextItem(this);
        event->accept();
    } else {
        QGraphicsTextItem::mousePressEvent(event);
    }
}

// --- PlotArea ---

PlotArea::PlotArea(QWidget* parent)
    : QWidget(parent)
{
    setupUi();

    undoShortcut = new QShortcut(QKeySequence("Ctrl+Z"), this);
    connect(undoShortcut, &QShortcut::activated, this, &PlotArea::undoLastAction);

    redoShortcut = new QShortcut(QKeySequence("Ctrl+Y"), this);
    connect(redoShortcut, &QShortcut::activated, this, &PlotArea::redoLastAction);
}

void PlotArea::setupUi()
{
    auto* mainLayout = new QVBoxLayout(this);
    mainLayout->setContentsMargins(0, 0, 0, 0);

    createTitleControls();
    mainLayout->addWidget(titleInput->parentWidget() ? titleInput->parentWidget() : titleInput);

    createToolbar();
    // The segment selectors wrap onto their own line when the toolbar plus
    // selectors do not fit (e.g. with the longer German labels).
    auto* toolRow = new QWidget(this);
    auto* toolFlow = new FlowLayout(toolRow, 12, 2);
    toolFlow->addWidget(toolbar);
    toolFlow->addWidget(segmentBar);
    mainLayout->addWidget(toolRow);

    createChart();
    mainLayout->addWidget(chartView, 1);

    createXAxisControls();
    mainLayout->addWidget(xMinInput->parentWidget());

    createLegendArea();
    mainLayout->addWidget(legendWidget);

    setLayout(mainLayout);
    retranslateUi();
}

void PlotArea::changeEvent(QEvent* event)
{
    if (event->type() == QEvent::LanguageChange)
        retranslateUi();
    QWidget::changeEvent(event);
}

void PlotArea::retranslateUi()
{
    titleLabel->setText(tr("Title:"));
    titleInput->setPlaceholderText(tr("Enter plot title..."));
    setTitleButton->setText(tr("Set Title"));

    toolbar->setWindowTitle(tr("Plot Tools"));
    cursorAction->setText(tr("Show Cursor"));
    cursorAction->setToolTip(tr("Toggle crosshair cursor that shows values at mouse position"));
    legendAction->setText(tr("Show Legend"));
    legendAction->setToolTip(tr("Toggle legend visibility"));
    fitAction->setText(tr("Fit to Screen"));
    fitAction->setToolTip(tr("Rescale both axes so the current data fills the view and clear any zoom"));
    highlighterAction->setText(tr("Highlight Mode"));
    highlighterAction->setToolTip(tr("Left-click to add highlight, double-click to remove nearest"));
    insertTextAction->setText(tr("Insert Text"));
    insertTextAction->setToolTip(tr("Click on plot to place text from comment box"));
    clearTextsAction->setText(tr("Clear All Texts"));
    clearTextsAction->setToolTip(tr("Remove all floating text boxes from plot"));
    clearHighlightsAction->setText(tr("Clear Highlights"));
    clearHighlightsAction->setToolTip(tr("Remove all highlight lines"));
    undoAction->setText(tr("Undo"));
    undoAction->setToolTip(tr("Undo last action (Ctrl+Z)"));
    redoAction->setText(tr("Redo"));
    redoAction->setToolTip(tr("Redo last action (Ctrl+Y)"));
    partitionAction->setText(tr("Partition Mode"));
    partitionAction->setToolTip(tr("Left-click to add a vertical divider, double-click to remove nearest"));
    orientCombo->setItemText(0, tr("Vertical"));
    orientCombo->setItemText(1, tr("Horizontal"));
    orientCombo->setToolTip(tr("Orientation of dividers added while Partition Mode is on"));
    clearPartitionsAction->setText(tr("Clear Partitions"));
    clearPartitionsAction->setToolTip(tr("Remove all partition dividers (both orientations)"));
    exportSegmentAction->setText(tr("Export Segment"));
    exportSegmentAction->setToolTip(tr("Export the data of the currently selected partition to CSV (opens in Excel)"));

    branchLabel->setText(tr("  Branch:"));
    branchCombo->setItemText(0, tr("All"));
    branchCombo->setItemText(1, tr("Upstream"));
    branchCombo->setItemText(2, tr("Downstream"));
    branchCombo->setToolTip(tr("Select forward (upstream) or reverse (downstream) branch of a loop"));
    xSegLabel->setText(tr("  X Seg:"));
    partitionCombo->setToolTip(tr("Select a single vertical (x) partition segment to analyse"));
    ySegLabel->setText(tr("  Y Seg:"));
    partitionComboY->setToolTip(tr("Select a single horizontal (y) partition band to analyse"));
    // Rebuilding keeps the current selection and only re-labels the entries.
    rebuildPartitionCombo();
    rebuildPartitionComboY();

    xRangeLabel->setText(tr("X Range:"));
    xMinInput->setPlaceholderText(tr("Min"));
    toLabel->setText(tr("to"));
    xMaxInput->setPlaceholderText(tr("Max"));
    xApplyButton->setText(tr("Apply"));
    xResetButton->setText(tr("Reset"));
}

void PlotArea::createTitleControls()
{
    auto* container = new QWidget(this);
    auto* layout = new QHBoxLayout(container);
    layout->setContentsMargins(0, 0, 0, 0);

    titleLabel = new QLabel(container);
    titleLabel->setStyleSheet("font-weight: bold;");
    layout->addWidget(titleLabel);

    titleInput = new QLineEdit(container);
    layout->addWidget(titleInput, 1);

    setTitleButton = new QPushButton(container);
    setTitleButton->setStyleSheet(R"(
        QPushButton {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 4px 10px;
            border-radius: 3px;
        }
        QPushButton:hover { background-color: #2980b9; }
    )");
    layout->addWidget(setTitleButton);
    container->setLayout(layout);

    connect(setTitleButton, &QPushButton::clicked, this, [this]() {
        saveState();
        currentTitle = titleInput->text();
        if (chart)
            chart->setTitle(currentTitle);
    });

    connect(titleInput, &QLineEdit::returnPressed, this, [this]() {
        setTitleButton->click();
    });
}

void PlotArea::createToolbar()
{
    toolbar = new QToolBar(this);
    toolbar->setIconSize(QSize(16, 16));

    cursorAction = toolbar->addAction(QString());
    cursorAction->setCheckable(true);
    cursorAction->setChecked(false);
    connect(cursorAction, &QAction::toggled, this, &PlotArea::toggleCursor);

    legendAction = toolbar->addAction(QString());
    legendAction->setCheckable(true);
    legendAction->setChecked(true);
    connect(legendAction, &QAction::toggled, this, &PlotArea::toggleLegend);

    fitAction = toolbar->addAction(QString());
    connect(fitAction, &QAction::triggered, this, &PlotArea::fitToScreen);

    highlighterAction = toolbar->addAction(QString());
    highlighterAction->setCheckable(true);
    highlighterAction->setChecked(false);
    connect(highlighterAction, &QAction::toggled, this, &PlotArea::toggleHighlighter);

    toolbar->addSeparator();

    insertTextAction = toolbar->addAction(QString());
    insertTextAction->setCheckable(true);
    insertTextAction->setChecked(false);
    connect(insertTextAction, &QAction::toggled, this, [this](bool checked) {
        if (checked) {
            // Find CommentBox via MainWindow
            auto* mainWin = window();
            CommentBox* commentBox = mainWin->findChild<CommentBox*>();
            if (!commentBox) {
                QMessageBox::warning(this, tr("Error"), tr("Comment box not found."));
                insertTextAction->setChecked(false);
                return;
            }
            QString text = commentBox->getComments();
            if (text.trimmed().isEmpty()) {
                QMessageBox::warning(this, tr("No Text"), tr("Please enter text in the Comments box first."));
                insertTextAction->setChecked(false);
                return;
            }
            textInsertionMode = true;
            pendingText = text;
            highlighterAction->setChecked(false);
        } else {
            cancelTextInsertion();
        }
    });

    clearTextsAction = toolbar->addAction(QString());
    connect(clearTextsAction, &QAction::triggered, this, &PlotArea::clearAllTexts);

    toolbar->addSeparator();

    clearHighlightsAction = toolbar->addAction(QString());
    connect(clearHighlightsAction, &QAction::triggered, this, [this]() {
        saveState();
        clearHighlights();
    });

    toolbar->addSeparator();

    undoAction = toolbar->addAction(QString());
    undoAction->setEnabled(false);
    connect(undoAction, &QAction::triggered, this, &PlotArea::undoLastAction);

    redoAction = toolbar->addAction(QString());
    redoAction->setEnabled(false);
    connect(redoAction, &QAction::triggered, this, &PlotArea::redoLastAction);

    toolbar->addSeparator();

    // --- Partitioning ---
    partitionAction = toolbar->addAction(QString());
    partitionAction->setCheckable(true);
    partitionAction->setChecked(false);
    connect(partitionAction, &QAction::toggled, this, &PlotArea::togglePartitionMode);

    orientCombo = new QComboBox(toolbar);
    orientCombo->addItems({QString(), QString()});
    toolbar->addWidget(orientCombo);
    connect(orientCombo, QOverload<int>::of(&QComboBox::currentIndexChanged),
            this, [this](int idx) { partitionHorizontal = (idx == 1); });

    clearPartitionsAction = toolbar->addAction(QString());
    connect(clearPartitionsAction, &QAction::triggered, this, [this]() {
        if (partitionDividers.isEmpty() && partitionDividersH.isEmpty())
            return;
        saveState();
        clearPartitions();
        emit partitionDividersChanged(partitionDividers);
        emit partitionDividersHChanged(partitionDividersH);
    });

    exportSegmentAction = toolbar->addAction(QString());
    connect(exportSegmentAction, &QAction::triggered, this, [this]() {
        emit exportSegmentRequested();
    });

    // Branch and segment selectors live in their own widget so they can wrap
    // onto a second line next to the toolbar.
    segmentBar = new QWidget(this);
    auto* segLayout = new QHBoxLayout(segmentBar);
    segLayout->setContentsMargins(0, 0, 0, 0);

    branchLabel = new QLabel(segmentBar);
    segLayout->addWidget(branchLabel);
    branchCombo = new QComboBox(segmentBar);
    branchCombo->addItems({QString(), QString(), QString()});
    branchCombo->setEnabled(false);
    segLayout->addWidget(branchCombo);
    connect(branchCombo, QOverload<int>::of(&QComboBox::currentIndexChanged),
            this, [this](int idx) { emit branchChanged(idx); });

    xSegLabel = new QLabel(segmentBar);
    segLayout->addWidget(xSegLabel);
    partitionCombo = new QComboBox(segmentBar);
    partitionCombo->addItem(QString());
    segLayout->addWidget(partitionCombo);
    connect(partitionCombo, QOverload<int>::of(&QComboBox::currentIndexChanged),
            this, [this](int idx) {
        // Index 0 == "All" -> segment -1; otherwise segment index 0-based.
        emit partitionSegmentChanged(idx <= 0 ? -1 : idx - 1);
    });

    ySegLabel = new QLabel(segmentBar);
    segLayout->addWidget(ySegLabel);
    partitionComboY = new QComboBox(segmentBar);
    partitionComboY->addItem(QString());
    segLayout->addWidget(partitionComboY);
    connect(partitionComboY, QOverload<int>::of(&QComboBox::currentIndexChanged),
            this, [this](int idx) {
        emit partitionYSegmentChanged(idx <= 0 ? -1 : idx - 1);
    });
}

void PlotArea::createXAxisControls()
{
    auto* container = new QWidget(this);
    auto* layout = new QHBoxLayout(container);
    layout->setContentsMargins(0, 0, 0, 0);

    xRangeLabel = new QLabel(container);
    xRangeLabel->setStyleSheet("font-weight: bold;");
    layout->addWidget(xRangeLabel);

    xMinInput = new QLineEdit(container);
    xMinInput->setMaximumWidth(80);
    layout->addWidget(xMinInput);

    toLabel = new QLabel(container);
    layout->addWidget(toLabel);

    xMaxInput = new QLineEdit(container);
    xMaxInput->setMaximumWidth(80);
    layout->addWidget(xMaxInput);

    xApplyButton = new QPushButton(container);
    xApplyButton->setStyleSheet(R"(
        QPushButton {
            background-color: #27ae60;
            color: white;
            border: none;
            padding: 4px 10px;
            border-radius: 3px;
        }
        QPushButton:hover { background-color: #229954; }
    )");
    layout->addWidget(xApplyButton);

    xResetButton = new QPushButton(container);
    xResetButton->setStyleSheet(R"(
        QPushButton {
            background-color: #95a5a6;
            color: white;
            border: none;
            padding: 4px 10px;
            border-radius: 3px;
        }
        QPushButton:hover { background-color: #7f8c8d; }
    )");
    layout->addWidget(xResetButton);

    layout->addStretch();
    container->setLayout(layout);

    connect(xApplyButton, &QPushButton::clicked, this, [this]() {
        if (!xAxis) return;
        bool minOk = false, maxOk = false;
        double minVal = xMinInput->text().toDouble(&minOk);
        double maxVal = xMaxInput->text().toDouble(&maxOk);
        if (minOk && maxOk && minVal < maxVal) {
            saveState();
            xAxis->setRange(minVal, maxVal);
        } else {
            QMessageBox::warning(this, tr("Invalid Range"), tr("Please enter valid min and max values."));
        }
    });

    connect(xResetButton, &QPushButton::clicked, this, [this]() {
        if (!xAxis || plotItems.isEmpty()) return;
        double globalMin = std::numeric_limits<double>::max();
        double globalMax = std::numeric_limits<double>::lowest();
        for (const auto& item : plotItems) {
            for (double v : item.xData) {
                globalMin = std::min(globalMin, v);
                globalMax = std::max(globalMax, v);
            }
        }
        if (globalMin < globalMax) {
            double margin = (globalMax - globalMin) * 0.02;
            xAxis->setRange(globalMin - margin, globalMax + margin);
        }
        xMinInput->clear();
        xMaxInput->clear();
    });
}

void PlotArea::createChart()
{
    chart = new QChart();
    chart->setAnimationOptions(QChart::NoAnimation);
    chart->legend()->hide();

    chartView = new QChartView(chart, this);
    chartView->setRenderHint(QPainter::Antialiasing);
    // No rubber-band: a stray click/drag used to zoom into an empty rectangle
    // and blank the plot. Zooming is done with the mouse wheel instead.
    chartView->setRubberBand(QChartView::NoRubberBand);

    chartView->setMouseTracking(true);
    chartView->viewport()->setMouseTracking(true);
    chartView->viewport()->installEventFilter(this);

    xAxis = new QValueAxis(this);
    xAxis->setTitleText("X");
    xAxis->setGridLineVisible(true);
    chart->addAxis(xAxis, Qt::AlignBottom);

    // Keep partition divider lines pinned to their x-values when the view changes.
    connect(xAxis, &QValueAxis::rangeChanged, this, [this](qreal, qreal) {
        updatePartitionLines();
    });
    connect(chart, &QChart::plotAreaChanged, this, [this](const QRectF&) {
        updatePartitionLines();
    });
}

void PlotArea::createLegendArea()
{
    legendWidget = new QWidget(this);
    legendLayout = new QHBoxLayout(legendWidget);
    legendLayout->setContentsMargins(5, 2, 5, 2);
    legendWidget->setLayout(legendLayout);
    legendWidget->setMaximumHeight(30);
}

// ========================================================================
// PLOTTING
// ========================================================================

// NaN-safe min/max — returns false if no valid values exist
static bool finiteMinMax(const QVector<double>& data, double& outMin, double& outMax)
{
    outMin = std::numeric_limits<double>::max();
    outMax = std::numeric_limits<double>::lowest();
    bool found = false;
    for (double v : data) {
        if (!std::isfinite(v)) continue;
        if (v < outMin) outMin = v;
        if (v > outMax) outMax = v;
        found = true;
    }
    return found;
}

// Binary search + interpolation on full data arrays (not downsampled series)
static double findClosestYFromData(const QVector<double>& xData, const QVector<double>& yData, double xVal)
{
    int n = qMin(xData.size(), yData.size());
    if (n == 0)
        return std::numeric_limits<double>::quiet_NaN();

    if (xVal <= xData[0])
        return yData[0];
    if (xVal >= xData[n - 1])
        return yData[n - 1];

    int lo = 0, hi = n - 1;
    while (lo < hi - 1) {
        int mid = (lo + hi) / 2;
        if (xData[mid] < xVal)
            lo = mid;
        else
            hi = mid;
    }

    double x0 = xData[lo], x1 = xData[hi];
    double y0 = yData[lo], y1 = yData[hi];

    if (std::abs(x1 - x0) < 1e-15)
        return y0;

    double t = (xVal - x0) / (x1 - x0);
    return y0 + t * (y1 - y0);
}

// Largest Triangle Three Buckets downsampling — keeps visual shape with far fewer points
static QList<QPointF> downsampleLTTB(const QVector<double>& xData, const QVector<double>& yData, int threshold)
{
    int n = qMin(xData.size(), yData.size());
    if (n <= threshold) {
        QList<QPointF> points;
        points.reserve(n);
        for (int i = 0; i < n; ++i)
            points.append(QPointF(xData[i], yData[i]));
        return points;
    }

    QList<QPointF> sampled;
    sampled.reserve(threshold);

    // Always keep first point
    sampled.append(QPointF(xData[0], yData[0]));

    double bucketSize = static_cast<double>(n - 2) / (threshold - 2);

    int prevSelected = 0;

    for (int bucket = 0; bucket < threshold - 2; ++bucket) {
        int rangeStart = static_cast<int>((bucket + 1) * bucketSize) + 1;
        int rangeEnd = static_cast<int>((bucket + 2) * bucketSize) + 1;
        if (rangeEnd > n - 1) rangeEnd = n - 1;

        // Average of next bucket (for triangle area calculation)
        double avgX = 0, avgY = 0;
        int nextStart = rangeEnd;
        int nextEnd = static_cast<int>((bucket + 3) * bucketSize) + 1;
        if (nextEnd > n) nextEnd = n;
        int nextCount = nextEnd - nextStart;
        if (nextCount <= 0) { nextCount = 1; nextStart = n - 1; nextEnd = n; }
        for (int j = nextStart; j < nextEnd; ++j) {
            avgX += xData[j];
            avgY += yData[j];
        }
        avgX /= nextCount;
        avgY /= nextCount;

        double maxArea = -1;
        int maxIdx = rangeStart;
        double x1 = xData[prevSelected], y1 = yData[prevSelected];

        for (int j = rangeStart; j < rangeEnd; ++j) {
            double area = std::abs((x1 - avgX) * (yData[j] - y1) - (x1 - xData[j]) * (avgY - y1));
            if (area > maxArea) {
                maxArea = area;
                maxIdx = j;
            }
        }

        sampled.append(QPointF(xData[maxIdx], yData[maxIdx]));
        prevSelected = maxIdx;
    }

    // Always keep last point
    sampled.append(QPointF(xData[n - 1], yData[n - 1]));
    return sampled;
}

static QList<QPointF> buildPointList(const QVector<double>& xData, const QVector<double>& yData)
{
    static constexpr int MAX_DISPLAY_POINTS = 5000;

    // Filter out NaN pairs first
    int n = qMin(xData.size(), yData.size());
    QVector<double> cleanX, cleanY;
    cleanX.reserve(n);
    cleanY.reserve(n);
    for (int i = 0; i < n; ++i) {
        if (std::isfinite(xData[i]) && std::isfinite(yData[i])) {
            cleanX.append(xData[i]);
            cleanY.append(yData[i]);
        }
    }

    return downsampleLTTB(cleanX, cleanY, MAX_DISPLAY_POINTS);
}

void PlotArea::plotData(const DataFrame& df, const QString& xColumn, const QStringList& yColumns,
                        const QVariantMap& smoothingParams, const QString& title)
{
    clearPlot();

    if (df.isEmpty() || xColumn.isEmpty() || yColumns.isEmpty())
        return;

    const QVector<double>& xData = df.columnRef(xColumn);
    if (xData.isEmpty())
        return;

    xColumnName = xColumn;
    xAxis->setTitleText(xColumn);

    double xMin, xMax;
    if (!finiteMinMax(xData, xMin, xMax)) return;
    double xMargin = (xMax - xMin) * 0.02;
    if (xMargin == 0) xMargin = 1.0;
    xAxis->setRange(xMin - xMargin, xMax + xMargin);

    bool applySmoothing = smoothingParams.value("apply", false).toBool();
    QString smoothMethod = smoothingParams.value("method", "moving_average").toString();
    int windowLength = smoothingParams.value("window_length", 51).toInt();
    int polyOrder = smoothingParams.value("poly_order", 3).toInt();
    double sigma = smoothingParams.value("sigma", 2.0).toDouble();
    double alphaVal = smoothingParams.value("alpha", 0.3).toDouble();
    double lowessFracVal = smoothingParams.value("lowess_frac", 0.1).toDouble();

    for (int i = 0; i < yColumns.size() && i < NUM_COLORS; ++i) {
        const QString& yCol = yColumns[i];
        const QVector<double>& yData = df.columnRef(yCol);
        if (yData.isEmpty())
            continue;

        QColor color = colors[i % NUM_COLORS];
        PlotItem plotItem;
        plotItem.name = yCol;
        plotItem.color = color;
        plotItem.xData = xData;   // full data kept for findClosestYValue
        plotItem.yData = yData;

        auto* yAx = new QValueAxis(this);
        yAx->setTitleText(yCol);
        yAx->setTitleBrush(QBrush(color));
        yAx->setLabelsColor(color);
        yAx->setGridLineVisible(i == 0);

        double yMin, yMax;
        if (!finiteMinMax(yData, yMin, yMax)) {
            yMin = 0; yMax = 1;
        }
        double yMargin = (yMax - yMin) * 0.05;
        if (yMargin == 0) yMargin = 1.0;
        yAx->setRange(yMin - yMargin, yMax + yMargin);

        Qt::Alignment alignment = (i == 0) ? Qt::AlignLeft : Qt::AlignRight;
        chart->addAxis(yAx, alignment);
        plotItem.yAxis = yAx;

        if (applySmoothing) {
            QVector<double> smoothedData = Smoothing::applySmoothing(
                yData, smoothMethod, windowLength, polyOrder, sigma, alphaVal, lowessFracVal);

            auto* smoothedSeries = new QLineSeries(this);
            smoothedSeries->setName(yCol + " (smoothed)");
            QPen smoothPen(color, 2.5);
            smoothedSeries->setPen(smoothPen);
            smoothedSeries->replace(buildPointList(xData, smoothedData));
            chart->addSeries(smoothedSeries);
            smoothedSeries->attachAxis(xAxis);
            smoothedSeries->attachAxis(yAx);
            plotItem.series = smoothedSeries;

            if (showOriginalData) {
                auto* origSeries = new QLineSeries(this);
                origSeries->setName(yCol + " (original)");
                QColor semiColor = color;
                semiColor.setAlpha(80);
                QPen origPen(semiColor, 1.0);
                origSeries->setPen(origPen);
                origSeries->replace(buildPointList(xData, yData));
                chart->addSeries(origSeries);
                origSeries->attachAxis(xAxis);
                origSeries->attachAxis(yAx);
                plotItem.originalSeries = origSeries;
            }
        } else {
            auto* series = new QLineSeries(this);
            series->setName(yCol);
            QPen pen(color, 2.0);
            series->setPen(pen);
            series->replace(buildPointList(xData, yData));
            chart->addSeries(series);
            series->attachAxis(xAxis);
            series->attachAxis(yAx);
            plotItem.series = series;
        }

        plotItems.append(plotItem);
    }

    if (!title.isEmpty())
        currentTitle = title;
    chart->setTitle(currentTitle);

    updateLegend();
    updatePartitionLines();
}

// ========================================================================
// CURVE FITTING
// ========================================================================

void PlotArea::applyCurveFitting(const QVector<double>& xData, const QVector<double>& yData,
                                  std::function<double(double)> fitFunc, const QString& equation,
                                  const QString& fitType, const QString& xLabel, const QString& yLabel)
{
    Q_UNUSED(yData)

    removeCurveFitting();

    if (!fitFunc || xData.isEmpty())
        return;

    double xMin = *std::min_element(xData.begin(), xData.end());
    double xMax = *std::max_element(xData.begin(), xData.end());
    int numPoints = std::max(200, static_cast<int>(xData.size()) * 2);
    double step = (xMax - xMin) / (numPoints - 1);

    auto* fitSeries = new QLineSeries(this);
    fitSeries->setName(fitType + " Fit: " + equation);

    QPen fitPen(QColor(255, 0, 0), 2.0, Qt::DashLine);
    fitSeries->setPen(fitPen);

    for (int i = 0; i < numPoints; ++i) {
        double x = xMin + i * step;
        double y = fitFunc(x);
        if (std::isfinite(y))
            fitSeries->append(x, y);
    }

    chart->addSeries(fitSeries);
    fitSeries->attachAxis(xAxis);

    if (!plotItems.isEmpty() && plotItems[0].yAxis) {
        fitSeries->attachAxis(plotItems[0].yAxis);
        plotItems[0].fitSeries = fitSeries;
    }

    updateLegend();
}

void PlotArea::removeCurveFitting()
{
    for (auto& item : plotItems) {
        if (item.fitSeries) {
            chart->removeSeries(item.fitSeries);
            delete item.fitSeries;
            item.fitSeries = nullptr;
        }
    }
    updateLegend();
}

// ========================================================================
// CLEAR / EXPORT
// ========================================================================

void PlotArea::clearPlot()
{
    clearHighlights();

    // Drop divider graphics but keep their x-values so they survive a replot.
    for (auto* line : partitionLineItems) {
        if (line && chart->scene()) { chart->scene()->removeItem(line); delete line; }
    }
    partitionLineItems.clear();
    for (auto* lbl : partitionLabelItems) {
        if (lbl && chart->scene()) { chart->scene()->removeItem(lbl); delete lbl; }
    }
    partitionLabelItems.clear();
    for (auto* line : partitionLineItemsH) {
        if (line && chart->scene()) { chart->scene()->removeItem(line); delete line; }
    }
    partitionLineItemsH.clear();
    for (auto* lbl : partitionLabelItemsH) {
        if (lbl && chart->scene()) { chart->scene()->removeItem(lbl); delete lbl; }
    }
    partitionLabelItemsH.clear();

    // Clear floating texts
    for (auto& ft : floatingTextItems) {
        if (ft.item && chart->scene()) {
            chart->scene()->removeItem(ft.item);
            delete ft.item;
        }
    }
    floatingTextItems.clear();

    if (crosshairV) {
        chart->scene()->removeItem(crosshairV);
        delete crosshairV;
        crosshairV = nullptr;
    }
    if (crosshairH) {
        chart->scene()->removeItem(crosshairH);
        delete crosshairH;
        crosshairH = nullptr;
    }
    if (cursorLabel) {
        chart->scene()->removeItem(cursorLabel);
        delete cursorLabel;
        cursorLabel = nullptr;
    }

    chart->removeAllSeries();
    for (auto& item : plotItems) {
        if (item.yAxis) {
            chart->removeAxis(item.yAxis);
            item.series = nullptr;
            item.originalSeries = nullptr;
            item.fitSeries = nullptr;
        }
    }
    plotItems.clear();

    chart->setTitle(QString());
    updateLegend();
}

void PlotArea::setDefaultTitle(const QString& title)
{
    currentTitle = title;
    titleInput->setText(title);
    if (chart)
        chart->setTitle(title);
}

void PlotArea::exportPlot(const QString& fileName)
{
    QString path = fileName;
    if (path.isEmpty()) {
        path = QFileDialog::getSaveFileName(this, "Export Plot", QString(),
                                            "PNG Images (*.png);;JPEG Images (*.jpg);;All Files (*)");
    }
    if (path.isEmpty())
        return;

    // Hide cursor during export
    bool cursorWasVisible = showCursor;
    if (cursorWasVisible) {
        if (crosshairV) crosshairV->setVisible(false);
        if (crosshairH) crosshairH->setVisible(false);
        if (cursorLabel) cursorLabel->setVisible(false);
    }
    QApplication::processEvents();

    // Render at a higher resolution than the on-screen widget so the exported
    // image is crisp. The chart is vector content (lines + text), so rendering
    // the widget through QPainter at a larger scale re-rasterizes everything at
    // full quality instead of upscaling a low-res screen grab.
    const qreal exportScale = 3.0;

    auto renderHiRes = [exportScale](QWidget* w) -> QImage {
        const QSize target = w->size() * exportScale;
        QImage image(target, QImage::Format_ARGB32);
        image.setDevicePixelRatio(1.0);
        image.fill(Qt::white);

        QPainter painter(&image);
        painter.setRenderHint(QPainter::Antialiasing, true);
        painter.setRenderHint(QPainter::TextAntialiasing, true);
        painter.setRenderHint(QPainter::SmoothPixmapTransform, true);
        painter.scale(exportScale, exportScale);
        w->render(&painter, QPoint(), QRegion(), QWidget::DrawChildren);
        painter.end();
        return image;
    };

    QImage plotImage = renderHiRes(chartView);

    // Combine with legend if visible
    if (showLegend && legendWidget->isVisible()) {
        QImage legendImage = renderHiRes(legendWidget);

        const int width = qMax(plotImage.width(), legendImage.width());
        const int totalHeight = plotImage.height() + legendImage.height();
        QImage combined(width, totalHeight, QImage::Format_ARGB32);
        combined.fill(Qt::white);

        QPainter painter(&combined);
        painter.drawImage(0, 0, plotImage);
        painter.drawImage(0, plotImage.height(), legendImage);
        painter.end();

        if (!combined.save(path))
            QMessageBox::critical(this, tr("Export Error"), tr("Failed to save plot image."));
    } else {
        if (!plotImage.save(path))
            QMessageBox::critical(this, tr("Export Error"), tr("Failed to save plot image."));
    }

    // Restore cursor
    if (cursorWasVisible) {
        if (crosshairV) crosshairV->setVisible(true);
        if (crosshairH) crosshairH->setVisible(true);
        if (cursorLabel) cursorLabel->setVisible(true);
    }
}

// ========================================================================
// TOOLBAR TOGGLES
// ========================================================================

void PlotArea::toggleCursor(bool enabled)
{
    showCursor = enabled;

    if (!enabled) {
        if (crosshairV) {
            chart->scene()->removeItem(crosshairV);
            delete crosshairV;
            crosshairV = nullptr;
        }
        if (crosshairH) {
            chart->scene()->removeItem(crosshairH);
            delete crosshairH;
            crosshairH = nullptr;
        }
        if (cursorLabel) {
            chart->scene()->removeItem(cursorLabel);
            delete cursorLabel;
            cursorLabel = nullptr;
        }
    }
}

void PlotArea::toggleLegend(bool enabled)
{
    showLegend = enabled;
    if (legendWidget)
        legendWidget->setVisible(enabled);
}

void PlotArea::toggleHighlighter(bool enabled)
{
    highlighterMode = enabled;
    if (enabled) {
        textInsertionMode = false;
        insertTextAction->setChecked(false);
        partitionMode = false;
        if (partitionAction) partitionAction->setChecked(false);
    }
}

// ========================================================================
// PARTITIONING
// ========================================================================

void PlotArea::togglePartitionMode(bool enabled)
{
    partitionMode = enabled;
    if (enabled) {
        highlighterMode = false;
        if (highlighterAction) highlighterAction->setChecked(false);
        textInsertionMode = false;
        if (insertTextAction) insertTextAction->setChecked(false);
    }
}

void PlotArea::fitToScreen()
{
    if (plotItems.isEmpty() || !xAxis)
        return;

    // X: full extent across all series.
    double xMin, xMax;
    double gMin = std::numeric_limits<double>::max();
    double gMax = std::numeric_limits<double>::lowest();
    for (const auto& item : plotItems) {
        if (finiteMinMax(item.xData, xMin, xMax)) {
            gMin = std::min(gMin, xMin);
            gMax = std::max(gMax, xMax);
        }
    }
    if (gMin < gMax) {
        double margin = (gMax - gMin) * 0.02;
        if (margin == 0) margin = 1.0;
        xAxis->setRange(gMin - margin, gMax + margin);
    }
    xMinInput->clear();
    xMaxInput->clear();

    // Y: each series fitted to its own axis.
    for (const auto& item : plotItems) {
        if (!item.yAxis)
            continue;
        double yMin, yMax;
        if (!finiteMinMax(item.yData, yMin, yMax))
            continue;
        double margin = (yMax - yMin) * 0.05;
        if (margin == 0) margin = 1.0;
        item.yAxis->setRange(yMin - margin, yMax + margin);
    }

    updatePartitionLines();
}

void PlotArea::setBranchAvailable(bool loop)
{
    if (!branchCombo)
        return;
    if (!loop) {
        // Not a loop: force back to "All" and disable the selector.
        if (branchCombo->currentIndex() != 0) {
            branchCombo->blockSignals(true);
            branchCombo->setCurrentIndex(0);
            branchCombo->blockSignals(false);
        }
        branchCombo->setEnabled(false);
    } else {
        branchCombo->setEnabled(true);
    }
}

// Snap a value to the nearest entry of a data array (returns the input unchanged
// when the array is empty).
static double snapToNearest(const QVector<double>& data, double v)
{
    double best = v;
    double bestDist = std::numeric_limits<double>::max();
    for (double d : data) {
        if (!std::isfinite(d)) continue;
        double dist = std::abs(d - v);
        if (dist < bestDist) { bestDist = dist; best = d; }
    }
    return best;
}

void PlotArea::addPartitionDivider(double x)
{
    if (!std::isfinite(x))
        return;

    // Snap to the nearest real data point so the divider sits on actual data.
    if (!plotItems.isEmpty())
        x = snapToNearest(plotItems.first().xData, x);

    // Ignore a divider that effectively duplicates an existing one.
    double tol = 1e-9;
    if (xAxis) {
        double span = xAxis->max() - xAxis->min();
        if (span > 0) tol = span * 1e-4;
    }
    for (double d : partitionDividers) {
        if (std::abs(d - x) <= tol)
            return;
    }

    saveState();
    partitionDividers.append(x);
    std::sort(partitionDividers.begin(), partitionDividers.end());

    updatePartitionLines();
    emit partitionDividersChanged(partitionDividers);
    rebuildPartitionCombo();
}

void PlotArea::removeNearestDivider(double x)
{
    if (partitionDividers.isEmpty())
        return;

    int nearest = -1;
    double best = std::numeric_limits<double>::max();
    for (int i = 0; i < partitionDividers.size(); ++i) {
        double dist = std::abs(partitionDividers[i] - x);
        if (dist < best) { best = dist; nearest = i; }
    }
    if (nearest < 0)
        return;

    saveState();
    partitionDividers.remove(nearest);
    updatePartitionLines();
    emit partitionDividersChanged(partitionDividers);
    rebuildPartitionCombo();
}

void PlotArea::addPartitionDividerH(double y)
{
    if (!std::isfinite(y) || plotItems.isEmpty())
        return;

    // Snap to the nearest real data point on the primary series.
    y = snapToNearest(plotItems.first().yData, y);

    QValueAxis* yAx = plotItems.first().yAxis;
    double tol = 1e-9;
    if (yAx) {
        double span = yAx->max() - yAx->min();
        if (span > 0) tol = span * 1e-4;
    }
    for (double d : partitionDividersH) {
        if (std::abs(d - y) <= tol)
            return;
    }

    saveState();
    partitionDividersH.append(y);
    std::sort(partitionDividersH.begin(), partitionDividersH.end());

    updatePartitionLines();
    emit partitionDividersHChanged(partitionDividersH);
    rebuildPartitionComboY();
}

void PlotArea::removeNearestDividerH(double y)
{
    if (partitionDividersH.isEmpty())
        return;

    int nearest = -1;
    double best = std::numeric_limits<double>::max();
    for (int i = 0; i < partitionDividersH.size(); ++i) {
        double dist = std::abs(partitionDividersH[i] - y);
        if (dist < best) { best = dist; nearest = i; }
    }
    if (nearest < 0)
        return;

    saveState();
    partitionDividersH.remove(nearest);
    updatePartitionLines();
    emit partitionDividersHChanged(partitionDividersH);
    rebuildPartitionComboY();
}

bool PlotArea::removePartitionAtPixel(const QPointF& scenePos)
{
    if (!chart || plotItems.isEmpty())
        return false;

    const double tol = 6.0;   // pixels
    double best = tol;
    int bestV = -1, bestH = -1;

    // Nearest vertical divider by horizontal pixel distance.
    for (int i = 0; i < partitionDividers.size(); ++i) {
        double x = partitionDividers[i];
        if (xAxis && (x < xAxis->min() || x > xAxis->max()))
            continue;
        double px = chart->mapToPosition(QPointF(x, 0)).x();
        double d = std::abs(scenePos.x() - px);
        if (d < best) { best = d; bestV = i; bestH = -1; }
    }

    // Nearest horizontal divider by vertical pixel distance.
    QValueAxis* yAx = plotItems.first().yAxis;
    auto* yRef = plotItems.first().series;
    for (int i = 0; i < partitionDividersH.size(); ++i) {
        double y = partitionDividersH[i];
        if (yAx && (y < yAx->min() || y > yAx->max()))
            continue;
        double py = yRef ? chart->mapToPosition(QPointF(0, y), yRef).y()
                         : chart->mapToPosition(QPointF(0, y)).y();
        double d = std::abs(scenePos.y() - py);
        if (d < best) { best = d; bestH = i; bestV = -1; }
    }

    if (bestV >= 0) {
        saveState();
        partitionDividers.remove(bestV);
        updatePartitionLines();
        emit partitionDividersChanged(partitionDividers);
        rebuildPartitionCombo();
        return true;
    }
    if (bestH >= 0) {
        saveState();
        partitionDividersH.remove(bestH);
        updatePartitionLines();
        emit partitionDividersHChanged(partitionDividersH);
        rebuildPartitionComboY();
        return true;
    }
    return false;
}

void PlotArea::clearPartitions()
{
    partitionDividers.clear();
    partitionDividersH.clear();
    updatePartitionLines();
    rebuildPartitionCombo();
    rebuildPartitionComboY();
}

void PlotArea::applyPartitionState(const QVector<double>& xs, const QVector<double>& ys,
                                   int branchIndex, int xSegment, int ySegment)
{
    // Restore the divider values directly (they were already snapped to real
    // data points when first created, so no re-snapping is needed).
    partitionDividers = xs;
    std::sort(partitionDividers.begin(), partitionDividers.end());
    partitionDividersH = ys;
    std::sort(partitionDividersH.begin(), partitionDividersH.end());

    updatePartitionLines();
    rebuildPartitionCombo();
    rebuildPartitionComboY();

    // Push the dividers to the owner so the active subset is recomputed.
    emit partitionDividersChanged(partitionDividers);
    emit partitionDividersHChanged(partitionDividersH);

    // Restore the branch selection.
    if (branchCombo && branchIndex >= 0 && branchIndex < branchCombo->count()) {
        branchCombo->blockSignals(true);
        branchCombo->setCurrentIndex(branchIndex);
        branchCombo->blockSignals(false);
        emit branchChanged(branchIndex);
    }

    // Restore the selected x-segment (combo index 0 == "All").
    if (partitionCombo) {
        int idx = (xSegment < 0) ? 0 : xSegment + 1;
        if (idx >= 0 && idx < partitionCombo->count()) {
            partitionCombo->blockSignals(true);
            partitionCombo->setCurrentIndex(idx);
            partitionCombo->blockSignals(false);
            emit partitionSegmentChanged(idx <= 0 ? -1 : idx - 1);
        }
    }

    // Restore the selected y-band.
    if (partitionComboY) {
        int idx = (ySegment < 0) ? 0 : ySegment + 1;
        if (idx >= 0 && idx < partitionComboY->count()) {
            partitionComboY->blockSignals(true);
            partitionComboY->setCurrentIndex(idx);
            partitionComboY->blockSignals(false);
            emit partitionYSegmentChanged(idx <= 0 ? -1 : idx - 1);
        }
    }
}

void PlotArea::updatePartitionLines()
{
    if (!chart || !chart->scene())
        return;

    // Remove old graphics (both orientations).
    for (auto* line : partitionLineItems)
        if (line) { chart->scene()->removeItem(line); delete line; }
    partitionLineItems.clear();
    for (auto* lbl : partitionLabelItems)
        if (lbl) { chart->scene()->removeItem(lbl); delete lbl; }
    partitionLabelItems.clear();
    for (auto* line : partitionLineItemsH)
        if (line) { chart->scene()->removeItem(line); delete line; }
    partitionLineItemsH.clear();
    for (auto* lbl : partitionLabelItemsH)
        if (lbl) { chart->scene()->removeItem(lbl); delete lbl; }
    partitionLabelItemsH.clear();

    if (plotItems.isEmpty())
        return;

    QRectF area = chart->plotArea();
    const QColor vColor(41, 128, 185);   // blue for vertical
    const QColor hColor(192, 57, 43);    // red for horizontal
    QPen vPen(vColor, 2, Qt::SolidLine);
    QPen hPen(hColor, 2, Qt::SolidLine);

    // Vertical dividers: value shown on the x-axis (bottom).
    for (int i = 0; i < partitionDividers.size(); ++i) {
        double x = partitionDividers[i];
        if (xAxis && (x < xAxis->min() || x > xAxis->max()))
            continue;
        QPointF pos = chart->mapToPosition(QPointF(x, 0));

        partitionLineItems.append(chart->scene()->addLine(
            pos.x(), area.top(), pos.x(), area.bottom(), vPen));

        auto* lbl = chart->scene()->addSimpleText(
            QString("P%1  x=%2").arg(i + 1).arg(x, 0, 'g', 5));
        lbl->setBrush(QBrush(vColor));
        lbl->setFont(QFont("Arial", 8, QFont::Bold));
        lbl->setPos(pos.x() + 3, area.top() + 2);
        partitionLabelItems.append(lbl);

        // Value pinned near the x-axis.
        auto* axisLbl = chart->scene()->addSimpleText(QString::number(x, 'g', 5));
        axisLbl->setBrush(QBrush(vColor));
        axisLbl->setFont(QFont("Arial", 8));
        axisLbl->setPos(pos.x() + 2, area.bottom() + 2);
        partitionLabelItems.append(axisLbl);
    }

    // Horizontal dividers: positioned/valued against the primary (left) y-axis.
    QValueAxis* yAx = plotItems.first().yAxis;
    auto* yRef = plotItems.first().series;
    for (int i = 0; i < partitionDividersH.size(); ++i) {
        double y = partitionDividersH[i];
        if (yAx && (y < yAx->min() || y > yAx->max()))
            continue;
        QPointF pos = yRef ? chart->mapToPosition(QPointF(0, y), yRef)
                           : chart->mapToPosition(QPointF(0, y));

        partitionLineItemsH.append(chart->scene()->addLine(
            area.left(), pos.y(), area.right(), pos.y(), hPen));

        auto* lbl = chart->scene()->addSimpleText(
            QString("H%1  y=%2").arg(i + 1).arg(y, 0, 'g', 5));
        lbl->setBrush(QBrush(hColor));
        lbl->setFont(QFont("Arial", 8, QFont::Bold));
        lbl->setPos(area.right() - lbl->boundingRect().width() - 4, pos.y() + 2);
        partitionLabelItemsH.append(lbl);

        // Value pinned near the y-axis (left).
        auto* axisLbl = chart->scene()->addSimpleText(QString::number(y, 'g', 5));
        axisLbl->setBrush(QBrush(hColor));
        axisLbl->setFont(QFont("Arial", 8));
        axisLbl->setPos(area.left() - axisLbl->boundingRect().width() - 4, pos.y() - 6);
        partitionLabelItemsH.append(axisLbl);
    }
}

void PlotArea::rebuildPartitionCombo()
{
    if (!partitionCombo)
        return;

    int prev = partitionCombo->currentIndex();
    partitionCombo->blockSignals(true);
    partitionCombo->clear();
    partitionCombo->addItem(tr("All"));
    int segments = partitionDividers.size() + 1;
    if (partitionDividers.isEmpty())
        segments = 0; // no dividers -> only "All"
    for (int i = 0; i < segments; ++i)
        partitionCombo->addItem(tr("Segment %1").arg(i + 1));

    int target = (prev >= 0 && prev < partitionCombo->count()) ? prev : 0;
    partitionCombo->setCurrentIndex(target);
    partitionCombo->blockSignals(false);

    // Only notify when the effective selection actually changed (e.g. the
    // previously selected segment vanished). Merely adding a divider while
    // "All" is selected must NOT trigger a replot that clears annotations.
    if (target != prev)
        emit partitionSegmentChanged(target <= 0 ? -1 : target - 1);
}

void PlotArea::rebuildPartitionComboY()
{
    if (!partitionComboY)
        return;

    int prev = partitionComboY->currentIndex();
    partitionComboY->blockSignals(true);
    partitionComboY->clear();
    partitionComboY->addItem(tr("All"));
    int segments = partitionDividersH.isEmpty() ? 0 : partitionDividersH.size() + 1;
    for (int i = 0; i < segments; ++i)
        partitionComboY->addItem(tr("Band %1").arg(i + 1));

    int target = (prev >= 0 && prev < partitionComboY->count()) ? prev : 0;
    partitionComboY->setCurrentIndex(target);
    partitionComboY->blockSignals(false);

    if (target != prev)
        emit partitionYSegmentChanged(target <= 0 ? -1 : target - 1);
}

// ========================================================================
// MOUSE EVENT HANDLING
// ========================================================================

// Zoom one axis around the fractional position `frac` (0..1 across the axis)
// by `factor` (<1 zooms in, >1 zooms out).
static void zoomAxisRange(QValueAxis* axis, double frac, double factor)
{
    if (!axis) return;
    double lo = axis->min(), hi = axis->max();
    double span = hi - lo;
    if (span <= 0) return;
    double center = lo + frac * span;
    axis->setRange(center - (center - lo) * factor,
                   center + (hi - center) * factor);
}

bool PlotArea::eventFilter(QObject* obj, QEvent* event)
{
    if (obj == chartView->viewport()) {
        if (event->type() == QEvent::Wheel) {
            auto* we = static_cast<QWheelEvent*>(event);
            if (!chart || plotItems.isEmpty())
                return true;

            double factor = we->angleDelta().y() > 0 ? 0.8 : 1.25; // in / out
            QPointF scenePos = chartView->mapToScene(we->position().toPoint());
            QRectF area = chart->plotArea();

            // Fractional cursor position across the plot (y inverted: top=1).
            double fracX = (scenePos.x() - area.left()) / area.width();
            double fracY = (area.bottom() - scenePos.y()) / area.height();

            bool overX = scenePos.y() > area.bottom() &&
                         scenePos.x() >= area.left() && scenePos.x() <= area.right();
            bool overY = scenePos.x() < area.left() &&
                         scenePos.y() >= area.top() && scenePos.y() <= area.bottom();

            if (overX) {
                zoomAxisRange(xAxis, std::clamp(fracX, 0.0, 1.0), factor);
            } else if (overY) {
                for (auto& item : plotItems)
                    zoomAxisRange(item.yAxis, std::clamp(fracY, 0.0, 1.0), factor);
            } else {
                // Over the plot: zoom both, centred on the cursor.
                zoomAxisRange(xAxis, std::clamp(fracX, 0.0, 1.0), factor);
                for (auto& item : plotItems)
                    zoomAxisRange(item.yAxis, std::clamp(fracY, 0.0, 1.0), factor);
            }
            updatePartitionLines();
            return true;
        }
        if (event->type() == QEvent::MouseMove) {
            auto* mouseEvent = static_cast<QMouseEvent*>(event);
            QPointF scenePos = chartView->mapToScene(mouseEvent->pos());
            QPointF chartPos = chart->mapFromScene(scenePos);
            QPointF value = chart->mapToValue(chartPos);
            onMouseMoved(value);
            return false;
        }
        if (event->type() == QEvent::MouseButtonPress) {
            auto* mouseEvent = static_cast<QMouseEvent*>(event);
            if (mouseEvent->button() == Qt::LeftButton && (highlighterMode || textInsertionMode || partitionMode)) {
                QPointF scenePos = chartView->mapToScene(mouseEvent->pos());
                QPointF chartPos = chart->mapFromScene(scenePos);
                QPointF value = chart->mapToValue(chartPos);

                // Use click timer for single/double click disambiguation
                if (highlighterMode || partitionMode) {
                    if (clickTimer && clickTimer->isActive()) {
                        clickTimer->stop();
                        delete clickTimer;
                        clickTimer = nullptr;
                        handleDoubleClick(value);
                    } else {
                        pendingClickValue = value;
                        clickTimer = new QTimer(this);
                        clickTimer->setSingleShot(true);
                        connect(clickTimer, &QTimer::timeout, this, &PlotArea::processPendingClick);
                        clickTimer->start(DOUBLE_CLICK_INTERVAL);
                    }
                } else if (textInsertionMode) {
                    handleLeftClick(value);
                }
                return true;
            }
            if (mouseEvent->button() == Qt::RightButton && textInsertionMode) {
                cancelTextInsertion();
                return true;
            }
            // Right-click directly on a partition line removes that specific line.
            if (mouseEvent->button() == Qt::RightButton && partitionMode) {
                QPointF scenePos = chartView->mapToScene(mouseEvent->pos());
                if (removePartitionAtPixel(scenePos))
                    return true;
            }
        }
        if (event->type() == QEvent::MouseButtonDblClick) {
            // Already handled via timer
            return false;
        }
    }
    return QWidget::eventFilter(obj, event);
}

void PlotArea::processPendingClick()
{
    delete clickTimer;
    clickTimer = nullptr;
    handleLeftClick(pendingClickValue);
}

void PlotArea::handleLeftClick(QPointF valuePos)
{
    if (textInsertionMode) {
        insertFloatingTextAt(valuePos.x(), valuePos.y());
    } else if (partitionMode) {
        if (partitionHorizontal)
            addPartitionDividerH(valuePos.y());
        else
            addPartitionDivider(valuePos.x());
    } else if (highlighterMode) {
        saveState();
        addHighlight(valuePos.x());
    }
}

void PlotArea::handleDoubleClick(QPointF valuePos)
{
    if (partitionMode) {
        if (partitionHorizontal)
            removeNearestDividerH(valuePos.y());
        else
            removeNearestDivider(valuePos.x());
    } else if (highlighterMode) {
        saveState();
        removeNearestHighlight(valuePos.x());
    }
}

void PlotArea::onMouseMoved(QPointF pos)
{
    if (!showCursor || !chart || !chart->scene())
        return;

    QRectF plotArea = chart->plotArea();
    QPointF scenePos = chart->mapToPosition(pos);

    if (!plotArea.contains(scenePos))
        return;

    QPen crosshairPen(QColor(150, 150, 150), 1, Qt::DashLine);

    if (!crosshairV)
        crosshairV = chart->scene()->addLine(QLineF(), crosshairPen);
    crosshairV->setLine(scenePos.x(), plotArea.top(), scenePos.x(), plotArea.bottom());
    crosshairV->setPen(crosshairPen);

    if (!crosshairH)
        crosshairH = chart->scene()->addLine(QLineF(), crosshairPen);
    crosshairH->setLine(plotArea.left(), scenePos.y(), plotArea.right(), scenePos.y());
    crosshairH->setPen(crosshairPen);

    QString labelText = QString("x: %1").arg(pos.x(), 0, 'f', 3);
    for (const auto& item : plotItems) {
        double yVal = findClosestYFromData(item.xData, item.yData, pos.x());
        if (std::isfinite(yVal))
            labelText += QString("\n%1: %2").arg(item.name).arg(yVal, 0, 'f', 3);
    }

    if (!cursorLabel) {
        cursorLabel = chart->scene()->addSimpleText(labelText);
        cursorLabel->setBrush(QBrush(QColor(50, 50, 50)));
        QFont labelFont("Arial", 8);
        cursorLabel->setFont(labelFont);
    }
    cursorLabel->setText(labelText);

    qreal labelX = scenePos.x() + 10;
    qreal labelY = scenePos.y() - 10;
    QRectF labelRect = cursorLabel->boundingRect();
    if (labelX + labelRect.width() > plotArea.right())
        labelX = scenePos.x() - labelRect.width() - 10;
    if (labelY < plotArea.top())
        labelY = plotArea.top() + 5;
    cursorLabel->setPos(labelX, labelY);
}

// ========================================================================
// HIGHLIGHT FUNCTIONALITY
// ========================================================================

void PlotArea::addHighlight(double x)
{
    if (!chart || !chart->scene())
        return;

    QRectF area = chart->plotArea();
    QPointF topPos = chart->mapToPosition(QPointF(x, 0));

    HighlightLine hl;
    hl.xValue = x;

    // Vertical line
    QPen hlPen(QColor(128, 128, 128), 2, Qt::DashLine);
    hl.verticalLine = chart->scene()->addLine(
        topPos.x(), area.top(), topPos.x(), area.bottom(), hlPen);

    // Build legend text
    QString xlabel = xColumnName.isEmpty() ? "X" : xColumnName;
    QString legendText = QString("%1: %2\n").arg(xlabel).arg(x, 0, 'f', 2);
    legendText += QString("-").repeated(30) + "\n";

    for (const auto& item : plotItems) {
        double yVal = findClosestYFromData(item.xData, item.yData, x);
        if (!std::isfinite(yVal))
            continue;

        legendText += QString("%1: %2\n").arg(item.name).arg(yVal, 0, 'f', 2);

        // Scatter dot at intersection
        QPointF intersectScene = chart->mapToPosition(QPointF(x, yVal), item.series);
        auto* dot = chart->scene()->addEllipse(
            intersectScene.x() - 5, intersectScene.y() - 5, 10, 10,
            QPen(Qt::red, 2), QBrush(Qt::red));
        hl.scatterDots.append(dot);

        // Horizontal dashed line from left edge to intersection
        QPen hLinePen(QColor(180, 180, 180), 1, Qt::DashLine);
        auto* hLine = chart->scene()->addLine(
            area.left(), intersectScene.y(), intersectScene.x(), intersectScene.y(), hLinePen);
        hl.horizontalLines.append(hLine);
    }

    // Draggable legend box
    auto* legendBox = new QGraphicsTextItem(legendText.trimmed());
    legendBox->setFont(QFont("Arial", 8));
    legendBox->setDefaultTextColor(Qt::black);
    legendBox->setFlags(QGraphicsItem::ItemIsMovable | QGraphicsItem::ItemIsSelectable);

    // Background for legend box
    QRectF textBounds = legendBox->boundingRect();
    auto* bg = chart->scene()->addRect(textBounds, QPen(Qt::black, 2), QBrush(QColor(255, 255, 255, 230)));
    bg->setParentItem(legendBox);
    bg->setZValue(-1);

    // Position near the clicked point
    double xOffset = (area.width()) * 0.02;
    double yPos = area.top() + 10;
    legendBox->setPos(topPos.x() + xOffset, yPos);

    chart->scene()->addItem(legendBox);
    hl.legendBox = legendBox;

    highlightLines.append(hl);
}

void PlotArea::removeNearestHighlight(double x)
{
    if (highlightLines.isEmpty()) {
        QMessageBox::information(this, tr("No Highlights"), tr("There are no highlights to remove."));
        return;
    }

    double minDist = std::numeric_limits<double>::max();
    int nearestIdx = -1;
    for (int i = 0; i < highlightLines.size(); ++i) {
        double dist = std::abs(highlightLines[i].xValue - x);
        if (dist < minDist) {
            minDist = dist;
            nearestIdx = i;
        }
    }

    if (nearestIdx < 0)
        return;

    auto& hl = highlightLines[nearestIdx];

    if (hl.verticalLine) {
        chart->scene()->removeItem(hl.verticalLine);
        delete hl.verticalLine;
    }
    for (auto* hLine : hl.horizontalLines) {
        chart->scene()->removeItem(hLine);
        delete hLine;
    }
    for (auto* dot : hl.scatterDots) {
        chart->scene()->removeItem(dot);
        delete dot;
    }
    for (auto* label : hl.labels) {
        chart->scene()->removeItem(label);
        delete label;
    }
    if (hl.legendBox) {
        chart->scene()->removeItem(hl.legendBox);
        delete hl.legendBox;
    }

    highlightLines.remove(nearestIdx);
}

void PlotArea::clearHighlights()
{
    if (!chart || !chart->scene())
        return;

    for (auto& hl : highlightLines) {
        if (hl.verticalLine) {
            chart->scene()->removeItem(hl.verticalLine);
            delete hl.verticalLine;
        }
        for (auto* hLine : hl.horizontalLines) {
            chart->scene()->removeItem(hLine);
            delete hLine;
        }
        for (auto* dot : hl.scatterDots) {
            chart->scene()->removeItem(dot);
            delete dot;
        }
        for (auto* label : hl.labels) {
            chart->scene()->removeItem(label);
            delete label;
        }
        if (hl.legendBox) {
            chart->scene()->removeItem(hl.legendBox);
            delete hl.legendBox;
        }
    }
    highlightLines.clear();
}

// ========================================================================
// TEXT INSERTION
// ========================================================================

void PlotArea::insertFloatingTextAt(double x, double y)
{
    saveState();

    auto* textItem = new EditableTextItem(pendingText);
    textItem->setPlotArea(this);

    // Yellow background via HTML
    textItem->setHtml(QString("<div style='background-color: rgba(255,255,0,0.9); "
                              "border: 2px solid black; padding: 4px;'>%1</div>")
                      .arg(pendingText.toHtmlEscaped()));

    QPointF scenePos = chart->mapToPosition(QPointF(x, y));
    textItem->setPos(scenePos);

    chart->scene()->addItem(textItem);

    FloatingText ft;
    ft.item = textItem;
    ft.text = pendingText;
    ft.position = QPointF(x, y);
    floatingTextItems.append(ft);

    textInsertionMode = false;
    pendingText.clear();
    insertTextAction->setChecked(false);
}

void PlotArea::cancelTextInsertion()
{
    textInsertionMode = false;
    pendingText.clear();
    insertTextAction->setChecked(false);
}

void PlotArea::clearAllTexts()
{
    if (floatingTextItems.isEmpty()) {
        QMessageBox::information(this, tr("No Texts"), tr("There are no text boxes to clear."));
        return;
    }

    auto reply = QMessageBox::question(this, tr("Clear All Texts"),
        tr("Are you sure you want to remove all %1 text boxes?").arg(floatingTextItems.size()),
        QMessageBox::Yes | QMessageBox::No, QMessageBox::No);

    if (reply != QMessageBox::Yes)
        return;

    saveState();

    for (auto& ft : floatingTextItems) {
        if (ft.item && chart->scene()) {
            chart->scene()->removeItem(ft.item);
            delete ft.item;
        }
    }
    floatingTextItems.clear();
}

void PlotArea::editTextItem(EditableTextItem* item)
{
    if (!item)
        return;

    QString currentText = item->toPlainText();
    bool ok;
    QString newText = QInputDialog::getText(this, tr("Edit Text"), tr("Enter new text:"),
                                             QLineEdit::Normal, currentText, &ok);
    if (!ok || newText.isEmpty())
        return;

    saveState();

    item->setHtml(QString("<div style='background-color: rgba(255,255,0,0.9); "
                          "border: 2px solid black; padding: 4px;'>%1</div>")
                  .arg(newText.toHtmlEscaped()));

    for (auto& ft : floatingTextItems) {
        if (ft.item == item) {
            ft.text = newText;
            break;
        }
    }
}

void PlotArea::removeTextItem(EditableTextItem* item)
{
    if (!item)
        return;

    saveState();

    if (chart->scene())
        chart->scene()->removeItem(item);

    for (int i = 0; i < floatingTextItems.size(); ++i) {
        if (floatingTextItems[i].item == item) {
            floatingTextItems.remove(i);
            break;
        }
    }

    delete item;
}

// ========================================================================
// UNDO / REDO
// ========================================================================

PlotArea::PlotState PlotArea::captureState() const
{
    PlotState state;
    for (const auto& hl : highlightLines)
        state.highlights.append({hl.xValue});
    for (const auto& ft : floatingTextItems)
        state.floatingTexts.append({ft.text, ft.position});
    state.partitionsV = partitionDividers;
    state.partitionsH = partitionDividersH;
    state.title = currentTitle;

    bool minOk, maxOk;
    state.xRangeMin = xMinInput->text().toDouble(&minOk);
    state.xRangeMax = xMaxInput->text().toDouble(&maxOk);
    if (!minOk) state.xRangeMin = 0;
    if (!maxOk) state.xRangeMax = 0;
    return state;
}

void PlotArea::saveState()
{
    PlotState state = captureState();

    historyStack.append(state);
    if (historyStack.size() > MAX_HISTORY)
        historyStack.removeFirst();

    redoStack.clear();
    updateUndoRedoButtons();
}

void PlotArea::restoreState(const PlotState& state)
{
    // Clear current highlights
    clearHighlights();

    // Clear current floating texts
    for (auto& ft : floatingTextItems) {
        if (ft.item && chart->scene()) {
            chart->scene()->removeItem(ft.item);
            delete ft.item;
        }
    }
    floatingTextItems.clear();

    // Restore highlights
    for (const auto& hlData : state.highlights)
        addHighlight(hlData.x);

    // Restore floating texts
    for (const auto& textData : state.floatingTexts) {
        auto* textItem = new EditableTextItem(textData.text);
        textItem->setPlotArea(this);
        textItem->setHtml(QString("<div style='background-color: rgba(255,255,0,0.9); "
                                  "border: 2px solid black; padding: 4px;'>%1</div>")
                          .arg(textData.text.toHtmlEscaped()));

        QPointF scenePos = chart->mapToPosition(textData.position);
        textItem->setPos(scenePos);
        chart->scene()->addItem(textItem);

        FloatingText ft;
        ft.item = textItem;
        ft.text = textData.text;
        ft.position = textData.position;
        floatingTextItems.append(ft);
    }

    // Restore partition dividers (both orientations) and sync the UI.
    partitionDividers = state.partitionsV;
    partitionDividersH = state.partitionsH;
    updatePartitionLines();
    rebuildPartitionCombo();
    rebuildPartitionComboY();
    emit partitionDividersChanged(partitionDividers);
    emit partitionDividersHChanged(partitionDividersH);

    // Restore title
    currentTitle = state.title;
    titleInput->setText(state.title);
    chart->setTitle(state.title);

    // Restore X range
    if (state.xRangeMin != 0 || state.xRangeMax != 0) {
        xMinInput->setText(QString::number(state.xRangeMin, 'f', 2));
        xMaxInput->setText(QString::number(state.xRangeMax, 'f', 2));
        if (xAxis && state.xRangeMin < state.xRangeMax)
            xAxis->setRange(state.xRangeMin, state.xRangeMax);
    }
}

void PlotArea::undoLastAction()
{
    if (historyStack.isEmpty())
        return;

    // Save current state to redo
    redoStack.append(captureState());

    PlotState prevState = historyStack.takeLast();
    restoreState(prevState);

    updateUndoRedoButtons();
}

void PlotArea::redoLastAction()
{
    if (redoStack.isEmpty())
        return;

    // Save current state to history
    historyStack.append(captureState());

    PlotState nextState = redoStack.takeLast();
    restoreState(nextState);

    updateUndoRedoButtons();
}

void PlotArea::updateUndoRedoButtons()
{
    undoAction->setEnabled(!historyStack.isEmpty());
    redoAction->setEnabled(!redoStack.isEmpty());
}

// ========================================================================
// LEGEND
// ========================================================================

void PlotArea::updateLegend()
{
    QLayoutItem* child;
    while ((child = legendLayout->takeAt(0)) != nullptr) {
        if (child->widget())
            delete child->widget();
        delete child;
    }

    for (const auto& item : plotItems) {
        auto* colorLabel = new QLabel(legendWidget);
        colorLabel->setFixedSize(12, 12);
        colorLabel->setStyleSheet(
            QString("background-color: %1; border-radius: 2px;").arg(item.color.name()));
        legendLayout->addWidget(colorLabel);

        auto* nameLabel = new QLabel(item.name, legendWidget);
        nameLabel->setStyleSheet("font-size: 9pt;");
        legendLayout->addWidget(nameLabel);

        legendLayout->addSpacing(10);

        if (item.fitSeries) {
            auto* fitColorLabel = new QLabel(legendWidget);
            fitColorLabel->setFixedSize(12, 12);
            fitColorLabel->setStyleSheet("background-color: red; border-radius: 2px;");
            legendLayout->addWidget(fitColorLabel);

            auto* fitLabel = new QLabel(item.fitSeries->name(), legendWidget);
            fitLabel->setStyleSheet("font-size: 9pt; color: red;");
            legendLayout->addWidget(fitLabel);

            legendLayout->addSpacing(10);
        }
    }

    legendLayout->addStretch();
    legendWidget->setVisible(showLegend);
}

// ========================================================================
// UTILITY
// ========================================================================

double PlotArea::findClosestYValue(QLineSeries* series, double xVal) const
{
    if (!series || series->count() == 0)
        return std::numeric_limits<double>::quiet_NaN();

    int lo = 0, hi = series->count() - 1;

    if (xVal <= series->at(0).x())
        return series->at(0).y();
    if (xVal >= series->at(hi).x())
        return series->at(hi).y();

    while (lo < hi - 1) {
        int mid = (lo + hi) / 2;
        if (series->at(mid).x() < xVal)
            lo = mid;
        else
            hi = mid;
    }

    double x0 = series->at(lo).x();
    double x1 = series->at(hi).x();
    double y0 = series->at(lo).y();
    double y1 = series->at(hi).y();

    if (std::abs(x1 - x0) < 1e-15)
        return y0;

    double t = (xVal - x0) / (x1 - x0);
    return y0 + t * (y1 - y0);
}
