#pragma once

#include <QGroupBox>
#include <QComboBox>
#include <QSpinBox>
#include <QPushButton>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>

class CurveFittingWidget : public QGroupBox {
    Q_OBJECT

public:
    explicit CurveFittingWidget(QWidget* parent = nullptr);

    QComboBox* fitType;
    QSpinBox* degreeSpinbox;
    QPushButton* applyFitButton;
    QPushButton* removeFitButton;

    void reset();

private slots:
    void onFitTypeChanged(int index);
    void onApplyFit();
    void onRemoveFit();

protected:
    void changeEvent(QEvent* event) override;

private:
    void setupUi();
    void retranslateUi();
    QLabel* typeLabel = nullptr;
    QLabel* degreeLabel = nullptr;

};
