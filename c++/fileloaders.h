#ifndef FILELOADERS_H
#define FILELOADERS_H

#include <QString>
#include <QStringList>
#include <QVariantList>
#include <QVector>
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

// One worksheet of an exported workbook. Holds either a DataFrame (written as a
// bold header row of column names followed by numeric rows) or, when `data` is
// empty, free-form `rows` whose cells are numbers (int/double/bool) or text.
// The first entry of `rows` is written as the bold header row.
struct ExcelSheet {
    QString name;
    DataFrame data;
    QList<QVariantList> rows;
};

// Write sheets to an .xlsx workbook. Throws std::runtime_error on failure
// (e.g. the file cannot be written or the data exceeds Excel's row limit).
void saveExcelFile(const QString &filePath, const QVector<ExcelSheet> &sheets);

// Make column names unique by appending _1, _2, etc. for duplicates
QStringList makeUniqueNames(const QStringList &names);

} // namespace FileLoaders

#endif // FILELOADERS_H
