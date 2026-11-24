#pragma once

#include <QDialog>
#include <QListWidget>
#include <QLabel>
#include <QPushButton>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QDialogButtonBox>

class SheetSelectionDialog : public QDialog {
    Q_OBJECT

public:
    explicit SheetSelectionDialog(const QStringList& sheets, QWidget* parent = nullptr);

    QStringList getSelectedSheets() const;
    QString getSelectedSheet() const;  // first selected sheet

    // Static convenience method
    static QString selectSheet(const QStringList& sheets, QWidget* parent = nullptr);

private:
    void setupUi(const QStringList& sheets);

    QListWidget* sheetList;
};
