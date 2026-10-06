#include <QApplication>
#include <QFile>
#include <QTextStream>
#include <QDateTime>
#include <QLoggingCategory>
#include <QSettings>
#include <QTranslator>
#include <QLibraryInfo>
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
    app.setOrganizationName("Inline");
    app.setApplicationName("Inline Data Analytics");
    app.setApplicationVersion("1.0");

    // Language: default to German; the user can switch to English in Settings.
    // English is the source language, so it needs no translation file.
    QSettings settings;
    const QString lang = settings.value("language", "de").toString();

    QTranslator qtTranslator;   // Qt's own strings (standard dialog buttons, etc.)
    QTranslator appTranslator;  // this application's strings
    if (lang != "en") {
        // Qt base translations: try the installed Qt first, then the embedded copy.
        if (qtTranslator.load("qtbase_" + lang,
                QLibraryInfo::path(QLibraryInfo::TranslationsPath))
            || qtTranslator.load(":/i18n/qtbase_" + lang + ".qm")) {
            app.installTranslator(&qtTranslator);
        }
        if (appTranslator.load(":/i18n/app_" + lang + ".qm"))
            app.installTranslator(&appTranslator);
    }

    MainWindow mainWindow;
    mainWindow.show();

    int result = app.exec();

    qInfo() << "Application exiting with code" << result;
    logFile.close();

    return result;
}
