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

private:
    QMenu* fileMenu;
    QMenu* editMenu;
    MainWindow* mainWindow;
};
