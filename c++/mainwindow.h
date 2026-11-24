#pragma once

#include <QMainWindow>
#include <QAction>
#include <QDragEnterEvent>
#include <QDropEvent>
#include "dataframe.h"

class LeftPanel;
class RightPanel;
class MenuBar;
class ToolBar;
class SessionManager;
class PresetManager;

class MainWindow : public QMainWindow {
    Q_OBJECT

public:
    explicit MainWindow(QWidget* parent = nullptr);

    // Data
    DataFrame df;
    DataFrame originalDf;
    DataFrame filteredDf;
    bool unsavedChanges = false;
    QString currentFile;

    // Multiple loaded files. Every dataset must share the same set of column
    // names as the first one loaded (order-independent); a file whose columns
    // differ is rejected. One dataset is "active" at a time and drives the
    // analysis pipeline (df/originalDf/filteredDf, filtering, partitioning,
    // statistics, curve fitting); the others are overlaid on the plot.
    struct Dataset {
        QString name;   // display name (file base name, made unique)
        QString path;   // source file path
        DataFrame data; // raw loaded data
    };
    QVector<Dataset> datasets;
    int activeDataset = -1;
    QStringList referenceColumns;  // sorted column-name set of the first dataset

    // Register a freshly loaded file. Enforces the column-name-set check against
    // the first dataset, shows a message and returns false if it does not match.
    bool addDataset(const QString& path, const DataFrame& data,
                    const QString& nameHint = QString());
    // Load one file (every chosen Excel sheet) as dataset(s); returns how many
    // datasets were added.
    int loadSingleFile(const QString& path);
    // Make dataset `index` the active one: load it into the analysis pipeline,
    // reset partition/branch/filter state and refresh the whole UI.
    void setActiveDataset(int index);

    // Partitioning / branch (upstream-downstream) state.
    // Everything that is plotted, analysed or fitted operates on currentSubset(),
    // which is filteredDf narrowed to the selected branch and partition segment.
    enum Branch { BranchAll = 0, BranchUpstream = 1, BranchDownstream = 2 };
    QVector<double> partitionDividers;   // vertical divider x-values, sorted ascending
    QVector<double> partitionDividersH;  // horizontal divider y-values, sorted ascending
    int activePartition = -1;            // -1 = whole range, else x-segment index
    int activePartitionY = -1;           // -1 = whole range, else y-band index
    int activeBranch = BranchAll;

    // filteredDf narrowed to the active branch and partition segment.
    DataFrame currentSubset() const;
    // Apply the current data-filter settings (filter column + min/max from the
    // left panel) to an arbitrary frame, without side effects or dialogs.
    DataFrame applyCurrentFilter(const DataFrame& source) const;
    // Narrow an arbitrary frame to the active branch and partition segment/band
    // using the shared divider values and the selected x/y columns.
    DataFrame narrowToSelection(const DataFrame& frame) const;
    // Row index of the x turning point (hysteresis apex), or -1 when the data is not a loop.
    int detectTurningIndex(const QVector<double>& x) const;

    // UI components (public for child access)
    LeftPanel* leftPanel;
    RightPanel* rightPanel;
    MenuBar* appMenuBar;
    ToolBar* appToolBar;
    SessionManager* sessionManager;
    PresetManager* presetManager;

public slots:
    void loadFile(const QString& filePath = QString());
    void saveData();
    void savePlot();
    void exportTableToExcel();
    void applyDataFilter(const QString& column, double minVal, double maxVal);
    void updatePlot(bool updateFilter = true);
    void updateStatistics();

    void onPartitionDividersChanged(const QVector<double>& xs);
    void onPartitionDividersHChanged(const QVector<double>& ys);
    void setActiveBranch(int branch);
    void setActivePartition(int segment);
    void setActivePartitionY(int segment);
    void exportCurrentSubset();

    void clearAllData();
    void resetUi();

protected:
    void dragEnterEvent(QDragEnterEvent* event) override;
    void dropEvent(QDropEvent* event) override;
    void changeEvent(QEvent* event) override;

private:
    void setupMenuBar();
    void setupUi();
    void setupEditActions();
    void retranslateUi();
    void updateUiAfterLoad();

    // What is drawn in the plot: currentSubset() limited to the visible x range,
    // with the x and selected y columns plus smoothed curves when smoothing is on.
    DataFrame plotViewData() const;
    // Same plot-view projection for an arbitrary subset (used per dataset).
    DataFrame plotViewOf(const DataFrame& subset) const;
    // A dataset narrowed by the current filter + branch/partition selection.
    DataFrame datasetSubset(int index) const;
    // Export data for one dataset: the whole dataset, or its current plot view.
    DataFrame exportDataForDataset(int index, bool plotView) const;
    // Ask whether to export the whole dataset or the current plot view.
    // Returns false if cancelled or the chosen data is empty.
    bool chooseExportData(DataFrame& data, bool& plotView);
    bool writeCsv(const QString& fileName, const DataFrame& data);

    // Edit actions
    QAction* showSmoothingAction;
    QAction* showCommentAction;
    QAction* showFilterAction;
    QAction* showCurveFitAction;
};
