#pragma once

#include <QObject>
#include <QString>
#include <QStringList>
#include <QVariantMap>
#include <QVector>

class MainWindow;

// Saves and restores the *options* the user has selected (axis choice,
// smoothing, curve fit, data filter, plot view) independently of the loaded
// data, so a saved preset can be applied to any dataset.
//
// Presets are stored as one JSON file per preset in a "presets" folder beside
// the executable, and an index.json in the same folder acts as the small
// database listing every preset and its metadata.
class PresetManager : public QObject {
    Q_OBJECT

public:
    explicit PresetManager(MainWindow* mainWindow, QObject* parent = nullptr);

    // Folder beside the executable where presets live (created on demand).
    QString presetsDir() const;

    // All preset names currently stored, sorted alphabetically.
    QStringList listPresets() const;

    // Capture the current UI options into a settings map (no data).
    QVariantMap captureCurrentSettings() const;
    // Apply a settings map to the current UI and replot.
    void applySettings(const QVariantMap& settings);

    // Write the current options as a preset with the given name.
    // Overwrites an existing preset of the same name. Returns true on success.
    bool savePreset(const QString& name, QString* errorOut = nullptr);
    // Load a stored preset and apply it to the current data.
    bool loadPreset(const QString& name, QString* errorOut = nullptr);
    // Remove a stored preset. Returns true on success.
    bool deletePreset(const QString& name, QString* errorOut = nullptr);

private:
    // If the saved dividers fall outside the available data range, ask the user
    // whether to recreate the same number of evenly spaced segments across the
    // current data; otherwise leave the dividers untouched.
    void fitDividersToData(QVector<double>& dividers, const QVector<double>& data,
                           const QString& axisLabel);

    QString presetFilePath(const QString& name) const;
    QString indexFilePath() const;
    void updateIndex();  // rewrite index.json from the preset files on disk

    MainWindow* mainWindow;

    static constexpr int PRESET_VERSION = 1;
};
