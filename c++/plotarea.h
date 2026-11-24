#pragma once

#include <QWidget>
#include <QLineEdit>
#include <QToolBar>
#include <QHBoxLayout>
#include <QVBoxLayout>
#include <QPushButton>
#include <QLabel>
#include <QAction>
#include <QShortcut>
#include <QTimer>
#include <QGraphicsTextItem>
#include <QComboBox>
#include <functional>

#include <QtCharts/QChart>
#include <QtCharts/QChartView>
#include <QtCharts/QLineSeries>
#include <QtCharts/QScatterSeries>
#include <QtCharts/QValueAxis>

#include "dataframe.h"

class PlotArea;

class EditableTextItem : public QGraphicsTextItem {
    Q_OBJECT
public:
    EditableTextItem(const QString& text, QGraphicsItem* parent = nullptr);
    void setPlotArea(PlotArea* area) { plotArea = area; }

protected:
    void mouseDoubleClickEvent(QGraphicsSceneMouseEvent* event) override;
    void mousePressEvent(QGraphicsSceneMouseEvent* event) override;

private:
    PlotArea* plotArea = nullptr;
};

class PlotArea : public QWidget {
    Q_OBJECT

public:
    explicit PlotArea(QWidget* parent = nullptr);

    void plotData(const DataFrame& df, const QString& xColumn, const QStringList& yColumns,
                  const QVariantMap& smoothingParams, const QString& title = QString(),
                  const QVector<QPair<QString, DataFrame>>& overlays = {});

    void applyCurveFitting(const QVector<double>& xData, const QVector<double>& yData,
                           std::function<double(double)> fitFunc, const QString& equation,
                           const QString& fitType, const QString& xLabel, const QString& yLabel);
    // Draw an additional fit curve (for an overlaid dataset) on the primary
    // y-axis in the given colour, so curve fitting mirrors across datasets.
    void addFitCurve(const QVector<double>& xData, std::function<double(double)> fitFunc,
                     const QColor& color, const QString& name);
    void removeCurveFitting();

    void clearPlot();
    void setDefaultTitle(const QString& title);
    void exportPlot(const QString& fileName);
    // Currently visible x-axis range (after X Range / zoom); false if nothing is plotted.
    bool visibleXRange(double& minX, double& maxX) const;

    void toggleCursor(bool enabled);
    void toggleLegend(bool enabled);
    void toggleHighlighter(bool enabled);

    struct PlotItem {
        QString name;
        QLineSeries* series = nullptr;
        QLineSeries* originalSeries = nullptr;
        QLineSeries* fitSeries = nullptr;
        QValueAxis* yAxis = nullptr;
        QColor color;
        QVector<double> xData;
        QVector<double> yData;
    };
    QVector<PlotItem> plotItems;
    // Fit curves for overlaid datasets (the active dataset's fit lives in
    // plotItems[0].fitSeries). Cleared by removeCurveFitting() and clearPlot().
    QVector<QLineSeries*> datasetFitSeries;

    bool getShowOriginalState() const { return showOriginalData; }
    void setShowOriginalState(bool show) { showOriginalData = show; }

    void editTextItem(EditableTextItem* item);
    void removeTextItem(EditableTextItem* item);

    // Partitioning (vertical + horizontal divider lines) + upstream/downstream branch.
    void clearPartitions();
    void setBranchAvailable(bool loop);
    QVector<double> partitionXs() const { return partitionDividers; }
    QVector<double> partitionYs() const { return partitionDividersH; }

    // Restore a complete partition configuration (used when loading a preset):
    // the vertical/horizontal divider values, the active branch (0=All,
    // 1=Upstream, 2=Downstream) and the selected x/y segment (-1 = All).
    void applyPartitionState(const QVector<double>& xs, const QVector<double>& ys,
                             int branchIndex, int xSegment, int ySegment);

signals:
    void partitionDividersChanged(const QVector<double>& xs);   // vertical divider x-values
    void partitionDividersHChanged(const QVector<double>& ys);  // horizontal divider y-values
    void branchChanged(int branchIndex);        // 0=All, 1=Upstream, 2=Downstream
    void partitionSegmentChanged(int segment);  // -1=All, else x-segment index
    void partitionYSegmentChanged(int segment); // -1=All, else y-segment index
    void exportSegmentRequested();              // export current partition subset

protected:
    void changeEvent(QEvent* event) override;

private:
    void setupUi();
    void retranslateUi();
    void createTitleControls();
    void createToolbar();
    void createXAxisControls();
    void createChart();
    void createLegendArea();

    bool eventFilter(QObject* obj, QEvent* event) override;
    void onMouseMoved(QPointF pos);
    void clearCursorItems();
    void setCursorItemsVisible(bool visible);
    void handleLeftClick(QPointF valuePos);
    void handleDoubleClick(QPointF valuePos);
    void processPendingClick();
    void addHighlight(double x);
    void removeNearestHighlight(double x);
    void clearHighlights();
    void updateLegend();
    double findClosestYValue(QLineSeries* series, double xVal) const;

    void insertFloatingTextAt(double x, double y);
    void cancelTextInsertion();
    void clearAllTexts();

    void togglePartitionMode(bool enabled);
    void addPartitionDivider(double x);
    void removeNearestDivider(double x);
    void addPartitionDividerH(double y);
    void removeNearestDividerH(double y);
    // Remove the divider (either orientation) nearest the given scene point, if
    // within a small pixel tolerance. Returns true if one was removed.
    bool removePartitionAtPixel(const QPointF& scenePos);
    void updatePartitionLines();
    void rebuildPartitionCombo();
    void rebuildPartitionComboY();
    void fitToScreen();

    struct PlotState {
        struct HighlightData { double x; };
        struct TextData { QString text; QPointF position; };
        QVector<HighlightData> highlights;
        QVector<TextData> floatingTexts;
        QVector<double> partitionsV;
        QVector<double> partitionsH;
        QString title;
        double xRangeMin = 0;
        double xRangeMax = 0;
    };
    PlotState captureState() const;
    void saveState();
    void restoreState(const PlotState& state);
    void undoLastAction();
    void redoLastAction();
    void updateUndoRedoButtons();

    QLabel* titleLabel = nullptr;
    QLabel* xRangeLabel = nullptr;
    QLabel* toLabel = nullptr;
    QLineEdit* titleInput = nullptr;
    QPushButton* setTitleButton = nullptr;
    QLineEdit* xMinInput = nullptr;
    QLineEdit* xMaxInput = nullptr;
    QPushButton* xApplyButton = nullptr;
    QPushButton* xResetButton = nullptr;
    QToolBar* toolbar = nullptr;
    QChart* chart = nullptr;
    QChartView* chartView = nullptr;
    QValueAxis* xAxis = nullptr;
    QWidget* legendWidget = nullptr;
    QHBoxLayout* legendLayout = nullptr;

    QAction* cursorAction = nullptr;
    QAction* legendAction = nullptr;
    QAction* highlighterAction = nullptr;
    QAction* insertTextAction = nullptr;
    QAction* clearTextsAction = nullptr;
    QAction* undoAction = nullptr;
    QAction* redoAction = nullptr;

    QAction* fitAction = nullptr;
    QAction* clearHighlightsAction = nullptr;
    QAction* clearPartitionsAction = nullptr;
    QAction* exportSegmentAction = nullptr;

    QAction* partitionAction = nullptr;
    QComboBox* orientCombo = nullptr;
    QComboBox* branchCombo = nullptr;
    QComboBox* partitionCombo = nullptr;
    QComboBox* partitionComboY = nullptr;
    QWidget* segmentBar = nullptr;     // branch + x/y segment selectors
    QLabel* branchLabel = nullptr;
    QLabel* xSegLabel = nullptr;
    QLabel* ySegLabel = nullptr;

    QShortcut* undoShortcut = nullptr;
    QShortcut* redoShortcut = nullptr;

    bool showCursor = false;
    bool showLegend = true;
    bool highlighterMode = false;
    bool showOriginalData = true;
    bool textInsertionMode = false;
    bool partitionMode = false;
    bool partitionHorizontal = false;   // orientation of dividers added in partition mode
    QString currentTitle;
    QString xColumnName;
    QString pendingText;

    QTimer* clickTimer = nullptr;
    QPointF pendingClickValue;
    static constexpr int DOUBLE_CLICK_INTERVAL = 300;

    // Base colours per plotted column. Chosen bright and well-separated so the
    // progressively darker shades used for overlaid datasets stay clearly
    // distinguishable from the base (dark starting colours collapse to black
    // when darkened, which made the first two series hard to tell apart).
    static constexpr int NUM_COLORS = 9;
    QColor colors[NUM_COLORS] = {
        QColor( 66, 165, 245),  // blue
        QColor(239, 108,  55),  // orange
        QColor( 76, 187,  95),  // green
        QColor(171, 110, 224),  // purple
        QColor(236, 190,  40),  // gold
        QColor( 38, 198, 218),  // cyan
        QColor(236, 101, 174),  // pink
        QColor(141, 110,  99),  // brown
        QColor(120, 144, 156)   // blue-grey
    };

    QGraphicsLineItem* crosshairV = nullptr;
    // One horizontal guide and marker per series, at the curve value the label reports.
    QVector<QGraphicsLineItem*> cursorHLines;
    QVector<QGraphicsEllipseItem*> cursorDots;
    QGraphicsSimpleTextItem* cursorLabel = nullptr;
    QGraphicsRectItem* cursorLabelBg = nullptr;

    struct HighlightLine {
        double xValue = 0;
        QGraphicsLineItem* verticalLine = nullptr;
        QVector<QGraphicsLineItem*> horizontalLines;
        QVector<QGraphicsEllipseItem*> scatterDots;
        QVector<QGraphicsSimpleTextItem*> labels;
        QGraphicsTextItem* legendBox = nullptr;
    };
    QVector<HighlightLine> highlightLines;

    struct FloatingText {
        EditableTextItem* item = nullptr;
        QString text;
        QPointF position;
    };
    QVector<FloatingText> floatingTextItems;

    // Vertical partition dividers (x-values, sorted) and their scene graphics.
    QVector<double> partitionDividers;
    QVector<QGraphicsLineItem*> partitionLineItems;
    QVector<QGraphicsSimpleTextItem*> partitionLabelItems;
    // Horizontal partition dividers (y-values on the primary axis, sorted).
    QVector<double> partitionDividersH;
    QVector<QGraphicsLineItem*> partitionLineItemsH;
    QVector<QGraphicsSimpleTextItem*> partitionLabelItemsH;

    QVector<PlotState> historyStack;
    QVector<PlotState> redoStack;
    static constexpr int MAX_HISTORY = 50;
};
