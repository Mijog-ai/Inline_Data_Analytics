#include "dataframe.h"

#include <QBuffer>
#include <QDataStream>
#include <algorithm>
#include <cmath>
#include <numeric>

DataFrame::DataFrame()
{
}

DataFrame::DataFrame(const DataFrame &other)
    : m_columnNames(other.m_columnNames)
    , m_columns(other.m_columns)
{
}

DataFrame &DataFrame::operator=(const DataFrame &other)
{
    if (this != &other) {
        m_columnNames = other.m_columnNames;
        m_columns = other.m_columns;
    }
    return *this;
}

void DataFrame::addColumn(const QString &name, const QVector<double> &data)
{
    if (!m_columns.isEmpty() && data.size() != m_columns.first().size()) {
        QVector<double> adjusted = data;
        int targetSize = m_columns.first().size();
        adjusted.resize(targetSize, std::numeric_limits<double>::quiet_NaN());
        m_columnNames.append(name);
        m_columns.append(std::move(adjusted));
    } else {
        m_columnNames.append(name);
        m_columns.append(data);
    }
}

void DataFrame::addColumn(const QString &name, QVector<double> &&data)
{
    if (!m_columns.isEmpty() && data.size() != m_columns.first().size()) {
        int targetSize = m_columns.first().size();
        data.resize(targetSize, std::numeric_limits<double>::quiet_NaN());
    }
    m_columnNames.append(name);
    m_columns.append(std::move(data));
}

QStringList DataFrame::columnNames() const
{
    return m_columnNames;
}

int DataFrame::columnCount() const
{
    return m_columnNames.size();
}

int DataFrame::rowCount() const
{
    if (m_columns.isEmpty())
        return 0;
    return m_columns.first().size();
}

bool DataFrame::hasColumn(const QString &name) const
{
    return m_columnNames.contains(name);
}

int DataFrame::columnIndex(const QString &name) const
{
    return m_columnNames.indexOf(name);
}

static const QVector<double> s_emptyColumn;

const QVector<double>& DataFrame::columnRef(const QString &name) const
{
    int idx = columnIndex(name);
    if (idx < 0)
        return s_emptyColumn;
    return m_columns[idx];
}

QVector<double> DataFrame::column(const QString &name) const
{
    return columnRef(name);
}

double DataFrame::value(int row, const QString &columnName) const
{
    int idx = columnIndex(columnName);
    if (idx < 0 || row < 0 || row >= rowCount())
        return std::numeric_limits<double>::quiet_NaN();
    return m_columns[idx][row];
}

DataFrame DataFrame::filter(const QString &columnName, double minVal, double maxVal) const
{
    int idx = columnIndex(columnName);
    if (idx < 0)
        return DataFrame();

    const QVector<double> &col = m_columns[idx];
    QVector<int> validRows;
    for (int i = 0; i < col.size(); ++i) {
        if (col[i] >= minVal && col[i] <= maxVal)
            validRows.append(i);
    }

    DataFrame result;
    for (int c = 0; c < m_columns.size(); ++c) {
        QVector<double> filtered;
        filtered.reserve(validRows.size());
        for (int row : validRows)
            filtered.append(m_columns[c][row]);
        result.addColumn(m_columnNames[c], filtered);
    }
    return result;
}

DataFrame DataFrame::filterMin(const QString &columnName, double minVal) const
{
    return filter(columnName, minVal, std::numeric_limits<double>::max());
}

DataFrame DataFrame::filterMax(const QString &columnName, double maxVal) const
{
    return filter(columnName, -std::numeric_limits<double>::max(), maxVal);
}

QVector<DataFrame::ColumnStats> DataFrame::describe() const
{
    QVector<ColumnStats> stats;
    for (int c = 0; c < m_columns.size(); ++c) {
        const QVector<double> &col = m_columns[c];
        ColumnStats s;
        s.name = m_columnNames[c];
        s.count = col.size();

        if (s.count == 0) {
            s.min = s.max = s.mean = s.std = std::numeric_limits<double>::quiet_NaN();
            stats.append(s);
            continue;
        }

        // Filter out NaN values for statistics
        QVector<double> valid;
        valid.reserve(s.count);
        for (double v : col) {
            if (!std::isnan(v))
                valid.append(v);
        }

        if (valid.isEmpty()) {
            s.min = s.max = s.mean = s.std = std::numeric_limits<double>::quiet_NaN();
            s.count = 0;
            stats.append(s);
            continue;
        }

        s.count = valid.size();
        s.min = *std::min_element(valid.begin(), valid.end());
        s.max = *std::max_element(valid.begin(), valid.end());
        s.mean = std::accumulate(valid.begin(), valid.end(), 0.0) / valid.size();

        double sumSqDiff = 0.0;
        for (double v : valid) {
            double diff = v - s.mean;
            sumSqDiff += diff * diff;
        }
        s.std = (valid.size() > 1) ? std::sqrt(sumSqDiff / (valid.size() - 1)) : 0.0;

        stats.append(s);
    }
    return stats;
}

bool DataFrame::isEmpty() const
{
    return m_columns.isEmpty() || rowCount() == 0;
}

DataFrame DataFrame::copy() const
{
    return DataFrame(*this);
}

QByteArray DataFrame::serialize() const
{
    QByteArray data;
    QDataStream stream(&data, QIODevice::WriteOnly);
    stream.setVersion(QDataStream::Qt_6_0);

    stream << static_cast<qint32>(m_columnNames.size());
    for (const QString &name : m_columnNames)
        stream << name;

    stream << static_cast<qint32>(rowCount());
    for (const QVector<double> &col : m_columns) {
        for (double val : col)
            stream << val;
    }

    return data;
}

DataFrame DataFrame::deserialize(const QByteArray &data)
{
    DataFrame df;
    QDataStream stream(data);
    stream.setVersion(QDataStream::Qt_6_0);

    qint32 colCount;
    stream >> colCount;

    QStringList names;
    for (int i = 0; i < colCount; ++i) {
        QString name;
        stream >> name;
        names.append(name);
    }

    qint32 rows;
    stream >> rows;

    for (int c = 0; c < colCount; ++c) {
        QVector<double> col(rows);
        for (int r = 0; r < rows; ++r)
            stream >> col[r];
        df.addColumn(names[c], col);
    }

    return df;
}
