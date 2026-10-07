#pragma once

#include <QGroupBox>
#include <QTextEdit>
#include <QVBoxLayout>
#include <QLabel>

class CommentBox : public QGroupBox {
    Q_OBJECT

public:
    explicit CommentBox(QWidget* parent = nullptr);

    QString getComments() const;
    void setComments(const QString& text);
    void clear();

protected:
    void changeEvent(QEvent* event) override;

private:
    void setupUi();
    void retranslateUi();
    QTextEdit* textEdit;
    QLabel* notesLabel = nullptr;
};
