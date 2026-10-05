#include "rightpanel.h"
#include "plotarea.h"
#include "statisticsarea.h"

#include <QVBoxLayout>
#include <QSplitter>

RightPanel::RightPanel(QWidget* parent)
    : QWidget(parent)
{
    auto* layout = new QVBoxLayout(this);

    plotArea = new PlotArea(this);
    statisticsArea = new StatisticsArea(this);

    auto* splitter = new QSplitter(Qt::Vertical, this);
    splitter->addWidget(plotArea);
    splitter->addWidget(statisticsArea);
    splitter->setSizes({700, 200});

    layout->addWidget(splitter);
}
