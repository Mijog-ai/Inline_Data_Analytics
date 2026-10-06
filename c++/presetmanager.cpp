#include "presetmanager.h"
#include "mainwindow.h"
#include "leftpanel.h"
#include "rightpanel.h"
#include "axisselection.h"
#include "smoothingoptions.h"
#include "datafilter.h"
#include "curvefittingwidget.h"
#include "plotarea.h"

#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QDateTime>
#include <QMessageBox>

PresetManager::PresetManager(MainWindow* mainWindow, QObject* parent)
    : QObject(parent)
    , mainWindow(mainWindow)
{
}

QString PresetManager::presetsDir() const
{
    QDir dir(QCoreApplication::applicationDirPath());
    const QString sub = QStringLiteral("presets");
    if (!dir.exists(sub))
        dir.mkpath(sub);
    return dir.absoluteFilePath(sub);
}

QString PresetManager::presetFilePath(const QString& name) const
{
    // Sanitize the name into a safe file name while keeping it readable.
    QString safe = name;
    static const QString illegal = QStringLiteral("<>:\"/\\|?*");
    for (QChar& c : safe) {
        if (illegal.contains(c))
            c = QLatin1Char('_');
    }
    return QDir(presetsDir()).absoluteFilePath(safe + QStringLiteral(".json"));
}

QString PresetManager::indexFilePath() const
{
    return QDir(presetsDir()).absoluteFilePath(QStringLiteral("index.json"));
}

QStringList PresetManager::listPresets() const
{
    QDir dir(presetsDir());
    QStringList names;
    const QStringList files = dir.entryList({QStringLiteral("*.json")}, QDir::Files, QDir::Name);
    for (const QString& file : files) {
        if (file == QStringLiteral("index.json"))
            continue;
        // Prefer the name recorded inside the file; fall back to the base name.
        QFile f(dir.absoluteFilePath(file));
        QString name;
        if (f.open(QIODevice::ReadOnly)) {
            const QJsonObject obj = QJsonDocument::fromJson(f.readAll()).object();
            name = obj.value(QStringLiteral("name")).toString();
            f.close();
        }
        if (name.isEmpty())
            name = QFileInfo(file).completeBaseName();
        names.append(name);
    }
    names.sort(Qt::CaseInsensitive);
    names.removeDuplicates();
    return names;
}

QVariantMap PresetManager::captureCurrentSettings() const
{
    QVariantMap s;

    // Axis selection
    s[QStringLiteral("xColumn")] = mainWindow->leftPanel->axisSelection->xColumn();
    s[QStringLiteral("yColumns")] = mainWindow->leftPanel->axisSelection->yColumns();

    // Smoothing parameters
    s[QStringLiteral("smoothing")] = mainWindow->leftPanel->smoothingOptions->getParams();

    // Curve fitting
    s[QStringLiteral("fitType")] = mainWindow->leftPanel->curveFitting->fitType->currentText();
    s[QStringLiteral("fitDegree")] = mainWindow->leftPanel->curveFitting->degreeSpinbox->value();

    // Data filter
    s[QStringLiteral("filterColumn")] = mainWindow->leftPanel->dataFilter->filterColumn->currentText();
    s[QStringLiteral("filterMin")] = mainWindow->leftPanel->dataFilter->minValue->text();
    s[QStringLiteral("filterMax")] = mainWindow->leftPanel->dataFilter->maxValue->text();

    // Plot view
    s[QStringLiteral("showOriginal")] = mainWindow->rightPanel->plotArea->getShowOriginalState();

    // Partitioning: divider lines + active branch and selected segments.
    QVariantList partitionX, partitionY;
    for (double v : mainWindow->partitionDividers)
        partitionX.append(v);
    for (double v : mainWindow->partitionDividersH)
        partitionY.append(v);
    s[QStringLiteral("partitionX")] = partitionX;
    s[QStringLiteral("partitionY")] = partitionY;
    s[QStringLiteral("activeBranch")] = mainWindow->activeBranch;
    s[QStringLiteral("activePartition")] = mainWindow->activePartition;
    s[QStringLiteral("activePartitionY")] = mainWindow->activePartitionY;

    return s;
}

void PresetManager::applySettings(const QVariantMap& s)
{
    // Axis selection - only apply columns that exist in the current data.
    const QString xColumn = s.value(QStringLiteral("xColumn")).toString();
    const QStringList yColumns = s.value(QStringLiteral("yColumns")).toStringList();

    if (!xColumn.isEmpty()) {
        int xIdx = mainWindow->leftPanel->axisSelection->xCombo->findText(xColumn);
        if (xIdx >= 0)
            mainWindow->leftPanel->axisSelection->xCombo->setCurrentIndex(xIdx);
    }

    mainWindow->leftPanel->axisSelection->yList->clearSelection();
    for (const QString& yCol : yColumns) {
        const auto items = mainWindow->leftPanel->axisSelection->yList->findItems(yCol, Qt::MatchExactly);
        for (auto* item : items)
            item->setSelected(true);
    }

    // Smoothing
    mainWindow->leftPanel->smoothingOptions->setParams(
        s.value(QStringLiteral("smoothing")).toMap());

    // Curve fitting
    const QString fitType = s.value(QStringLiteral("fitType")).toString();
    int fitIdx = mainWindow->leftPanel->curveFitting->fitType->findText(fitType);
    if (fitIdx >= 0)
        mainWindow->leftPanel->curveFitting->fitType->setCurrentIndex(fitIdx);
    mainWindow->leftPanel->curveFitting->degreeSpinbox->setValue(
        s.value(QStringLiteral("fitDegree")).toInt());

    // Data filter - keep the current column list, just set the selection/values.
    mainWindow->leftPanel->dataFilter->setFilter(
        s.value(QStringLiteral("filterColumn")).toString(),
        s.value(QStringLiteral("filterMin")).toString(),
        s.value(QStringLiteral("filterMax")).toString());

    // Plot view
    mainWindow->rightPanel->plotArea->setShowOriginalState(
        s.value(QStringLiteral("showOriginal")).toBool());

    // Redraw with the applied options, then restore the partition configuration
    // on top of the freshly drawn plot.
    if (!mainWindow->df.isEmpty()) {
        mainWindow->updatePlot();

        QVector<double> partitionX, partitionY;
        for (const QVariant& v : s.value(QStringLiteral("partitionX")).toList())
            partitionX.append(v.toDouble());
        for (const QVariant& v : s.value(QStringLiteral("partitionY")).toList())
            partitionY.append(v.toDouble());

        // If the saved dividers don't fit the current data (the data doesn't
        // cover those values), offer to recreate the SAME NUMBER of segments
        // spread evenly across the data that IS available. When they do fit,
        // apply them unchanged so the same segmentation is reproduced.
        const auto& items = mainWindow->rightPanel->plotArea->plotItems;
        if (!items.isEmpty()) {
            fitDividersToData(partitionX, items.first().xData, QStringLiteral("X"));
            fitDividersToData(partitionY, items.first().yData, QStringLiteral("Y"));
        }

        mainWindow->rightPanel->plotArea->applyPartitionState(
            partitionX, partitionY,
            s.value(QStringLiteral("activeBranch"), 0).toInt(),
            s.value(QStringLiteral("activePartition"), -1).toInt(),
            s.value(QStringLiteral("activePartitionY"), -1).toInt());
    }
}

void PresetManager::fitDividersToData(QVector<double>& dividers,
                                      const QVector<double>& data,
                                      const QString& axisLabel)
{
    if (dividers.isEmpty() || data.isEmpty())
        return;

    double dataMin = data.first();
    double dataMax = data.first();
    for (double v : data) {
        dataMin = qMin(dataMin, v);
        dataMax = qMax(dataMax, v);
    }
    if (dataMax <= dataMin)
        return;

    // A divider "fits" when it lies inside the available data range.
    bool allFit = true;
    for (double d : dividers) {
        if (d < dataMin || d > dataMax) {
            allFit = false;
            break;
        }
    }
    if (allFit)
        return;  // same data (or compatible) -> keep the exact saved segmentation

    const int count = dividers.size();
    const int segments = count + 1;
    auto reply = QMessageBox::question(
        mainWindow, QObject::tr("Partitions Don't Fit Data"),
        QObject::tr("This preset defines %1 %2 segment(s), but its divider "
                    "positions fall outside the current data range.\n\n"
                    "Create %1 equal %2 segment(s) across the available data instead?")
            .arg(segments).arg(axisLabel),
        QMessageBox::Yes | QMessageBox::No);

    if (reply == QMessageBox::Yes) {
        // Spread `count` dividers evenly, producing `count + 1` equal segments.
        QVector<double> fresh;
        for (int i = 1; i <= count; ++i)
            fresh.append(dataMin + (dataMax - dataMin) * i / segments);
        dividers = fresh;
    } else {
        dividers.clear();  // skip partitioning for this axis
    }
}

bool PresetManager::savePreset(const QString& name, QString* errorOut)
{
    if (name.trimmed().isEmpty()) {
        if (errorOut) *errorOut = tr("Preset name cannot be empty.");
        return false;
    }

    QJsonObject obj;
    obj[QStringLiteral("name")] = name;
    obj[QStringLiteral("version")] = PRESET_VERSION;
    obj[QStringLiteral("savedAt")] = QDateTime::currentDateTime().toString(Qt::ISODate);
    obj[QStringLiteral("settings")] = QJsonObject::fromVariantMap(captureCurrentSettings());

    QFile file(presetFilePath(name));
    if (!file.open(QIODevice::WriteOnly | QIODevice::Truncate)) {
        if (errorOut) *errorOut = tr("Cannot write preset file: %1").arg(file.errorString());
        return false;
    }
    file.write(QJsonDocument(obj).toJson(QJsonDocument::Indented));
    file.close();

    updateIndex();
    return true;
}

bool PresetManager::loadPreset(const QString& name, QString* errorOut)
{
    QFile file(presetFilePath(name));
    if (!file.open(QIODevice::ReadOnly)) {
        if (errorOut) *errorOut = tr("Cannot open preset '%1': %2").arg(name, file.errorString());
        return false;
    }
    const QJsonDocument doc = QJsonDocument::fromJson(file.readAll());
    file.close();

    if (!doc.isObject()) {
        if (errorOut) *errorOut = tr("Preset '%1' is not valid.").arg(name);
        return false;
    }

    const QVariantMap settings = doc.object().value(QStringLiteral("settings")).toObject().toVariantMap();
    applySettings(settings);
    return true;
}

bool PresetManager::deletePreset(const QString& name, QString* errorOut)
{
    QFile file(presetFilePath(name));
    if (!file.exists()) {
        if (errorOut) *errorOut = tr("Preset '%1' does not exist.").arg(name);
        return false;
    }
    if (!file.remove()) {
        if (errorOut) *errorOut = tr("Cannot delete preset '%1': %2").arg(name, file.errorString());
        return false;
    }
    updateIndex();
    return true;
}

void PresetManager::updateIndex()
{
    QDir dir(presetsDir());
    QJsonArray entries;
    const QStringList files = dir.entryList({QStringLiteral("*.json")}, QDir::Files, QDir::Name);
    for (const QString& file : files) {
        if (file == QStringLiteral("index.json"))
            continue;
        QFile f(dir.absoluteFilePath(file));
        if (!f.open(QIODevice::ReadOnly))
            continue;
        const QJsonObject obj = QJsonDocument::fromJson(f.readAll()).object();
        f.close();

        QJsonObject entry;
        entry[QStringLiteral("name")] = obj.value(QStringLiteral("name")).toString(
            QFileInfo(file).completeBaseName());
        entry[QStringLiteral("file")] = file;
        entry[QStringLiteral("savedAt")] = obj.value(QStringLiteral("savedAt")).toString();
        entries.append(entry);
    }

    QJsonObject index;
    index[QStringLiteral("version")] = PRESET_VERSION;
    index[QStringLiteral("updatedAt")] = QDateTime::currentDateTime().toString(Qt::ISODate);
    index[QStringLiteral("presets")] = entries;

    QFile indexFile(indexFilePath());
    if (indexFile.open(QIODevice::WriteOnly | QIODevice::Truncate)) {
        indexFile.write(QJsonDocument(index).toJson(QJsonDocument::Indented));
        indexFile.close();
    }
}
