#include <QApplication>
#include <QFile>
#include <QTextStream>
#include <QDateTime>
#include <QLoggingCategory>
#include "mainwindow.h"

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
    app.setApplicationName("Inline Data Analytics");
    app.setApplicationVersion("1.0");

    MainWindow mainWindow;
    mainWindow.show();

    int result = app.exec();

    qInfo() << "Application exiting with code" << result;
    logFile.close();

    return result;
}
