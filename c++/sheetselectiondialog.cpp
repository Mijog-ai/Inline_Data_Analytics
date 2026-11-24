#include "sheetselectiondialog.h"

SheetSelectionDialog::SheetSelectionDialog(const QStringList& sheets, QWidget* parent)
    : QDialog(parent)
{
    setupUi(sheets);
}

void SheetSelectionDialog::setupUi(const QStringList& sheets)
{
    setWindowTitle(tr("Select Sheet"));
    setMinimumWidth(300);
    setModal(true);

    auto* layout = new QVBoxLayout(this);

    // Info label
    auto* infoLabel = new QLabel(
        tr("The selected file contains multiple sheets.\n"
           "Select one or more sheets to load (each becomes its own dataset):"), this);
    infoLabel->setStyleSheet("font-size: 10pt; padding: 5px;");
    infoLabel->setWordWrap(true);
    layout->addWidget(infoLabel);

    // Sheet selection list (click to toggle several sheets)
    sheetList = new QListWidget(this);
    sheetList->addItems(sheets);
    sheetList->setSelectionMode(QAbstractItemView::MultiSelection);
    sheetList->setToolTip(tr("Select the sheets to load"));
    if (sheetList->count() > 0)
        sheetList->item(0)->setSelected(true);
    layout->addWidget(sheetList);

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

    connect(buttonBox, &QDialogButtonBox::accepted, this, [this]() {
        if (!getSelectedSheets().isEmpty())
            accept();
    });
    connect(buttonBox, &QDialogButtonBox::rejected, this, &QDialog::reject);

    setLayout(layout);
}

QStringList SheetSelectionDialog::getSelectedSheets() const
{
    QStringList result;
    for (int i = 0; i < sheetList->count(); ++i)
        if (sheetList->item(i)->isSelected())
            result << sheetList->item(i)->text();
    return result;
}

QString SheetSelectionDialog::getSelectedSheet() const
{
    const QStringList s = getSelectedSheets();
    return s.isEmpty() ? QString() : s.first();
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
