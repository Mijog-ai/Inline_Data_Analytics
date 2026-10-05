#pragma once

#include <QWidget>

class AxisSelection;
class SmoothingOptions;
class DataFilter;
class CurveFittingWidget;
class CommentBox;

class LeftPanel : public QWidget {
    Q_OBJECT

public:
    explicit LeftPanel(QWidget* parent = nullptr);

    AxisSelection* axisSelection;
    SmoothingOptions* smoothingOptions;
    DataFilter* dataFilter;
    CurveFittingWidget* curveFitting;
    CommentBox* commentBox;

    void updateOptions(const QStringList& columns);
};
