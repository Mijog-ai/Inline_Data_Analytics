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

    // Partitioning / branch (upstream-downstream) state.
    // Everything that is plotted, analysed or fitted operates on currentSubset(),
    // which is filteredDf narrowed to the selected branch and partition segment.
    enum Branch { BranchAll = 0, BranchUpstream = 1, BranchDownstream = 2 };
    QVector<double> partitionDividers;   // divider x-values, kept sorted ascending
    int activePartition = -1;            // -1 = whole range, else segment index [0 .. dividers.size()]
    int activeBranch = BranchAll;

    // filteredDf narrowed to the active branch and partition segment.
    DataFrame currentSubset() const;
    // Row index of the x turning point (hysteresis apex), or -1 when the data is not a loop.
    int detectTurningIndex(const QVector<double>& x) const;

    // UI components (public for child access)
    LeftPanel* leftPanel;
    RightPanel* rightPanel;
    MenuBar* appMenuBar;
    ToolBar* appToolBar;
    SessionManager* sessionManager;

public slots:
    void loadFile(const QString& filePath = QString());
    void saveData();
    void savePlot();
    void exportTableToExcel();
    void applyDataFilter(const QString& column, double minVal, double maxVal);
    void updatePlot(bool updateFilter = true);
    void updateStatistics();

    void onPartitionDividersChanged(const QVector<double>& xs);
    void setActiveBranch(int branch);
    void setActivePartition(int segment);

    void clearAllData();
    void resetUi();

protected:
    void dragEnterEvent(QDragEnterEvent* event) override;
    void dropEvent(QDropEvent* event) override;

private:
    void setupMenuBar();
    void setupUi();
    void setupEditActions();
    void updateUiAfterLoad();

    // Edit actions
    QAction* showSmoothingAction;
    QAction* showCommentAction;
    QAction* showFilterAction;
    QAction* showCurveFitAction;
};
