#include "commentbox.h"
#include <QLabel>

CommentBox::CommentBox(QWidget* parent)
    : QGroupBox("Comments", parent)
{
    setupUi();
}

void CommentBox::setupUi()
{
    auto* layout = new QVBoxLayout(this);

    auto* label = new QLabel("Notes / Comments:", this);
    label->setStyleSheet("font-weight: bold;");
    layout->addWidget(label);

    textEdit = new QTextEdit(this);
    textEdit->setPlaceholderText("Enter your comments or notes here...");
    textEdit->setToolTip("Add comments about the data or analysis");
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
