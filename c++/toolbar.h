#pragma once

#include <QToolBar>
#include <QLabel>
#include <QComboBox>

class MainWindow;

class ToolBar : public QToolBar {
    Q_OBJECT

public:
    explicit ToolBar(QWidget* parent = nullptr);
    void updateFileName(const QString& filePath);

    // Reload the preset dropdown from the presets stored beside the exe.
    void refreshPresetList();

private slots:
    void loadFileTriggered();
    void onSavePreset();
    void onLoadPreset();
    void onDeletePreset();

protected:
    void changeEvent(QEvent* event) override;

private:
    void retranslateUi();

    QString currentFilePath;
    QAction* loadAction;
    QAction* saveDataAction;
    QAction* savePlotAction;
    QLabel* presetLabel;
    QAction* loadPresetAction;
    QAction* savePresetAction;
    QAction* deletePresetAction;
    QLabel* fileLabel;
    QComboBox* presetCombo;
    MainWindow* mainWindow;
};
