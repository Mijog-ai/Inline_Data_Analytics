#include <QApplication>
#include <QFile>
#include <QTextStream>
#include <QDateTime>
#include <QLoggingCategory>
#include <QSettings>
#include <QIcon>
#include "mainwindow.h"
#include "language.h"

static QFile logFile;

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
    app.setApplicationVersion("1.0");
    app.setWindowIcon(QIcon(":/appicon.png"));

    // Language: default to German; the user can switch live in Settings.
    Language::apply(Language::current());

    MainWindow mainWindow;
    mainWindow.show();

    int result = app.exec();

    qInfo() << "Application exiting with code" << result;
    logFile.close();

    return result;
}
