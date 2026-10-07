#pragma once

#include <QGroupBox>
#include <QCheckBox>
#include <QComboBox>
#include <QSlider>
#include <QSpinBox>
#include <QDoubleSpinBox>
#include <QPushButton>
#include <QLabel>
#include <QFormLayout>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QVariantMap>

class SmoothingOptions : public QGroupBox {
    Q_OBJECT

public:
    explicit SmoothingOptions(QWidget* parent = nullptr);

    QVariantMap getParams() const;
    void setParams(const QVariantMap& params);
    void reset();

signals:
    void paramsChanged();

private slots:
    void onSmoothingToggled(int state);
    void updateMethodDescription();
    void updateParameterVisibility();
    void updateWindowLabel(int value);
    void updateSigmaLabel(int value);
    void applyPreset(const QString& preset);

protected:
    void changeEvent(QEvent* event) override;

private:
    void setupUi();
    void retranslateUi();
    QLabel* methodLabel = nullptr;
    QLabel* windowLabel = nullptr;
    QLabel* polyOrderLabel = nullptr;
    QLabel* sigmaLabel = nullptr;
    QLabel* alphaLabel = nullptr;
    QLabel* lowessFracLabel = nullptr;
    QLabel* presetLabel = nullptr;

    void connectSignals();
    void hideAllParams();
    void showParam(const QString& paramName);
    void setLayoutVisible(QLayout* layout, bool visible);

    // Controls
    QCheckBox* smoothCheck;
    QComboBox* smoothMethod;
    QLabel* methodDescription;

    // Window size
    QSlider* windowSlider;
    QLabel* windowValueLabel;
    QVBoxLayout* windowContainer;

    // Polynomial order
    QSpinBox* polyOrder;

    // Sigma
    QSlider* sigmaSlider;
    QLabel* sigmaValueLabel;
    QVBoxLayout* sigmaContainer;

    // Alpha
    QDoubleSpinBox* alpha;

    // Lowess fraction
    QDoubleSpinBox* lowessFrac;

    // Preset buttons
    QPushButton* lightButton;
    QPushButton* mediumButton;
    QPushButton* heavyButton;

    // Layout tracking for show/hide
    QFormLayout* paramsLayout;

    // Row indices for each parameter in paramsLayout
    enum ParamRow {
        WindowRow = 0,
        PolyOrderRow = 1,
        SigmaRow = 2,
        AlphaRow = 3,
        LowessFracRow = 4
    };
};
