#pragma once

#include <QDialog>
#include <QComboBox>
#include <QLabel>
#include <QPushButton>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QDialogButtonBox>

class SheetSelectionDialog : public QDialog {
    Q_OBJECT

public:
    explicit SheetSelectionDialog(const QStringList& sheets, QWidget* parent = nullptr);

    QString getSelectedSheet() const;

    // Static convenience method
    static QString selectSheet(const QStringList& sheets, QWidget* parent = nullptr);

private:
    void setupUi(const QStringList& sheets);

    QComboBox* sheetCombo;
};
