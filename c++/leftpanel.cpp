#include "leftpanel.h"
#include "axisselection.h"
#include "smoothingoptions.h"
#include "datafilter.h"
#include "curvefittingwidget.h"
#include "commentbox.h"

#include <QVBoxLayout>

LeftPanel::LeftPanel(QWidget* parent)
    : QWidget(parent)
{
    auto* layout = new QVBoxLayout(this);

    axisSelection = new AxisSelection(this);
    smoothingOptions = new SmoothingOptions(this);
    dataFilter = new DataFilter(this);
    curveFitting = new CurveFittingWidget(this);
    commentBox = new CommentBox(this);

    layout->addWidget(axisSelection);
    layout->addWidget(dataFilter);
    layout->addWidget(smoothingOptions);
    layout->addWidget(curveFitting);
    layout->addWidget(commentBox);
    layout->addStretch(1);

    // Initialize components as hidden
    smoothingOptions->hide();
    commentBox->hide();
    dataFilter->hide();
    curveFitting->hide();
}

void LeftPanel::updateOptions(const QStringList& columns)
{
    axisSelection->updateOptions(columns);
    dataFilter->updateColumns(columns);
}
