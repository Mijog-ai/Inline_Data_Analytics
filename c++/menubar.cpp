#include "menubar.h"
#include "mainwindow.h"
#include "sessionmanager.h"
#include "language.h"

#include <QAction>
#include <QActionGroup>
#include <QMenu>
#include <QMessageBox>
#include <QEvent>
#include <QApplication>
#include <QLoggingCategory>

static Q_LOGGING_CATEGORY(lcMenuBar, "app.menubar")

MenuBar::MenuBar(QWidget* parent)
    : QMenuBar(parent)
    , mainWindow(qobject_cast<MainWindow*>(parent))
{
    // File menu
    fileMenu = addMenu(QString());

    loadAction = new QAction(this);
    connect(loadAction, &QAction::triggered, this, &MenuBar::loadFileTriggered);
    fileMenu->addAction(loadAction);

    saveDataAction = new QAction(this);
    connect(saveDataAction, &QAction::triggered, mainWindow, &MainWindow::saveData);
    fileMenu->addAction(saveDataAction);

    savePlotAction = new QAction(this);
    connect(savePlotAction, &QAction::triggered, mainWindow, &MainWindow::savePlot);
    fileMenu->addAction(savePlotAction);

    exportTableAction = new QAction(this);
    connect(exportTableAction, &QAction::triggered, mainWindow, &MainWindow::exportTableToExcel);
    fileMenu->addAction(exportTableAction);

    fileMenu->addSeparator();

    newSessionAction = new QAction(this);
    connect(newSessionAction, &QAction::triggered, this, &MenuBar::newSession);
    fileMenu->addAction(newSessionAction);

    saveSessionAction = new QAction(this);
    connect(saveSessionAction, &QAction::triggered, this, &MenuBar::saveSession);
    fileMenu->addAction(saveSessionAction);

    loadSessionAction = new QAction(this);
    connect(loadSessionAction, &QAction::triggered, this, &MenuBar::loadSession);
    fileMenu->addAction(loadSessionAction);

    fileMenu->addSeparator();

    exitAction = new QAction(this);
    connect(exitAction, &QAction::triggered, mainWindow, &QMainWindow::close);
    fileMenu->addAction(exitAction);

    // Edit menu (actions added later via addEditActions)
    editMenu = addMenu(QString());

    // Settings menu
    settingsMenu = addMenu(QString());
    languageMenu = settingsMenu->addMenu(QString());

    const QString currentLang = Language::current();
    auto* langGroup = new QActionGroup(this);
    langGroup->setExclusive(true);

    germanAction = new QAction(this);
    germanAction->setCheckable(true);
    germanAction->setChecked(currentLang == "de");
    connect(germanAction, &QAction::triggered, this, [this]() { changeLanguage("de"); });
    langGroup->addAction(germanAction);
    languageMenu->addAction(germanAction);

    englishAction = new QAction(this);
    englishAction->setCheckable(true);
    englishAction->setChecked(currentLang == "en");
    connect(englishAction, &QAction::triggered, this, [this]() { changeLanguage("en"); });
    langGroup->addAction(englishAction);
    languageMenu->addAction(englishAction);

    retranslateUi();
}

void MenuBar::changeEvent(QEvent* event)
{
    if (event->type() == QEvent::LanguageChange)
        retranslateUi();
    QMenuBar::changeEvent(event);
}

void MenuBar::retranslateUi()
{
    fileMenu->setTitle(tr("File"));
    loadAction->setText(tr("Load File"));
    saveDataAction->setText(tr("Save Data"));
    savePlotAction->setText(tr("Save Plot"));
    exportTableAction->setText(tr("Export Table to Excel"));
    newSessionAction->setText(tr("New Session"));
    saveSessionAction->setText(tr("Save Session"));
    loadSessionAction->setText(tr("Load Session"));
    exitAction->setText(tr("Exit"));
    editMenu->setTitle(tr("Edit"));
    settingsMenu->setTitle(tr("Settings"));
    languageMenu->setTitle(tr("Language"));
    germanAction->setText(tr("German"));
    englishAction->setText(tr("English"));
}

void MenuBar::changeLanguage(const QString& code)
{
    if (Language::current() == code)
        return;  // no change

    // Switches in place: all widgets re-translate themselves, data is kept.
    qCInfo(lcMenuBar) << "Switching language to" << code;
    Language::apply(code);
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
