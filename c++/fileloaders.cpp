#include "fileloaders.h"

#include <QFile>
#include <QTextStream>
#include <QStringList>
#include <QRegularExpression>
#include <QDebug>
#include <QMessageBox>
#include <QFileInfo>
#include <QStringConverter>

namespace FileLoaders {

// Detect if a line starts with numeric data (number followed by separator)
static bool isDataLine(const QString &line)
{
    if (line.trimmed().isEmpty())
        return false;

    // Check if line starts with an optional minus sign followed by digits
    // Handles both '.' and ',' as decimal separators
    static QRegularExpression re(R"(^\s*-?\d+[\.,]?\d*[\t;, ])");
    return re.match(line).hasMatch();
}

// Make column names unique by appending _1, _2, etc. for duplicates
QStringList makeUniqueNames(const QStringList &names)
{
    QStringList result;
    QMap<QString, int> counts;

    for (const QString &name : names) {
        QString trimmed = name.trimmed();
        if (trimmed.isEmpty())
            trimmed = "Column";

        if (counts.contains(trimmed)) {
            counts[trimmed]++;
            result.append(trimmed + "_" + QString::number(counts[trimmed]));
        } else {
            counts[trimmed] = 0;
            result.append(trimmed);
        }
    }
    return result;
}

// Try to parse a numeric value, handling comma-as-decimal
static double parseNumber(const QString &text)
{
    QString cleaned = text.trimmed();
    cleaned.replace(',', '.');
    bool ok;
    double val = cleaned.toDouble(&ok);
    return ok ? val : std::numeric_limits<double>::quiet_NaN();
}

// Try reading file content with UTF-8 first, then Latin-1
static QString readFileContent(const QString &filePath)
{
    QFile file(filePath);
    if (!file.open(QIODevice::ReadOnly))
        return QString();

    // Try UTF-8 first
    QByteArray rawData = file.readAll();
    file.close();

    // Check for UTF-8 BOM
    if (rawData.startsWith("\xEF\xBB\xBF"))
        rawData = rawData.mid(3);

    // Try UTF-8 decoding
    QString content = QString::fromUtf8(rawData);

    // If UTF-8 produced replacement characters, try Latin-1
    if (content.contains(QChar(0xFFFD))) {
        content = QString::fromLatin1(rawData);
    }

    return content;
}

// Detect the separator used in a CSV-like file
static QChar detectSeparator(const QString &content)
{
    // Take first few lines to analyze
    QStringList lines = content.split('\n');
    int linesToCheck = qMin(10, lines.size());

    int commaCount = 0, semicolonCount = 0, tabCount = 0;
    for (int i = 0; i < linesToCheck; ++i) {
        commaCount += lines[i].count(',');
        semicolonCount += lines[i].count(';');
        tabCount += lines[i].count('\t');
    }

    // Tab is preferred for .asc files
    if (tabCount > 0 && tabCount >= commaCount && tabCount >= semicolonCount)
        return '\t';
    if (semicolonCount > commaCount)
        return ';';
    return ',';
}

DataFrame loadAscFile(const QString &filePath)
{
    qInfo() << "Loading ASC file:" << filePath;

    QFile file(filePath);
    if (!file.open(QIODevice::ReadOnly)) {
        qWarning() << "Failed to open file:" << filePath;
        return DataFrame();
    }

    // Estimate row count for reserve (assume ~50 bytes per line)
    qint64 fileSize = file.size();
    int estimatedRows = static_cast<int>(fileSize / 50);

    QTextStream stream(&file);

    // Read header lines until we find data
    QStringList headerLines;
    QString firstDataLine;
    while (!stream.atEnd()) {
        QString line = stream.readLine();
        if (isDataLine(line)) {
            firstDataLine = line;
            break;
        }
        headerLines.append(line);
    }

    if (firstDataLine.isEmpty()) {
        qWarning() << "No numeric data found in ASC file";
        return DataFrame();
    }

    // Header is the last non-data line
    QStringList headers;
    if (!headerLines.isEmpty())
        headers = headerLines.last().split('\t', Qt::SkipEmptyParts);

    // Parse first data line to determine column count
    QStringList firstFields = firstDataLine.split('\t', Qt::SkipEmptyParts);
    int numCols = firstFields.size();

    QVector<QVector<double>> columns(numCols);
    for (int c = 0; c < numCols; ++c)
        columns[c].reserve(estimatedRows);

    // Parse first line
    for (int c = 0; c < numCols; ++c)
        columns[c].append(parseNumber(firstFields[c]));

    // Stream remaining lines
    while (!stream.atEnd()) {
        QString line = stream.readLine();
        if (line.isEmpty())
            continue;

        QStringList fields = line.split('\t', Qt::SkipEmptyParts);
        for (int c = 0; c < qMin(fields.size(), numCols); ++c)
            columns[c].append(parseNumber(fields[c]));
        for (int c = fields.size(); c < numCols; ++c)
            columns[c].append(std::numeric_limits<double>::quiet_NaN());
    }
    file.close();

    while (headers.size() < numCols)
        headers.append("Column_" + QString::number(headers.size() + 1));
    headers = makeUniqueNames(headers);

    DataFrame df;
    for (int c = 0; c < numCols; ++c)
        df.addColumn(headers[c], std::move(columns[c]));

    qInfo() << "Loaded ASC file:" << df.rowCount() << "rows," << df.columnCount() << "columns";
    return df;
}

DataFrame loadCsvFile(const QString &filePath)
{
    qInfo() << "Loading CSV file:" << filePath;

    QFile file(filePath);
    if (!file.open(QIODevice::ReadOnly)) {
        qWarning() << "Failed to read file:" << filePath;
        return DataFrame();
    }

    qint64 fileSize = file.size();
    int estimatedRows = static_cast<int>(fileSize / 50);

    // Read first few lines to detect separator
    QByteArray peek = file.read(qMin(fileSize, qint64(4096)));
    file.seek(0);
    QString peekStr = QString::fromUtf8(peek);
    QChar sep = detectSeparator(peekStr);
    qInfo() << "Detected separator:" << (sep == '\t' ? "TAB" : QString(sep));

    QTextStream stream(&file);

    // Read header line
    QString headerLine = stream.readLine();
    if (headerLine.isEmpty()) {
        file.close();
        return DataFrame();
    }

    QStringList headers = headerLine.split(sep, Qt::KeepEmptyParts);
    for (auto &h : headers)
        h = h.trimmed().remove('"');
    headers = makeUniqueNames(headers);
    int numCols = headers.size();

    QVector<QVector<double>> columns(numCols);
    for (int c = 0; c < numCols; ++c)
        columns[c].reserve(estimatedRows);

    // Stream data lines
    while (!stream.atEnd()) {
        QString line = stream.readLine();
        if (line.isEmpty())
            continue;

        QStringList fields = line.split(sep, Qt::KeepEmptyParts);
        for (int c = 0; c < qMin(fields.size(), numCols); ++c) {
            QString field = fields[c].trimmed().remove('"');
            columns[c].append(parseNumber(field));
        }
        for (int c = fields.size(); c < numCols; ++c)
            columns[c].append(std::numeric_limits<double>::quiet_NaN());
    }
    file.close();

    DataFrame df;
    for (int c = 0; c < numCols; ++c)
        df.addColumn(headers[c], std::move(columns[c]));

    qInfo() << "Loaded CSV file:" << df.rowCount() << "rows," << df.columnCount() << "columns";
    return df;
}

} // namespace FileLoaders
