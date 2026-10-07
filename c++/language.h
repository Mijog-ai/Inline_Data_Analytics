#pragma once

#include <QString>

namespace Language {

// Language code stored in the settings ("de" by default, or "en").
QString current();

// Installs the translators for `code` ("de", "en", ...) and stores it in the
// settings. Takes effect immediately: Qt sends a LanguageChange event to every
// widget, which re-applies its texts, so no restart (and no data loss) is needed.
void apply(const QString& code);

} // namespace Language
