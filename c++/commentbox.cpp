#include "commentbox.h"
#include <QLabel>
#include <QEvent>

CommentBox::CommentBox(QWidget* parent)
    : QGroupBox(parent)
{
    setupUi();
}

void CommentBox::setupUi()
{
    auto* layout = new QVBoxLayout(this);

    notesLabel = new QLabel(this);
    notesLabel->setStyleSheet("font-weight: bold;");
    layout->addWidget(notesLabel);

    textEdit = new QTextEdit(this);
    textEdit->setMaximumHeight(100);
    textEdit->setStyleSheet(R"(
        QTextEdit {
            border: 1px solid #bdc3c7;
            border-radius: 4px;
            padding: 4px;
        }
        QTextEdit:focus {
            border: 1px solid #3498db;
        }
    )");
    layout->addWidget(textEdit);

    setLayout(layout);
    retranslateUi();
}

QString CommentBox::getComments() const
{
    return textEdit->toPlainText();
}

void CommentBox::setComments(const QString& text)
{
    textEdit->setPlainText(text);
}

void CommentBox::clear()
{
    textEdit->clear();
}

void CommentBox::changeEvent(QEvent* event)
{
    if (event->type() == QEvent::LanguageChange)
        retranslateUi();
    QGroupBox::changeEvent(event);
}

void CommentBox::retranslateUi()
{
    setTitle(tr("Comments"));
    notesLabel->setText(tr("Notes / Comments:"));
    textEdit->setPlaceholderText(tr("Enter your comments or notes here..."));
    textEdit->setToolTip(tr("Add comments about the data or analysis"));
}
