#include "sessionmanager.h"
#include "mainwindow.h"
#include "leftpanel.h"
#include "rightpanel.h"
#include "axisselection.h"
#include "smoothingoptions.h"
#include "datafilter.h"
#include "curvefittingwidget.h"
#include "commentbox.h"
#include "plotarea.h"
#include "statisticsarea.h"

#include <QFileDialog>
#include <QMessageBox>
#include <QProgressDialog>
#include <QDataStream>
#include <QFile>
#include <QCoreApplication>

SessionManager::SessionManager(MainWindow* mainWindow, QObject* parent)
    : QObject(parent)
    , mainWindow(mainWindow)
{
}

void SessionManager::saveSession()
{
    QString fileName = QFileDialog::getSaveFileName(
        mainWindow, tr("Save Session"), QString(),
        tr("Inline Analytics Files (*.inlingh)"));

    if (fileName.isEmpty())
        return;

    if (!fileName.endsWith(".inlingh"))
        fileName += ".inlingh";

    QProgressDialog progress(tr("Saving session..."), tr("Cancel"), 0, 100, mainWindow);
    progress.setWindowModality(Qt::WindowModal);
    progress.setMinimumDuration(0);
    progress.setValue(0);

    QFile file(fileName);
    if (!file.open(QIODevice::WriteOnly)) {
        QMessageBox::critical(mainWindow, tr("Error"),
            tr("Cannot open file for writing: %1").arg(file.errorString()));
        return;
    }

    QDataStream out(&file);
    out.setVersion(QDataStream::Qt_6_0);

    // Write magic and version
    out << SESSION_MAGIC;
    out << SESSION_VERSION;

    progress.setValue(10);
    QCoreApplication::processEvents();

    // Save DataFrames
    out << mainWindow->df.serialize();
    out << mainWindow->originalDf.serialize();
    out << mainWindow->filteredDf.serialize();

    progress.setValue(30);
    QCoreApplication::processEvents();

    // Save axis selections
    out << mainWindow->leftPanel->axisSelection->xColumn();
    out << mainWindow->leftPanel->axisSelection->yColumns();

    progress.setValue(40);
    QCoreApplication::processEvents();

    // Save smoothing params
    out << mainWindow->leftPanel->smoothingOptions->getParams();

    // Save curve fitting state
    out << mainWindow->leftPanel->curveFitting->fitType->currentText();
    out << mainWindow->leftPanel->curveFitting->degreeSpinbox->value();

    progress.setValue(50);
    QCoreApplication::processEvents();

    // Save comments
    out << mainWindow->leftPanel->commentBox->getComments();

    // Save data filter settings
    out << mainWindow->leftPanel->dataFilter->filterColumn->currentText();
    out << mainWindow->leftPanel->dataFilter->minValue->text();
    out << mainWindow->leftPanel->dataFilter->maxValue->text();
    // Save all filter column names
    QStringList filterColumns;
    for (int i = 0; i < mainWindow->leftPanel->dataFilter->filterColumn->count(); ++i) {
        filterColumns.append(mainWindow->leftPanel->dataFilter->filterColumn->itemText(i));
    }
    out << filterColumns;

    progress.setValue(70);
    QCoreApplication::processEvents();

    // Save statistics
    out << mainWindow->rightPanel->statisticsArea->getStats();

    // Save plot state
    out << mainWindow->rightPanel->plotArea->getShowOriginalState();

    progress.setValue(90);
    QCoreApplication::processEvents();

    file.close();
    progress.setValue(100);

    mainWindow->unsavedChanges = false;
    QMessageBox::information(mainWindow, tr("Success"), tr("Session saved successfully!"));
}

void SessionManager::loadSession()
{
    QString fileName = QFileDialog::getOpenFileName(
        mainWindow, tr("Load Session"), QString(),
        tr("Inline Analytics Files (*.inlingh)"));

    if (fileName.isEmpty())
        return;

    QProgressDialog progress(tr("Loading session..."), tr("Cancel"), 0, 100, mainWindow);
    progress.setWindowModality(Qt::WindowModal);
    progress.setMinimumDuration(0);
    progress.setValue(0);

    QFile file(fileName);
    if (!file.open(QIODevice::ReadOnly)) {
        QMessageBox::critical(mainWindow, tr("Error"),
            tr("Cannot open file: %1").arg(file.errorString()));
        return;
    }

    QDataStream in(&file);
    in.setVersion(QDataStream::Qt_6_0);

    // Read and verify magic and version
    quint32 magic = 0;
    quint32 version = 0;
    in >> magic >> version;

    if (magic != SESSION_MAGIC) {
        QMessageBox::critical(mainWindow, tr("Error"), tr("Invalid session file format."));
        file.close();
        return;
    }

    if (version > SESSION_VERSION) {
        QMessageBox::critical(mainWindow, tr("Error"),
            tr("Session file was created with a newer version of the application."));
        file.close();
        return;
    }

    progress.setValue(10);
    QCoreApplication::processEvents();

    // Load DataFrames
    QByteArray dfData, origDfData, filtDfData;
    in >> dfData >> origDfData >> filtDfData;
    mainWindow->df = DataFrame::deserialize(dfData);
    mainWindow->originalDf = DataFrame::deserialize(origDfData);
    mainWindow->filteredDf = DataFrame::deserialize(filtDfData);

    progress.setValue(30);
    QCoreApplication::processEvents();

    // Load axis selections
    QString xColumn;
    QStringList yColumns;
    in >> xColumn >> yColumns;

    mainWindow->leftPanel->axisSelection->updateOptions(mainWindow->df.columnNames());
    int xIdx = mainWindow->leftPanel->axisSelection->xCombo->findText(xColumn);
    if (xIdx >= 0)
        mainWindow->leftPanel->axisSelection->xCombo->setCurrentIndex(xIdx);

    mainWindow->leftPanel->axisSelection->yList->clearSelection();
    for (const auto& yCol : yColumns) {
        auto items = mainWindow->leftPanel->axisSelection->yList->findItems(yCol, Qt::MatchExactly);
        for (auto* item : items) {
            item->setSelected(true);
        }
    }

    progress.setValue(40);
    QCoreApplication::processEvents();

    // Load smoothing params
    QVariantMap smoothingParams;
    in >> smoothingParams;
    mainWindow->leftPanel->smoothingOptions->setParams(smoothingParams);

    // Load curve fitting state
    QString fitTypeText;
    int fitDegree;
    in >> fitTypeText >> fitDegree;
    int fitIdx = mainWindow->leftPanel->curveFitting->fitType->findText(fitTypeText);
    if (fitIdx >= 0)
        mainWindow->leftPanel->curveFitting->fitType->setCurrentIndex(fitIdx);
    mainWindow->leftPanel->curveFitting->degreeSpinbox->setValue(fitDegree);

    progress.setValue(50);
    QCoreApplication::processEvents();

    // Load comments
    QString comments;
    in >> comments;
    mainWindow->leftPanel->commentBox->setComments(comments);

    // Load data filter settings
    QString filterCol, filterMin, filterMax;
    QStringList filterColumns;
    in >> filterCol >> filterMin >> filterMax >> filterColumns;
    mainWindow->leftPanel->dataFilter->updateColumns(filterColumns);
    mainWindow->leftPanel->dataFilter->setFilter(filterCol, filterMin, filterMax);

    progress.setValue(70);
    QCoreApplication::processEvents();

    // Load statistics
    QVariantList stats;
    in >> stats;
    mainWindow->rightPanel->statisticsArea->setStats(stats);

    // Load plot state
    bool showOriginal;
    in >> showOriginal;
    mainWindow->rightPanel->plotArea->setShowOriginalState(showOriginal);

    progress.setValue(90);
    QCoreApplication::processEvents();

    file.close();

    // Refresh the plot
    mainWindow->updatePlot();

    progress.setValue(100);
    mainWindow->unsavedChanges = false;
    QMessageBox::information(mainWindow, tr("Success"), tr("Session loaded successfully!"));
}

void SessionManager::newSession()
{
    // Check for unsaved changes
    if (mainWindow->unsavedChanges) {
        auto reply = QMessageBox::question(
            mainWindow, tr("Save Changes?"),
            tr("Do you want to save the current session before creating a new one?"),
            QMessageBox::Yes | QMessageBox::No | QMessageBox::Cancel);

        if (reply == QMessageBox::Yes) {
            saveSession();
        } else if (reply == QMessageBox::Cancel) {
            return;
        }
    }

    // Clear plot first to prevent errors
    mainWindow->rightPanel->plotArea->clearPlot();

    // Clear all data
    mainWindow->clearAllData();

    // Reset UI
    mainWindow->resetUi();

    QMessageBox::information(mainWindow, tr("New Session"), tr("A new session has been created."));
}
