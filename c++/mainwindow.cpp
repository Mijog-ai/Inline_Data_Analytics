#include "mainwindow.h"
#include "leftpanel.h"
#include "rightpanel.h"
#include "menubar.h"
#include "toolbar.h"
#include "axisselection.h"
#include "smoothingoptions.h"
#include "datafilter.h"
#include "curvefittingwidget.h"
#include "commentbox.h"
#include "plotarea.h"
#include "statisticsarea.h"
#include "sessionmanager.h"
#include "presetmanager.h"
#include "sheetselectiondialog.h"
#include "fileloaders.h"

#include <QHBoxLayout>
#include <QFileDialog>
#include <QMessageBox>
#include <QMimeData>
#include <QFileInfo>
#include <QFile>
#include <QTextStream>
#include <QDialog>
#include <QLoggingCategory>
#include <QApplication>
#include <QElapsedTimer>
#include <limits>
#include <algorithm>
#include <cmath>

static Q_LOGGING_CATEGORY(lcMainWindow, "app.mainwindow")

MainWindow::MainWindow(QWidget* parent)
    : QMainWindow(parent)
{
    setGeometry(100, 100, 1600, 900);

    auto* centralWidget = new QWidget(this);
    setCentralWidget(centralWidget);
    auto* layout = new QHBoxLayout(centralWidget);

    setupMenuBar();
    setupUi();
    setupEditActions();

    setAcceptDrops(true);

    sessionManager = new SessionManager(this);
    presetManager = new PresetManager(this);
    appToolBar->refreshPresetList();

    // Connect smoothing parameter changes to auto-replot
    connect(leftPanel->smoothingOptions, &SmoothingOptions::paramsChanged,
            this, [this]() {
        if (df.isEmpty())
            return;

        QString xCol = leftPanel->axisSelection->xColumn();
        QStringList yCols = leftPanel->axisSelection->yColumns();

        if (xCol.isEmpty() || yCols.isEmpty())
            return;

        updatePlot(false);
    });

    // Partition / branch controls live in the plot area; route their changes
    // back here so the active subset is recomputed and everything replots.
    connect(rightPanel->plotArea, &PlotArea::partitionDividersChanged,
            this, &MainWindow::onPartitionDividersChanged);
    connect(rightPanel->plotArea, &PlotArea::branchChanged,
            this, &MainWindow::setActiveBranch);
    connect(rightPanel->plotArea, &PlotArea::partitionSegmentChanged,
            this, &MainWindow::setActivePartition);
    connect(rightPanel->plotArea, &PlotArea::partitionDividersHChanged,
            this, &MainWindow::onPartitionDividersHChanged);
    connect(rightPanel->plotArea, &PlotArea::partitionYSegmentChanged,
            this, &MainWindow::setActivePartitionY);
    connect(rightPanel->plotArea, &PlotArea::exportSegmentRequested,
            this, &MainWindow::exportCurrentSubset);

    layout->addWidget(leftPanel, 1);
    layout->addWidget(rightPanel, 4);
}

void MainWindow::setupMenuBar()
{
    appMenuBar = new MenuBar(this);
    setMenuBar(appMenuBar);
}

void MainWindow::setupUi()
{
    appToolBar = new ToolBar(this);
    addToolBar(appToolBar);

    leftPanel = new LeftPanel(this);
    rightPanel = new RightPanel(this);
}

void MainWindow::setupEditActions()
{
    showSmoothingAction = new QAction(this);
    showSmoothingAction->setCheckable(true);
    connect(showSmoothingAction, &QAction::triggered, this, [this](bool checked) {
        leftPanel->smoothingOptions->setVisible(checked);
    });

    showCommentAction = new QAction(this);
    showCommentAction->setCheckable(true);
    connect(showCommentAction, &QAction::triggered, this, [this](bool checked) {
        leftPanel->commentBox->setVisible(checked);
    });

    showFilterAction = new QAction(this);
    showFilterAction->setCheckable(true);
    connect(showFilterAction, &QAction::triggered, this, [this](bool checked) {
        leftPanel->dataFilter->setVisible(checked);
    });

    showCurveFitAction = new QAction(this);
    showCurveFitAction->setCheckable(true);
    connect(showCurveFitAction, &QAction::triggered, this, [this](bool checked) {
        leftPanel->curveFitting->setVisible(checked);
    });

    appMenuBar->addEditActions(showSmoothingAction, showCommentAction,
                               showFilterAction, showCurveFitAction);
    retranslateUi();
}

void MainWindow::changeEvent(QEvent* event)
{
    if (event->type() == QEvent::LanguageChange)
        retranslateUi();
    QMainWindow::changeEvent(event);
}

void MainWindow::retranslateUi()
{
    setWindowTitle(tr("Inline Analytical Tool"));
    showSmoothingAction->setText(tr("Smoothing_options"));
    showCommentAction->setText(tr("Add_Comment_plot"));
    showFilterAction->setText(tr("Data_Filter_plotter"));
    showCurveFitAction->setText(tr("Curve Fitting"));
}

void MainWindow::clearAllData()
{
    df = DataFrame();
    originalDf = DataFrame();
    filteredDf = DataFrame();
    unsavedChanges = false;
    partitionDividers.clear();
    partitionDividersH.clear();
    activePartition = -1;
    activePartitionY = -1;
    activeBranch = BranchAll;
}

void MainWindow::resetUi()
{
    // Reset LeftPanel
    leftPanel->axisSelection->updateOptions({});
    leftPanel->smoothingOptions->reset();
    leftPanel->dataFilter->reset();
    leftPanel->curveFitting->reset();
    leftPanel->commentBox->clear();

    // Reset RightPanel - clear plot first to prevent errors
    rightPanel->plotArea->clearPartitions();
    rightPanel->plotArea->clearPlot();
    rightPanel->statisticsArea->clearStats();
    partitionDividers.clear();
    partitionDividersH.clear();
    activePartition = -1;
    activePartitionY = -1;
    activeBranch = BranchAll;

    // Reset toolbar file name
    appToolBar->updateFileName(QString());
    currentFile.clear();
}

void MainWindow::loadFile(const QString& filePath)
{
    QString path = filePath;

    qCInfo(lcMainWindow) << "loadFile method called";

    if (path.isEmpty()) {
        path = QFileDialog::getOpenFileName(
            this, tr("Open File"), QString(),
            tr("All Files (*);;ASC Files (*.asc);;CSV Files (*.csv);;"
               "TDMS Files (*.tdms);;Excel Files (*.xlsx *.xlsm *.xls)"));
    }

    if (path.isEmpty()) {
        qCInfo(lcMainWindow) << "File loading cancelled by user";
        return;
    }

    qCInfo(lcMainWindow) << "File selected:" << path;

    try {
        QFileInfo fi(path);
        QString ext = fi.suffix().toLower();

        const bool isExcel = (ext == "xlsx" || ext == "xlsm" || ext == "xls");
        if (!isExcel && ext != "asc" && ext != "csv" && ext != "tdms") {
            QMessageBox::critical(this, tr("Error"),
                                  tr("Unsupported file type: %1").arg(ext));
            return;
        }

        // Pick the Excel sheet before showing the wait cursor
        QString excelSheet;
        if (isExcel) {
            QStringList sheetNames = FileLoaders::getExcelSheets(path);

            if (sheetNames.isEmpty()) {
                QMessageBox::critical(this, tr("Error"), tr("No sheets found in Excel file"));
                return;
            }

            if (sheetNames.size() > 1) {
                SheetSelectionDialog dialog(sheetNames, this);
                if (dialog.exec() != QDialog::Accepted) {
                    qCInfo(lcMainWindow) << "User cancelled sheet selection";
                    return;
                }
                excelSheet = dialog.getSelectedSheet();
            } else {
                excelSheet = sheetNames.first();
            }
        }

        QApplication::setOverrideCursor(Qt::WaitCursor);
        QElapsedTimer timer;
        timer.start();

        DataFrame loaded;

        if (ext == "asc") {
            loaded = FileLoaders::loadAscFile(path);
        } else if (ext == "csv") {
            loaded = FileLoaders::loadCsvFile(path);
        } else if (ext == "tdms") {
            loaded = FileLoaders::loadTdmsFile(path);
        } else {
            loaded = FileLoaders::loadExcelFile(path, excelSheet);
            qCInfo(lcMainWindow) << "Loaded sheet:" << excelSheet;
        }

        if (loaded.isEmpty()) {
            QApplication::restoreOverrideCursor();
            QMessageBox::critical(this, tr("Error"), tr("No data loaded from the file"));
            return;
        }

        df = loaded;
        originalDf = df.copy();
        filteredDf = df.copy();
        updateUiAfterLoad();

        currentFile = path;
        appToolBar->updateFileName(currentFile);

        // Set default title to filename without extension
        QString filenameWithoutExt = fi.completeBaseName();
        rightPanel->plotArea->setDefaultTitle(filenameWithoutExt);

        QApplication::restoreOverrideCursor();
        qint64 elapsed = timer.elapsed();
        qCInfo(lcMainWindow) << "File loaded successfully. Rows:" << df.rowCount()
                             << "in" << elapsed << "ms";
        QMessageBox::information(this, tr("Success"),
            tr("File loaded successfully!\n%1 rows, %2 columns in %3 ms")
                .arg(df.rowCount()).arg(df.columnCount()).arg(elapsed));

    } catch (const std::exception& e) {
        QApplication::restoreOverrideCursor();
        qCCritical(lcMainWindow) << "Error loading file:" << e.what();
        QMessageBox::critical(this, tr("Error"),
                              tr("An error occurred while loading the file: %1").arg(e.what()));
    }
}

void MainWindow::saveData()
{
    if (df.isEmpty()) {
        QMessageBox::warning(this, tr("Warning"), tr("No data to save. Please load a file first."));
        return;
    }

    QString defaultName = currentFile.isEmpty()
        ? "data"
        : QFileInfo(currentFile).completeBaseName();

    QString fileName = QFileDialog::getSaveFileName(
        this, tr("Save Data"), defaultName,
        tr("CSV Files (*.csv);;Excel Files (*.xlsx)"));

    if (fileName.isEmpty())
        return;

    if (fileName.endsWith(".csv")) {
        QFile file(fileName);
        if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
            QMessageBox::critical(this, tr("Error"), tr("Could not open file for writing"));
            return;
        }
        QTextStream out(&file);
        // Header
        out << df.columnNames().join(';') << "\n";
        // Data
        for (int r = 0; r < df.rowCount(); ++r) {
            QStringList vals;
            for (const auto& col : df.columnNames())
                vals << QString::number(df.value(r, col), 'g', 10);
            out << vals.join(';') << "\n";
        }
        file.close();
        QMessageBox::information(this, tr("Success"), tr("Data saved successfully!"));
    } else if (fileName.endsWith(".xlsx")) {
        // TODO: Add QXlsx library for Excel export
        QMessageBox::warning(this, tr("Not Supported"),
                             tr("Excel export requires the QXlsx library. Please save as CSV."));
    }
}

void MainWindow::savePlot()
{
    if (rightPanel->plotArea->plotItems.isEmpty()) {
        QMessageBox::warning(this, tr("Warning"), tr("No plot to save. Please create a plot first."));
        return;
    }

    QString defaultName = currentFile.isEmpty()
        ? "plot"
        : QFileInfo(currentFile).completeBaseName();

    QString fileName = QFileDialog::getSaveFileName(
        this, tr("Save Plot"), defaultName,
        tr("PNG Files (*.png);;PDF Files (*.pdf);;All Files (*)"));

    if (fileName.isEmpty())
        return;

    try {
        // Ensure proper extension
        if (!fileName.endsWith(".png") && !fileName.endsWith(".pdf")) {
            fileName += ".png";
        }

        rightPanel->plotArea->exportPlot(fileName);

        QMessageBox::information(this, tr("Success"),
                                 tr("Plot saved successfully to:\n%1").arg(fileName));
        qCInfo(lcMainWindow) << "Plot exported to:" << fileName;

    } catch (const std::exception& e) {
        qCCritical(lcMainWindow) << "Error saving plot:" << e.what();
        QMessageBox::critical(this, tr("Error"),
                              tr("An error occurred while saving the plot:\n%1").arg(e.what()));
    }
}

void MainWindow::exportTableToExcel()
{
    if (df.isEmpty()) {
        QMessageBox::warning(this, tr("Warning"), tr("No data to export. Please load a file first."));
        return;
    }

    QString defaultName = currentFile.isEmpty()
        ? "data"
        : QFileInfo(currentFile).completeBaseName();

    QString fileName = QFileDialog::getSaveFileName(
        this, tr("Export Table to Excel"), defaultName,
        tr("Excel Files (*.xlsx)"));

    if (fileName.isEmpty())
        return;

    // TODO: Add QXlsx library for full Excel export with multiple sheets
    QMessageBox::warning(this, tr("Not Supported"),
                         tr("Excel export requires the QXlsx library. Please use Save Data as CSV instead."));
}

void MainWindow::applyDataFilter(const QString& column, double minVal, double maxVal)
{
    try {
        qCInfo(lcMainWindow) << "Applying data filter: column=" << column
                             << ", min=" << minVal << ", max=" << maxVal;

        if (column.isEmpty()) {
            QMessageBox::warning(this, tr("Filter Error"), tr("Column name cannot be empty"));
            return;
        }

        if (originalDf.isEmpty() || !originalDf.columnNames().contains(column)) {
            QMessageBox::warning(this, tr("Filter Error"),
                                 tr("Column '%1' not found in the dataframe").arg(column));
            return;
        }

        filteredDf = originalDf.filter(column, minVal, maxVal);

        if (filteredDf.rowCount() == 0) {
            QMessageBox::warning(this, tr("Filter Error"), tr("No data points in the selected range"));
            filteredDf = originalDf.copy();
            return;
        }

        qCInfo(lcMainWindow) << "Filter applied. Rows before:" << originalDf.rowCount()
                             << ", after:" << filteredDf.rowCount();

        updateStatistics();
        updatePlot(false);

        QMessageBox::information(this, tr("Filter Applied"), tr("Data filter applied successfully"));

    } catch (const std::exception& e) {
        qCCritical(lcMainWindow) << "Error applying filter:" << e.what();
        QMessageBox::critical(this, tr("Error"),
                              tr("An unexpected error occurred: %1").arg(e.what()));
        filteredDf = originalDf.copy();
    }
}

void MainWindow::updatePlot(bool updateFilter)
{
    if (filteredDf.isEmpty())
        return;

    try {
        QString xColumn = leftPanel->axisSelection->xColumn();
        QStringList yColumns = leftPanel->axisSelection->yColumns();
        auto smoothingParams = leftPanel->smoothingOptions->getParams();

        // Apply data filter if needed
        if (updateFilter) {
            QString filterCol = leftPanel->dataFilter->filterColumn->currentText();
            QString minValue = leftPanel->dataFilter->minValue->text();
            QString maxValue = leftPanel->dataFilter->maxValue->text();

            if (!filterCol.isEmpty()) {
                bool hasMin = !minValue.trimmed().isEmpty();
                bool hasMax = !maxValue.trimmed().isEmpty();

                if (hasMin || hasMax) {
                    double min = hasMin ? minValue.toDouble() : std::numeric_limits<double>::lowest();
                    double max = hasMax ? maxValue.toDouble() : std::numeric_limits<double>::max();
                    applyDataFilter(filterCol, min, max);
                }
            }
        }

        // Tell the plot area whether this data forms an up/down loop so it can
        // enable the Upstream/Downstream selector.
        bool isLoop = false;
        if (!xColumn.isEmpty() && filteredDf.hasColumn(xColumn))
            isLoop = detectTurningIndex(filteredDf.columnRef(xColumn)) >= 0;
        rightPanel->plotArea->setBranchAvailable(isLoop);

        rightPanel->plotArea->plotData(currentSubset(), xColumn, yColumns, smoothingParams);
        updateStatistics();
        unsavedChanges = true;

    } catch (const std::exception& e) {
        qCCritical(lcMainWindow) << "Error updating plot:" << e.what();
        QMessageBox::critical(this, tr("Error"),
                              tr("Failed to update plot: %1").arg(e.what()));
    }
}

void MainWindow::updateStatistics()
{
    DataFrame subset = currentSubset();
    if (!subset.isEmpty()) {
        rightPanel->statisticsArea->updateStats(subset);
    } else {
        qCWarning(lcMainWindow) << "No data available to update statistics";
    }
}

// ========================================================================
// PARTITIONING / BRANCH (UPSTREAM-DOWNSTREAM)
// ========================================================================

int MainWindow::detectTurningIndex(const QVector<double>& x) const
{
    const int n = x.size();
    if (n < 4)
        return -1;

    int idxMax = -1, idxMin = -1;
    double vMax = std::numeric_limits<double>::lowest();
    double vMin = std::numeric_limits<double>::max();
    for (int i = 0; i < n; ++i) {
        if (!std::isfinite(x[i]))
            continue;
        if (x[i] > vMax) { vMax = x[i]; idxMax = i; }
        if (x[i] < vMin) { vMin = x[i]; idxMin = i; }
    }

    // A turning point only exists if an extremum sits clearly in the interior,
    // i.e. x rises to a peak and falls back (or dips to a valley and rises).
    auto interior = [n](int i) {
        return i > n / 20 && i < n - n / 20;
    };
    if (idxMax >= 0 && interior(idxMax))
        return idxMax;
    if (idxMin >= 0 && interior(idxMin))
        return idxMin;
    return -1;
}

DataFrame MainWindow::currentSubset() const
{
    if (filteredDf.isEmpty())
        return filteredDf;

    QString xCol = leftPanel->axisSelection->xColumn();
    if (xCol.isEmpty() || !filteredDf.hasColumn(xCol))
        return filteredDf;

    const QVector<double>& x = filteredDf.columnRef(xCol);
    const int n = x.size();

    // 1. Branch restricts the row range (acquisition order preserved).
    int rowLo = 0, rowHi = n;
    if (activeBranch != BranchAll) {
        int tp = detectTurningIndex(x);
        if (tp > 0) {
            if (activeBranch == BranchUpstream) { rowLo = 0;  rowHi = tp + 1; }
            else                                 { rowLo = tp; rowHi = n;      }
        }
    }

    // 2. Partition segment restricts by x-value within the chosen branch.
    double segLo = std::numeric_limits<double>::lowest();
    double segHi = std::numeric_limits<double>::max();
    if (activePartition >= 0 && !partitionDividers.isEmpty()) {
        QVector<double> d = partitionDividers;
        std::sort(d.begin(), d.end());
        int seg = activePartition;
        if (seg > d.size())
            seg = -1;                 // selection no longer valid -> whole range
        if (seg >= 0) {
            segLo = (seg == 0)        ? std::numeric_limits<double>::lowest() : d[seg - 1];
            segHi = (seg == d.size()) ? std::numeric_limits<double>::max()    : d[seg];
        }
    }

    // 3. Horizontal partition band restricts by y-value on the primary y column.
    double bandLo = std::numeric_limits<double>::lowest();
    double bandHi = std::numeric_limits<double>::max();
    QString yCol;
    {
        QStringList yCols = leftPanel->axisSelection->yColumns();
        if (!yCols.isEmpty())
            yCol = yCols.first();
    }
    if (activePartitionY >= 0 && !partitionDividersH.isEmpty() &&
        !yCol.isEmpty() && filteredDf.hasColumn(yCol)) {
        QVector<double> d = partitionDividersH;
        std::sort(d.begin(), d.end());
        int band = activePartitionY;
        if (band > d.size())
            band = -1;
        if (band >= 0) {
            bandLo = (band == 0)        ? std::numeric_limits<double>::lowest() : d[band - 1];
            bandHi = (band == d.size()) ? std::numeric_limits<double>::max()    : d[band];
        }
    }
    const bool haveBand = (bandLo != std::numeric_limits<double>::lowest() ||
                           bandHi != std::numeric_limits<double>::max());
    const QVector<double>* yvals = haveBand ? &filteredDf.columnRef(yCol) : nullptr;

    // Fast path: nothing is actually narrowed, so hand back the frame as-is.
    bool fullRows = (rowLo == 0 && rowHi == n);
    bool fullSeg  = (segLo == std::numeric_limits<double>::lowest() &&
                     segHi == std::numeric_limits<double>::max());
    if (fullRows && fullSeg && !haveBand)
        return filteredDf;

    // Build the sliced frame, keeping every column aligned.
    const QStringList cols = filteredDf.columnNames();
    QVector<const QVector<double>*> srcCols(cols.size());
    for (int c = 0; c < cols.size(); ++c)
        srcCols[c] = &filteredDf.columnRef(cols[c]);

    QVector<QVector<double>> out(cols.size());
    for (auto& c : out)
        c.reserve(rowHi - rowLo);

    for (int r = rowLo; r < rowHi; ++r) {
        double xv = x[r];
        if (std::isfinite(xv) && (xv < segLo || xv >= segHi))
            continue;
        if (yvals) {
            double yv = (*yvals)[r];
            if (std::isfinite(yv) && (yv < bandLo || yv >= bandHi))
                continue;
        }
        for (int c = 0; c < cols.size(); ++c)
            out[c].append((*srcCols[c])[r]);
    }

    DataFrame result;
    for (int c = 0; c < cols.size(); ++c)
        result.addColumn(cols[c], std::move(out[c]));
    return result;
}

void MainWindow::onPartitionDividersChanged(const QVector<double>& xs)
{
    partitionDividers = xs;
    std::sort(partitionDividers.begin(), partitionDividers.end());
    // Keep the active segment valid; otherwise fall back to the whole range.
    if (activePartition > partitionDividers.size())
        activePartition = -1;
    // Dividers only change the plotted data when an x-segment is actually
    // selected. When viewing "All", skip the replot so annotations (text
    // boxes, highlights) placed on the plot are preserved.
    if (activePartition >= 0)
        updatePlot(false);
}

void MainWindow::setActiveBranch(int branch)
{
    activeBranch = branch;
    updatePlot(false);
}

void MainWindow::setActivePartition(int segment)
{
    activePartition = segment;
    updatePlot(false);
}

void MainWindow::onPartitionDividersHChanged(const QVector<double>& ys)
{
    partitionDividersH = ys;
    std::sort(partitionDividersH.begin(), partitionDividersH.end());
    if (activePartitionY > partitionDividersH.size())
        activePartitionY = -1;
    if (activePartitionY >= 0)
        updatePlot(false);
}

void MainWindow::setActivePartitionY(int segment)
{
    activePartitionY = segment;
    updatePlot(false);
}

void MainWindow::exportCurrentSubset()
{
    DataFrame subset = currentSubset();
    if (subset.isEmpty()) {
        QMessageBox::warning(this, tr("Nothing to Export"),
                             tr("The selected partition contains no data."));
        return;
    }

    QString base = currentFile.isEmpty()
        ? QStringLiteral("partition")
        : QFileInfo(currentFile).completeBaseName() + "_partition";
    // Reflect the active selection in the suggested name.
    if (activeBranch == BranchUpstream)   base += "_upstream";
    else if (activeBranch == BranchDownstream) base += "_downstream";
    if (activePartition >= 0)  base += QString("_xseg%1").arg(activePartition + 1);
    if (activePartitionY >= 0) base += QString("_yband%1").arg(activePartitionY + 1);

    QString fileName = QFileDialog::getSaveFileName(
        this, tr("Export Partition Data"), base, tr("CSV Files (*.csv)"));
    if (fileName.isEmpty())
        return;
    if (!fileName.endsWith(".csv", Qt::CaseInsensitive))
        fileName += ".csv";

    QFile file(fileName);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        QMessageBox::critical(this, tr("Error"), tr("Could not open file for writing"));
        return;
    }
    QTextStream out(&file);
    const QStringList cols = subset.columnNames();
    out << cols.join(';') << "\n";
    for (int r = 0; r < subset.rowCount(); ++r) {
        QStringList vals;
        for (const auto& col : cols)
            vals << QString::number(subset.value(r, col), 'g', 10);
        out << vals.join(';') << "\n";
    }
    file.close();

    QMessageBox::information(this, tr("Export Complete"),
        tr("Exported %1 rows to:\n%2\n\n(CSV opens directly in Excel.)")
            .arg(subset.rowCount()).arg(fileName));
}

void MainWindow::updateUiAfterLoad()
{
    if (!df.isEmpty()) {
        QStringList columns = df.columnNames();
        leftPanel->updateOptions(columns);
        rightPanel->statisticsArea->updateStats(filteredDf);
    } else {
        qCWarning(lcMainWindow) << "DataFrame is empty after loading";
    }
}

void MainWindow::dragEnterEvent(QDragEnterEvent* event)
{
    if (event->mimeData()->hasUrls()) {
        event->acceptProposedAction();
    }
}

void MainWindow::dropEvent(QDropEvent* event)
{
    const QList<QUrl> urls = event->mimeData()->urls();
    for (const QUrl& url : urls) {
        loadFile(url.toLocalFile());
    }
}
