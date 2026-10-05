#include "sheetselectiondialog.h"

SheetSelectionDialog::SheetSelectionDialog(const QStringList& sheets, QWidget* parent)
    : QDialog(parent)
{
    setupUi(sheets);
}

void SheetSelectionDialog::setupUi(const QStringList& sheets)
{
    setWindowTitle("Select Sheet");
    setMinimumWidth(300);
    setModal(true);

    auto* layout = new QVBoxLayout(this);

    // Info label
    auto* infoLabel = new QLabel(
        "The selected file contains multiple sheets.\nPlease select the sheet to load:", this);
    infoLabel->setStyleSheet("font-size: 10pt; padding: 5px;");
    infoLabel->setWordWrap(true);
    layout->addWidget(infoLabel);

    // Sheet selection combo
    sheetCombo = new QComboBox(this);
    sheetCombo->addItems(sheets);
    sheetCombo->setToolTip("Select a sheet to load");
    sheetCombo->setStyleSheet(R"(
        QComboBox {
            padding: 5px;
            border: 1px solid #bdc3c7;
            border-radius: 4px;
        }
        QComboBox:focus {
            border: 1px solid #3498db;
        }
    )");
    layout->addWidget(sheetCombo);

    layout->addSpacing(10);

    // OK/Cancel buttons
    auto* buttonBox = new QDialogButtonBox(
        QDialogButtonBox::Ok | QDialogButtonBox::Cancel, this);
    buttonBox->button(QDialogButtonBox::Ok)->setStyleSheet(R"(
        QPushButton {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 6px 20px;
            border-radius: 3px;
            font-weight: bold;
        }
        QPushButton:hover { background-color: #2980b9; }
    )");
    layout->addWidget(buttonBox);

    connect(buttonBox, &QDialogButtonBox::accepted, this, &QDialog::accept);
    connect(buttonBox, &QDialogButtonBox::rejected, this, &QDialog::reject);

    setLayout(layout);
}

QString SheetSelectionDialog::getSelectedSheet() const
{
    return sheetCombo->currentText();
}

QString SheetSelectionDialog::selectSheet(const QStringList& sheets, QWidget* parent)
{
    if (sheets.isEmpty())
        return QString();

    if (sheets.size() == 1)
        return sheets.first();

    SheetSelectionDialog dialog(sheets, parent);
    if (dialog.exec() == QDialog::Accepted) {
        return dialog.getSelectedSheet();
    }
    return QString();
}
