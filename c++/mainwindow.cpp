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
#include "smoothing.h"

#include <QHBoxLayout>
#include <QFileDialog>
#include <QMessageBox>
#include <QPushButton>
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
    datasets.clear();
    activeDataset = -1;
    referenceColumns.clear();
    if (appToolBar)
        appToolBar->refreshDatasetList();
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
    QStringList paths;

    qCInfo(lcMainWindow) << "loadFile method called";

    if (filePath.isEmpty()) {
        paths = QFileDialog::getOpenFileNames(
            this, tr("Open File(s)"), QString(),
            tr("All Files (*);;ASC Files (*.asc);;CSV Files (*.csv);;"
               "TDMS Files (*.tdms);;Excel Files (*.xlsx *.xlsm *.xls)"));
    } else {
        paths << filePath;
    }

    if (paths.isEmpty()) {
        qCInfo(lcMainWindow) << "File loading cancelled by user";
        return;
    }

    QElapsedTimer timer;
    timer.start();
    int added = 0;
    for (const QString& path : paths) {
        qCInfo(lcMainWindow) << "File selected:" << path;
        added += loadSingleFile(path);
    }

    if (added > 0) {
        QMessageBox::information(this, tr("Success"),
            tr("%1 dataset(s) loaded (%2 in total).\nActive: %3 rows, %4 columns (%5 ms)")
                .arg(added).arg(datasets.size())
                .arg(df.rowCount()).arg(df.columnCount()).arg(timer.elapsed()));
    }
}

int MainWindow::loadSingleFile(const QString& path)
{
    try {
        QFileInfo fi(path);
        const QString ext = fi.suffix().toLower();

        const bool isExcel = (ext == "xlsx" || ext == "xlsm" || ext == "xls");
        if (!isExcel && ext != "asc" && ext != "csv" && ext != "tdms") {
            QMessageBox::critical(this, tr("Error"),
                                  tr("Unsupported file type: %1").arg(ext));
            return 0;
        }

        // Pick the Excel sheet(s) before showing the wait cursor
        QStringList excelSheets;
        if (isExcel) {
            QStringList sheetNames = FileLoaders::getExcelSheets(path);

            if (sheetNames.isEmpty()) {
                QMessageBox::critical(this, tr("Error"), tr("No sheets found in Excel file"));
                return 0;
            }

            if (sheetNames.size() > 1) {
                SheetSelectionDialog dialog(sheetNames, this);
                if (dialog.exec() != QDialog::Accepted) {
                    qCInfo(lcMainWindow) << "User cancelled sheet selection";
                    return 0;
                }
                excelSheets = dialog.getSelectedSheets();
            } else {
                excelSheets = sheetNames;
            }
        }

        // Non-Excel files load as one dataset (empty sheet name).
        const QStringList jobs = isExcel ? excelSheets : QStringList{QString()};
        int added = 0;

        for (const QString& sheet : jobs) {
            QApplication::setOverrideCursor(Qt::WaitCursor);
            DataFrame loaded;
            QString nameHint;

            try {
                if (ext == "asc") {
                    loaded = FileLoaders::loadAscFile(path);
                } else if (ext == "csv") {
                    loaded = FileLoaders::loadCsvFile(path);
                } else if (ext == "tdms") {
                    loaded = FileLoaders::loadTdmsFile(path);
                } else {
                    loaded = FileLoaders::loadExcelFile(path, sheet);
                    qCInfo(lcMainWindow) << "Loaded sheet:" << sheet;
                    if (excelSheets.size() > 1)
                        nameHint = fi.completeBaseName() + " - " + sheet;
                }
            } catch (...) {
                QApplication::restoreOverrideCursor();
                throw;
            }
            QApplication::restoreOverrideCursor();

            if (loaded.isEmpty()) {
                QMessageBox::critical(this, tr("Error"),
                    isExcel ? tr("No data loaded from sheet \"%1\"").arg(sheet)
                            : tr("No data loaded from the file"));
                continue;
            }

            // On a column mismatch addDataset has already told the user why.
            if (addDataset(path, loaded, nameHint))
                ++added;
        }
        return added;

    } catch (const std::exception& e) {
        qCCritical(lcMainWindow) << "Error loading file:" << e.what();
        QMessageBox::critical(this, tr("Error"),
                              tr("An error occurred while loading the file: %1").arg(e.what()));
        return 0;
    }
}

void MainWindow::saveData()
{
    if (df.isEmpty()) {
        QMessageBox::warning(this, tr("Warning"), tr("No data to save. Please load a file first."));
        return;
    }

    DataFrame data;
    bool plotView = false;
    if (!chooseExportData(data, plotView))
        return;

    QString defaultName = currentFile.isEmpty()
        ? "data"
        : QFileInfo(currentFile).completeBaseName();
    if (plotView)
        defaultName += "_plot";

    QString fileName = QFileDialog::getSaveFileName(
        this, tr("Save Data"), defaultName,
        tr("CSV Files (*.csv);;Excel Files (*.xlsx)"));

    if (fileName.isEmpty())
        return;

    const bool multi = datasets.size() > 1;

    if (fileName.endsWith(".csv")) {
        if (!multi) {
            if (writeCsv(fileName, data))
                QMessageBox::information(this, tr("Success"), tr("Data saved successfully!"));
            return;
        }
        // CSV holds one table, so write one file per dataset, suffixed by name.
        QFileInfo fi(fileName);
        int ok = 0;
        for (int k = 0; k < datasets.size(); ++k) {
            DataFrame d = exportDataForDataset(k, plotView);
            if (d.isEmpty())
                continue;
            QString out = fi.dir().filePath(
                fi.completeBaseName() + "_" + datasets[k].name + ".csv");
            if (writeCsv(out, d))
                ++ok;
        }
        QMessageBox::information(this, tr("Success"),
            tr("Saved %1 dataset file(s) next to:\n%2").arg(ok).arg(fileName));
    } else if (fileName.endsWith(".xlsx")) {
        try {
            QApplication::setOverrideCursor(Qt::WaitCursor);
            QVector<FileLoaders::ExcelSheet> sheets;
            if (!multi) {
                sheets.append({QStringLiteral("Data"), data, {}});
            } else {
                // One worksheet per dataset, same filter/plot-view projection.
                for (int k = 0; k < datasets.size(); ++k) {
                    DataFrame d = exportDataForDataset(k, plotView);
                    if (!d.isEmpty())
                        sheets.append({datasets[k].name, d, {}});
                }
            }
            FileLoaders::saveExcelFile(fileName, sheets);
            QApplication::restoreOverrideCursor();
            QMessageBox::information(this, tr("Success"), tr("Data saved successfully!"));
        } catch (const std::exception& e) {
            QApplication::restoreOverrideCursor();
            QMessageBox::critical(this, tr("Error"),
                                  tr("An error occurred while saving the data:\n%1").arg(e.what()));
        }
    }
}

bool MainWindow::writeCsv(const QString& fileName, const DataFrame& data)
{
    QFile file(fileName);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        QMessageBox::critical(this, tr("Error"), tr("Could not open file for writing"));
        return false;
    }
    QTextStream out(&file);
    const QStringList cols = data.columnNames();
    out << cols.join(';') << "\n";
    for (int r = 0; r < data.rowCount(); ++r) {
        QStringList vals;
        for (const auto& col : cols)
            vals << QString::number(data.value(r, col), 'g', 10);
        out << vals.join(';') << "\n";
    }
    return true;
}

DataFrame MainWindow::plotViewData() const
{
    return plotViewOf(currentSubset());
}

DataFrame MainWindow::datasetSubset(int index) const
{
    if (index < 0 || index >= datasets.size())
        return DataFrame();
    if (index == activeDataset)
        return currentSubset();
    return narrowToSelection(applyCurrentFilter(datasets[index].data));
}

DataFrame MainWindow::exportDataForDataset(int index, bool plotView) const
{
    if (index < 0 || index >= datasets.size())
        return DataFrame();
    return plotView ? plotViewOf(datasetSubset(index)) : datasets[index].data;
}

DataFrame MainWindow::plotViewOf(const DataFrame& subset) const
{
    const QString xCol = leftPanel->axisSelection->xColumn();
    if (subset.isEmpty() || xCol.isEmpty() || !subset.hasColumn(xCol))
        return DataFrame();

    double lo = std::numeric_limits<double>::lowest();
    double hi = std::numeric_limits<double>::max();
    rightPanel->plotArea->visibleXRange(lo, hi);

    const QVector<double>& x = subset.columnRef(xCol);
    QVector<int> rows;
    for (int i = 0; i < x.size(); ++i)
        if (x[i] >= lo && x[i] <= hi)
            rows << i;

    auto pick = [&rows](const QVector<double>& col) {
        QVector<double> out;
        out.reserve(rows.size());
        for (int r : rows)
            out << (r < col.size() ? col[r] : std::numeric_limits<double>::quiet_NaN());
        return out;
    };

    // Smoothing runs on the whole subset before the x range is applied, as in the plot.
    const QVariantMap params = leftPanel->smoothingOptions->getParams();
    const bool smooth = params.value("apply", false).toBool();

    DataFrame out;
    out.addColumn(xCol, pick(x));
    for (const QString& yCol : leftPanel->axisSelection->yColumns()) {
        if (yCol == xCol || !subset.hasColumn(yCol))
            continue;
        const QVector<double>& y = subset.columnRef(yCol);
        out.addColumn(yCol, pick(y));
        if (smooth) {
            const QVector<double> smoothed = Smoothing::applySmoothing(
                y, params.value("method", "moving_average").toString(),
                params.value("window_length", 51).toInt(), params.value("poly_order", 3).toInt(),
                params.value("sigma", 2.0).toDouble(), params.value("alpha", 0.3).toDouble(),
                params.value("lowess_frac", 0.1).toDouble());
            out.addColumn(yCol + " (smoothed)", pick(smoothed));
        }
    }
    return out;
}

bool MainWindow::chooseExportData(DataFrame& data, bool& plotView)
{
    const DataFrame view = plotViewData();

    QMessageBox box(QMessageBox::Question, tr("Export Data"),
                    tr("Which data do you want to export?"), QMessageBox::Cancel, this);
    box.setInformativeText(tr("The current plot view contains only the plotted columns and the "
                              "rows shown in the plot (data filter, branch, partition segments "
                              "and visible x range), plus the smoothed curves if smoothing is on."));
    QPushButton* viewButton = box.addButton(
        tr("Current Plot View (%1 rows)").arg(view.rowCount()), QMessageBox::AcceptRole);
    QPushButton* wholeButton = box.addButton(
        tr("Whole Dataset (%1 rows)").arg(df.rowCount()), QMessageBox::AcceptRole);
    viewButton->setEnabled(!view.isEmpty());
    box.setDefaultButton(view.isEmpty() ? wholeButton : viewButton);
    box.exec();

    if (box.clickedButton() == wholeButton) {
        data = df;
        plotView = false;
        return true;
    }
    if (box.clickedButton() == viewButton) {
        data = view;
        plotView = true;
        return true;
    }
    return false;
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

    DataFrame data;
    bool plotView = false;
    if (!chooseExportData(data, plotView))
        return;

    QString defaultName = currentFile.isEmpty()
        ? "data"
        : QFileInfo(currentFile).completeBaseName();
    if (plotView)
        defaultName += "_plot";

    QString fileName = QFileDialog::getSaveFileName(
        this, tr("Export Table to Excel"), defaultName,
        tr("Excel Files (*.xlsx)"));

    if (fileName.isEmpty())
        return;

    if (!fileName.endsWith(".xlsx", Qt::CaseInsensitive))
        fileName += ".xlsx";

    const bool multi = datasets.size() > 1;

    // One (sheet name, data) pair per dataset to export; single dataset keeps
    // the "Data" sheet name as before.
    QVector<QPair<QString, DataFrame>> exportSets;
    if (!multi) {
        exportSets.append({QStringLiteral("Data"), data});
    } else {
        for (int k = 0; k < datasets.size(); ++k) {
            DataFrame d = exportDataForDataset(k, plotView);
            if (!d.isEmpty())
                exportSets.append({datasets[k].name, d});
        }
    }

    // Statistics in the layout of pandas' describe(): one column per data
    // column, with a per-dataset block when several are loaded.
    auto describeBlock = [](const DataFrame& d) {
        QList<QVariantList> rows;
        const auto stats = d.describe();
        QVariantList header{QString()}, countRow{"count"}, meanRow{"mean"}, stdRow{"std"},
            minRow{"min"}, maxRow{"max"};
        for (const auto& s : stats) {
            header << s.name; countRow << s.count; meanRow << s.mean;
            stdRow << s.std; minRow << s.min; maxRow << s.max;
        }
        rows << header << countRow << meanRow << stdRow << minRow << maxRow;
        return rows;
    };
    QList<QVariantList> statsRows;
    if (!multi) {
        statsRows = describeBlock(data);
    } else {
        for (const auto& set : exportSets) {
            statsRows << QVariantList{set.first};
            statsRows.append(describeBlock(set.second));
            statsRows << QVariantList{};  // blank spacer row
        }
    }

    QStringList yAxes;
    for (const auto* item : leftPanel->axisSelection->yList->selectedItems())
        yAxes << item->text();
    const QVariantMap smoothing = leftPanel->smoothingOptions->getParams();
    QList<QVariantList> configRows{
        {"Setting", "Value"},
        {"X-axis", leftPanel->axisSelection->xCombo->currentText()},
        {"Y-axes", yAxes.join(", ")},
        {"Smoothing", smoothing.value("apply")},
        {"Smoothing Method", smoothing.value("method")},
        {"Window Size", smoothing.value("window_length")},
        {"Polynomial Order", smoothing.value("poly_order")},
        {"Gaussian Sigma", smoothing.value("sigma")},
        {"Alpha", smoothing.value("alpha")},
        {"LOWESS Fraction", smoothing.value("lowess_frac")},
        {"Exported Data", plotView ? "Current plot view" : "Whole dataset"},
    };
    if (plotView) {
        double lo = 0, hi = 0;
        if (rightPanel->plotArea->visibleXRange(lo, hi))
            configRows << QVariantList{"X Range Min", lo} << QVariantList{"X Range Max", hi};
        static const char* branchNames[] = {"All", "Upstream", "Downstream"};
        configRows << QVariantList{"Branch", branchNames[qBound(0, activeBranch, 2)]}
                   << QVariantList{"X Segment", activePartition >= 0 ? QVariant(activePartition + 1)
                                                                     : QVariant("All")}
                   << QVariantList{"Y Band", activePartitionY >= 0 ? QVariant(activePartitionY + 1)
                                                                   : QVariant("All")};
    }

    QList<QVariantList> commentRows{{"Comments"}, {leftPanel->commentBox->getComments()}};

    try {
        QApplication::setOverrideCursor(Qt::WaitCursor);
        QVector<FileLoaders::ExcelSheet> sheets;
        for (const auto& set : exportSets)
            sheets.append({set.first, set.second, {}});
        sheets.append({QStringLiteral("Statistics"), {}, statsRows});
        sheets.append({QStringLiteral("Plot Configuration"), {}, configRows});
        sheets.append({QStringLiteral("Comments"), {}, commentRows});
        FileLoaders::saveExcelFile(fileName, sheets);
        QApplication::restoreOverrideCursor();
        QMessageBox::information(this, tr("Success"), tr("Table exported to Excel successfully!"));
    } catch (const std::exception& e) {
        QApplication::restoreOverrideCursor();
        QMessageBox::critical(this, tr("Error"),
                              tr("An error occurred while exporting the table:\n%1").arg(e.what()));
    }
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

        // Overlay the other loaded datasets. Each one gets the same data
        // filter and the same branch/partition narrowing as the active
        // dataset, so filters and segment selections affect every curve on
        // the plot, not just the active file.
        QVector<QPair<QString, DataFrame>> overlays;
        for (int k = 0; k < datasets.size(); ++k)
            if (k != activeDataset)
                overlays.append({datasets[k].name,
                                 narrowToSelection(applyCurrentFilter(datasets[k].data))});

        rightPanel->plotArea->plotData(currentSubset(), xColumn, yColumns,
                                       smoothingParams, QString(), overlays);
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
    if (subset.isEmpty()) {
        qCWarning(lcMainWindow) << "No data available to update statistics";
        return;
    }

    // With more than one dataset loaded, show stats for every dataset using the
    // same filter/segment narrowing, so the panel mirrors the plot.
    if (datasets.size() > 1 && activeDataset >= 0) {
        QVector<QPair<QString, DataFrame>> sets;
        sets.append({datasets[activeDataset].name, subset});
        for (int k = 0; k < datasets.size(); ++k)
            if (k != activeDataset)
                sets.append({datasets[k].name,
                             narrowToSelection(applyCurrentFilter(datasets[k].data))});
        rightPanel->statisticsArea->updateStatsMulti(sets);
    } else {
        rightPanel->statisticsArea->updateStats(subset);
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
    return narrowToSelection(filteredDf);
}

DataFrame MainWindow::applyCurrentFilter(const DataFrame& source) const
{
    if (source.isEmpty())
        return source;

    const QString filterCol = leftPanel->dataFilter->filterColumn->currentText();
    if (filterCol.isEmpty() || !source.hasColumn(filterCol))
        return source;

    const QString minS = leftPanel->dataFilter->minValue->text();
    const QString maxS = leftPanel->dataFilter->maxValue->text();
    const bool hasMin = !minS.trimmed().isEmpty();
    const bool hasMax = !maxS.trimmed().isEmpty();
    if (!hasMin && !hasMax)
        return source;

    const double mn = hasMin ? minS.toDouble() : std::numeric_limits<double>::lowest();
    const double mx = hasMax ? maxS.toDouble() : std::numeric_limits<double>::max();
    DataFrame f = source.filter(filterCol, mn, mx);
    // Mirror the active-dataset behaviour: an empty result means the range
    // excludes everything, so fall back to the unfiltered frame.
    return f.rowCount() > 0 ? f : source;
}

DataFrame MainWindow::narrowToSelection(const DataFrame& filteredDf) const
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

    if (datasets.size() <= 1) {
        if (writeCsv(fileName, subset))
            QMessageBox::information(this, tr("Export Complete"),
                tr("Exported %1 rows to:\n%2\n\n(CSV opens directly in Excel.)")
                    .arg(subset.rowCount()).arg(fileName));
        return;
    }

    // Several datasets loaded: write the active one to the chosen file and each
    // other dataset's matching subset to a file suffixed with its name.
    QFileInfo fi(fileName);
    int files = 0, rows = 0;
    for (int k = 0; k < datasets.size(); ++k) {
        DataFrame sub = datasetSubset(k);
        if (sub.isEmpty())
            continue;
        QString out = (k == activeDataset)
            ? fileName
            : fi.dir().filePath(fi.completeBaseName() + "_" + datasets[k].name + ".csv");
        if (writeCsv(out, sub)) { ++files; rows += sub.rowCount(); }
    }
    QMessageBox::information(this, tr("Export Complete"),
        tr("Exported %1 dataset file(s), %2 rows total, next to:\n%3\n\n"
           "(CSV opens directly in Excel.)").arg(files).arg(rows).arg(fileName));
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

bool MainWindow::addDataset(const QString& path, const DataFrame& data,
                            const QString& nameHint)
{
    // Enforce the shared-column-names rule (order-independent) against the
    // first dataset that was loaded.
    QStringList sortedCols = data.columnNames();
    sortedCols.sort();

    if (!datasets.isEmpty() && sortedCols != referenceColumns) {
        QStringList missing, extra;
        for (const QString& c : referenceColumns)
            if (!sortedCols.contains(c)) missing << c;
        for (const QString& c : sortedCols)
            if (!referenceColumns.contains(c)) extra << c;

        QString detail;
        if (!missing.isEmpty())
            detail += tr("Missing columns: %1\n").arg(missing.join(", "));
        if (!extra.isEmpty())
            detail += tr("Unexpected columns: %1\n").arg(extra.join(", "));

        QMessageBox::warning(this, tr("Columns Do Not Match"),
            tr("This file's columns do not match the already-loaded data, so it "
               "was not added.\n\nExpected columns: %1\n\n%2")
                .arg(referenceColumns.join(", "), detail));
        return false;
    }

    if (datasets.isEmpty())
        referenceColumns = sortedCols;

    // Build a unique display name from the file base name.
    QString base = nameHint.isEmpty() ? QFileInfo(path).completeBaseName() : nameHint;
    QString name = base;
    int suffix = 2;
    auto nameTaken = [this](const QString& n) {
        for (const auto& d : datasets)
            if (d.name == n) return true;
        return false;
    };
    while (nameTaken(name))
        name = QStringLiteral("%1 (%2)").arg(base).arg(suffix++);

    datasets.append({name, path, data});
    setActiveDataset(datasets.size() - 1);
    return true;
}

void MainWindow::setActiveDataset(int index)
{
    if (index < 0 || index >= datasets.size())
        return;

    activeDataset = index;
    const Dataset& ds = datasets[index];

    // Load the dataset into the analysis pipeline and start from a clean
    // partition/branch/filter state.
    df = ds.data.copy();
    originalDf = df.copy();
    filteredDf = df.copy();
    partitionDividers.clear();
    partitionDividersH.clear();
    activePartition = -1;
    activePartitionY = -1;
    activeBranch = BranchAll;

    currentFile = ds.path;
    appToolBar->updateFileName(currentFile);
    appToolBar->refreshDatasetList();
    rightPanel->plotArea->setDefaultTitle(ds.name);

    updateUiAfterLoad();
    updatePlot();
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
