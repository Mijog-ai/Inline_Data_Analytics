#pragma once

#include <QToolBar>
#include <QLabel>

class MainWindow;

class ToolBar : public QToolBar {
    Q_OBJECT

public:
    explicit ToolBar(QWidget* parent = nullptr);
    void updateFileName(const QString& filePath);

private slots:
    void loadFileTriggered();

private:
    QLabel* fileLabel;
    MainWindow* mainWindow;
};
