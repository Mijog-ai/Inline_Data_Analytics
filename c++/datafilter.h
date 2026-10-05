#pragma once

#include <QGroupBox>
#include <QComboBox>
#include <QLineEdit>
#include <QPushButton>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>

class DataFilter : public QGroupBox {
    Q_OBJECT

public:
    explicit DataFilter(QWidget* parent = nullptr);

    QComboBox* filterColumn;
    QLineEdit* minValue;
    QLineEdit* maxValue;
    QPushButton* applyFilter;

    void updateColumns(const QStringList& columns);
    void setFilter(const QString& column, const QString& minVal, const QString& maxVal);
    void reset();

private slots:
    void onApplyClicked();

private:
    void setupUi();
};
