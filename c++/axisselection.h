#pragma once

#include <QGroupBox>
#include <QComboBox>
#include <QListWidget>
#include <QVBoxLayout>
#include <QLabel>

class AxisSelection : public QGroupBox {
    Q_OBJECT

public:
    explicit AxisSelection(QWidget* parent = nullptr);

    QComboBox* xCombo;
    QListWidget* yList;

    void updateOptions(const QStringList& columns);
    void reset();

    QString xColumn() const;
    QStringList yColumns() const;

private slots:
    void onSelectionChanged();
    void onYSelectionChanged();

protected:
    void changeEvent(QEvent* event) override;

private:
    void setupUi();
    void retranslateUi();
    QLabel* xLabel = nullptr;
    QLabel* yLabel = nullptr;

    void limitYSelection();
    static constexpr int MAX_Y_COLUMNS = 3;
};
