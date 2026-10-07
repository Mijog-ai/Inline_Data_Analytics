#pragma once

#include <QMenuBar>

class MainWindow;

class MenuBar : public QMenuBar {
    Q_OBJECT

public:
    explicit MenuBar(QWidget* parent = nullptr);
    void addEditActions(QAction* smoothing, QAction* comment, QAction* filter, QAction* curveFit);

private slots:
    void loadFileTriggered();
    void saveSession();
    void loadSession();
    void newSession();
    void changeLanguage(const QString& code);

protected:
    void changeEvent(QEvent* event) override;

private:
    void retranslateUi();

    QMenu* fileMenu;
    QMenu* editMenu;
    QMenu* settingsMenu;
    QMenu* languageMenu;
    QAction* loadAction;
    QAction* saveDataAction;
    QAction* savePlotAction;
    QAction* exportTableAction;
    QAction* newSessionAction;
    QAction* saveSessionAction;
    QAction* loadSessionAction;
    QAction* exitAction;
    QAction* germanAction;
    QAction* englishAction;
    MainWindow* mainWindow;
};
