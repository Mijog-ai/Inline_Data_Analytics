#include "toolbar.h"
#include "mainwindow.h"
#include "presetmanager.h"

#include <QAction>
#include <QFileInfo>
#include <QInputDialog>
#include <QLineEdit>
#include <QMessageBox>
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

    // --- Preset controls -------------------------------------------------
    addWidget(new QLabel(tr("Preset:"), this));

    presetCombo = new QComboBox(this);
    presetCombo->setMinimumWidth(160);
    presetCombo->setToolTip(tr("Saved option presets (stored beside the application)"));
    addWidget(presetCombo);

    auto* loadPresetAction = new QAction(tr("Load Preset"), this);
    loadPresetAction->setToolTip(tr("Apply the selected preset to the current data"));
    connect(loadPresetAction, &QAction::triggered, this, &ToolBar::onLoadPreset);
    addAction(loadPresetAction);

    auto* savePresetAction = new QAction(tr("Save Preset"), this);
    savePresetAction->setToolTip(tr("Save the current options as a named preset"));
    connect(savePresetAction, &QAction::triggered, this, &ToolBar::onSavePreset);
    addAction(savePresetAction);

    auto* deletePresetAction = new QAction(tr("Delete Preset"), this);
    connect(deletePresetAction, &QAction::triggered, this, &ToolBar::onDeletePreset);
    addAction(deletePresetAction);

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

void ToolBar::refreshPresetList()
{
    if (!mainWindow || !mainWindow->presetManager)
        return;

    const QString current = presetCombo->currentText();
    presetCombo->blockSignals(true);
    presetCombo->clear();
    presetCombo->addItems(mainWindow->presetManager->listPresets());
    int idx = presetCombo->findText(current);
    if (idx >= 0)
        presetCombo->setCurrentIndex(idx);
    presetCombo->blockSignals(false);
}

void ToolBar::onSavePreset()
{
    if (!mainWindow || !mainWindow->presetManager)
        return;

    bool ok = false;
    const QString name = QInputDialog::getText(
        mainWindow, tr("Save Preset"),
        tr("Preset name:"), QLineEdit::Normal,
        presetCombo->currentText(), &ok).trimmed();

    if (!ok || name.isEmpty())
        return;

    if (mainWindow->presetManager->listPresets().contains(name, Qt::CaseInsensitive)) {
        auto reply = QMessageBox::question(
            mainWindow, tr("Overwrite Preset?"),
            tr("A preset named '%1' already exists. Overwrite it?").arg(name),
            QMessageBox::Yes | QMessageBox::No);
        if (reply != QMessageBox::Yes)
            return;
    }

    QString error;
    if (!mainWindow->presetManager->savePreset(name, &error)) {
        QMessageBox::critical(mainWindow, tr("Error"), error);
        return;
    }

    refreshPresetList();
    int idx = presetCombo->findText(name);
    if (idx >= 0)
        presetCombo->setCurrentIndex(idx);

    QMessageBox::information(mainWindow, tr("Preset Saved"),
        tr("Preset '%1' saved beside the application.").arg(name));
}

void ToolBar::onLoadPreset()
{
    if (!mainWindow || !mainWindow->presetManager)
        return;

    const QString name = presetCombo->currentText();
    if (name.isEmpty()) {
        QMessageBox::information(mainWindow, tr("Load Preset"),
            tr("No preset selected."));
        return;
    }

    QString error;
    if (!mainWindow->presetManager->loadPreset(name, &error)) {
        QMessageBox::critical(mainWindow, tr("Error"), error);
        return;
    }
}

void ToolBar::onDeletePreset()
{
    if (!mainWindow || !mainWindow->presetManager)
        return;

    const QString name = presetCombo->currentText();
    if (name.isEmpty())
        return;

    auto reply = QMessageBox::question(
        mainWindow, tr("Delete Preset?"),
        tr("Delete preset '%1'? This cannot be undone.").arg(name),
        QMessageBox::Yes | QMessageBox::No);
    if (reply != QMessageBox::Yes)
        return;

    QString error;
    if (!mainWindow->presetManager->deletePreset(name, &error)) {
        QMessageBox::critical(mainWindow, tr("Error"), error);
        return;
    }
    refreshPresetList();
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
