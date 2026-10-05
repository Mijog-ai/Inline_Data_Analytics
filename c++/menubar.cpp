#include "menubar.h"
#include "mainwindow.h"
#include "sessionmanager.h"

#include <QAction>
#include <QLoggingCategory>

static Q_LOGGING_CATEGORY(lcMenuBar, "app.menubar")

MenuBar::MenuBar(QWidget* parent)
    : QMenuBar(parent)
    , mainWindow(qobject_cast<MainWindow*>(parent))
{
    // File menu
    fileMenu = addMenu(tr("File"));

    auto* loadAction = new QAction(tr("Load File"), this);
    connect(loadAction, &QAction::triggered, this, &MenuBar::loadFileTriggered);
    fileMenu->addAction(loadAction);

    auto* saveDataAction = new QAction(tr("Save Data"), this);
    connect(saveDataAction, &QAction::triggered, mainWindow, &MainWindow::saveData);
    fileMenu->addAction(saveDataAction);

    auto* savePlotAction = new QAction(tr("Save Plot"), this);
    connect(savePlotAction, &QAction::triggered, mainWindow, &MainWindow::savePlot);
    fileMenu->addAction(savePlotAction);

    auto* exportTableAction = new QAction(tr("Export Table to Excel"), this);
    connect(exportTableAction, &QAction::triggered, mainWindow, &MainWindow::exportTableToExcel);
    fileMenu->addAction(exportTableAction);

    fileMenu->addSeparator();

    auto* newSessionAction = new QAction(tr("New Session"), this);
    connect(newSessionAction, &QAction::triggered, this, &MenuBar::newSession);
    fileMenu->addAction(newSessionAction);

    auto* saveSessionAction = new QAction(tr("Save Session"), this);
    connect(saveSessionAction, &QAction::triggered, this, &MenuBar::saveSession);
    fileMenu->addAction(saveSessionAction);

    auto* loadSessionAction = new QAction(tr("Load Session"), this);
    connect(loadSessionAction, &QAction::triggered, this, &MenuBar::loadSession);
    fileMenu->addAction(loadSessionAction);

    fileMenu->addSeparator();

    auto* exitAction = new QAction(tr("Exit"), this);
    connect(exitAction, &QAction::triggered, mainWindow, &QMainWindow::close);
    fileMenu->addAction(exitAction);

    // Edit menu (actions added later via addEditActions)
    editMenu = addMenu(tr("Edit"));
}

void MenuBar::addEditActions(QAction* smoothing, QAction* comment,
                             QAction* filter, QAction* curveFit)
{
    editMenu->addAction(smoothing);
    editMenu->addAction(comment);
    editMenu->addAction(filter);
    editMenu->addAction(curveFit);
}

void MenuBar::loadFileTriggered()
{
    qCInfo(lcMenuBar) << "Load File menu item clicked";
    if (mainWindow) {
        mainWindow->loadFile();
    } else {
        qCCritical(lcMenuBar) << "MainWindow pointer is null";
    }
}

void MenuBar::saveSession()
{
    if (mainWindow && mainWindow->sessionManager) {
        mainWindow->sessionManager->saveSession();
    } else {
        qCWarning(lcMenuBar) << "Session manager not initialized";
    }
}

void MenuBar::loadSession()
{
    if (mainWindow && mainWindow->sessionManager) {
        mainWindow->sessionManager->loadSession();
    } else {
        qCWarning(lcMenuBar) << "Session manager not initialized";
    }
}

void MenuBar::newSession()
{
    if (mainWindow && mainWindow->sessionManager) {
        mainWindow->sessionManager->newSession();
    } else {
        qCWarning(lcMenuBar) << "Session manager not initialized";
    }
}
