#pragma once

#include <QGroupBox>
#include <QTextEdit>
#include <QVBoxLayout>

class CommentBox : public QGroupBox {
    Q_OBJECT

public:
    explicit CommentBox(QWidget* parent = nullptr);

    QString getComments() const;
    void setComments(const QString& text);
    void clear();

private:
    void setupUi();
    QTextEdit* textEdit;
};
