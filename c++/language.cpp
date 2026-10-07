#include "language.h"

#include <QCoreApplication>
#include <QLibraryInfo>
#include <QPointer>
#include <QSettings>
#include <QTranslator>

namespace Language {

namespace {
QPointer<QTranslator> qtTranslator;    // Qt's own strings (standard dialog buttons, etc.)
QPointer<QTranslator> appTranslator;   // this application's strings

void remove(QPointer<QTranslator>& translator)
{
    if (translator) {
        QCoreApplication::removeTranslator(translator);
        delete translator;
    }
}
} // namespace

QString current()
{
    return QSettings().value("language", "de").toString();
}

void apply(const QString& code)
{
    QSettings().setValue("language", code);

    remove(qtTranslator);
    remove(appTranslator);

    // English is the source language, so it needs no translation file.
    if (code == "en")
        return;

    auto* qt = new QTranslator(QCoreApplication::instance());
    // Qt base translations: try the installed Qt first, then the embedded copy.
    if (qt->load("qtbase_" + code, QLibraryInfo::path(QLibraryInfo::TranslationsPath))
        || qt->load(":/i18n/qtbase_" + code + ".qm")) {
        QCoreApplication::installTranslator(qt);
        qtTranslator = qt;
    } else {
        delete qt;
    }

    auto* app = new QTranslator(QCoreApplication::instance());
    if (app->load(":/i18n/app_" + code + ".qm")) {
        QCoreApplication::installTranslator(app);
        appTranslator = app;
    } else {
        delete app;
    }
}

} // namespace Language
