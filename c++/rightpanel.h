#pragma once

#include <QWidget>

class PlotArea;
class StatisticsArea;

class RightPanel : public QWidget {
    Q_OBJECT

public:
    explicit RightPanel(QWidget* parent = nullptr);

    PlotArea* plotArea;
    StatisticsArea* statisticsArea;
};
