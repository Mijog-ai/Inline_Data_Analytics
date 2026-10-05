#include "toolbar.h"
#include "mainwindow.h"

#include <QAction>
#include <QFileInfo>
#include <QLoggingCategory>

static Q_LOGGING_CATEGORY(lcToolBar, "app.toolbar")

ToolBar::ToolBar(QWidget* parent)
    : QToolBar(tr("Main"), parent)
    , mainWindow(qobject_cast<MainWindow*>(parent))
{
    auto* loadAction = new QAction(tr("Load Data"), this);
    connect(loadAction, &QAction::triggered, this, &ToolBar::loadFileTriggered);
    addAction(loadAction);

    auto* saveDataAction = new QAction(tr("Save Data"), this);
    connect(saveDataAction, &QAction::triggered, mainWindow, &MainWindow::saveData);
    addAction(saveDataAction);

    auto* savePlotAction = new QAction(tr("Save Plot"), this);
    connect(savePlotAction, &QAction::triggered, mainWindow, &MainWindow::savePlot);
    addAction(savePlotAction);

    addSeparator();

    fileLabel = new QLabel(tr("No file loaded"), this);
    fileLabel->setAlignment(Qt::AlignCenter);
    addWidget(fileLabel);
}

void ToolBar::updateFileName(const QString& filePath)
{
    if (!filePath.isEmpty()) {
        QString fileName = QFileInfo(filePath).fileName();
        fileLabel->setText(tr("Loaded file: %1").arg(fileName));
    } else {
        fileLabel->setText(tr("No file loaded"));
    }
}

void ToolBar::loadFileTriggered()
{
    qCInfo(lcToolBar) << "Load File toolbar button clicked";
    if (mainWindow) {
        mainWindow->loadFile();
    } else {
        qCCritical(lcToolBar) << "MainWindow pointer is null";
    }
}
