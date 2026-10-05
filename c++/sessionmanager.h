#pragma once

#include <QObject>
#include <QString>

class MainWindow;

class SessionManager : public QObject {
    Q_OBJECT

public:
    explicit SessionManager(MainWindow* mainWindow, QObject* parent = nullptr);

    void saveSession();
    void loadSession();
    void newSession();

private:
    MainWindow* mainWindow;

    static constexpr quint32 SESSION_MAGIC = 0x494E4C47; // "INLG"
    static constexpr quint32 SESSION_VERSION = 1;
};
