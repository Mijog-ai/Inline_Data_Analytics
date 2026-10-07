#ifndef FILELOADERS_H
#define FILELOADERS_H

#include <QString>
#include <QStringList>
#include "dataframe.h"

namespace FileLoaders {

// Loaders return an empty DataFrame when the file holds no usable data.
// The Excel and TDMS loaders throw std::runtime_error for unreadable or
// unsupported files so the caller can show the reason.
DataFrame loadAscFile(const QString &filePath);
DataFrame loadCsvFile(const QString &filePath);
DataFrame loadExcelFile(const QString &filePath, const QString &sheetName = QString());
DataFrame loadTdmsFile(const QString &filePath);
QStringList getExcelSheets(const QString &filePath);

// Make column names unique by appending _1, _2, etc. for duplicates
QStringList makeUniqueNames(const QStringList &names);

} // namespace FileLoaders

#endif // FILELOADERS_H
