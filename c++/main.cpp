#include <QApplication>
#include <QFile>
#include <QTextStream>
#include <QDateTime>
#include <QLoggingCategory>
#include <QSettings>
#include <QIcon>
#include <QEvent>
#include <QObject>
#include <QWidget>
#include "mainwindow.h"
#include "language.h"

#ifndef APP_VERSION
#define APP_VERSION "0.0.0"
#endif

static QFile logFile;

// Keeps a "  —  v<version>" suffix on the main window title even after it is re-translated on a live
// language switch. Lives here so the version is shown without touching mainwindow.cpp.
class TitleVersionKeeper : public QObject
{
public:
    explicit TitleVersionKeeper(QWidget *window)
        : QObject(window), m_window(window)
    {
        m_marker = QStringLiteral("  —  v");          // "  —  v"
        apply();
    }

    void apply()
    {
        const QString suffix = m_marker + QApplication::applicationVersion();
        QString title = m_window->windowTitle();
        if (title.endsWith(suffix))
            return;
        const int idx = title.indexOf(m_marker);
        if (idx >= 0)
            title = title.left(idx);
        m_window->setWindowTitle(title + suffix);
    }

protected:
    bool eventFilter(QObject *obj, QEvent *event) override
    {
        if (obj == m_window && event->type() == QEvent::WindowTitleChange)
            apply();   // guarded by the endsWith() check in apply(), so it does not recurse
        return QObject::eventFilter(obj, event);
    }

private:
    QWidget *m_window;
    QString m_marker;
};

void messageHandler(QtMsgType type, const QMessageLogContext &context, const QString &msg)
{
    if (!logFile.isOpen())
        return;

    QTextStream out(&logFile);
    QString timestamp = QDateTime::currentDateTime().toString("yyyy-MM-dd hh:mm:ss.zzz");

    QString level;
    switch (type) {
    case QtDebugMsg:    level = "DEBUG"; break;
    case QtInfoMsg:     level = "INFO"; break;
    case QtWarningMsg:  level = "WARNING"; break;
    case QtCriticalMsg: level = "CRITICAL"; break;
    case QtFatalMsg:    level = "FATAL"; break;
    }

    out << timestamp << " [" << level << "] "
        << msg;
    if (context.file)
        out << " (" << context.file << ":" << context.line << ")";
    out << "\n";
    out.flush();
}

int main(int argc, char *argv[])
{
    logFile.setFileName("app.log");
    if (!logFile.open(QIODevice::WriteOnly | QIODevice::Append | QIODevice::Text)) {
        qWarning("Could not open log file");
    }
    qInstallMessageHandler(messageHandler);

    qInfo() << "Application starting";

    QApplication app(argc, argv);
    app.setOrganizationName("Inline");
    app.setApplicationName("Inline Data Analytics");
    app.setApplicationVersion(QStringLiteral(APP_VERSION));
    app.setWindowIcon(QIcon(":/appicon.png"));

    // Language: default to German; the user can switch live in Settings.
    Language::apply(Language::current());

    MainWindow mainWindow;
    // Show the version in the title bar (and keep it across language switches).
    TitleVersionKeeper titleKeeper(&mainWindow);
    mainWindow.installEventFilter(&titleKeeper);
    mainWindow.show();

    int result = app.exec();

    qInfo() << "Application exiting with code" << result;
    logFile.close();

    return result;
}
