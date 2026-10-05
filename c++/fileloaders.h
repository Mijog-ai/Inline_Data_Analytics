#ifndef FILELOADERS_H
#define FILELOADERS_H

#include <QString>
#include <QStringList>
#include "dataframe.h"

namespace FileLoaders {

DataFrame loadAscFile(const QString &filePath);
DataFrame loadCsvFile(const QString &filePath);
DataFrame loadExcelFile(const QString &filePath, const QString &sheetName = QString());
DataFrame loadTdmsFile(const QString &filePath);
QStringList getExcelSheets(const QString &filePath);

} // namespace FileLoaders

#endif // FILELOADERS_H
