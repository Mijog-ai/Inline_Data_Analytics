#ifndef DATAFRAME_H
#define DATAFRAME_H

#include <QString>
#include <QStringList>
#include <QVector>
#include <QByteArray>

class DataFrame {
public:
    DataFrame();
    DataFrame(const DataFrame &other);
    DataFrame &operator=(const DataFrame &other);

    // Column management
    void addColumn(const QString &name, const QVector<double> &data);
    void addColumn(const QString &name, QVector<double> &&data);
    QStringList columnNames() const;
    int columnCount() const;
    int rowCount() const;
    bool hasColumn(const QString &name) const;

    // Data access — const ref to avoid copies on large datasets
    const QVector<double>& columnRef(const QString &name) const;
    QVector<double> column(const QString &name) const;
    double value(int row, const QString &column) const;

    // Filtering
    DataFrame filter(const QString &column, double minVal, double maxVal) const;
    DataFrame filterMin(const QString &column, double minVal) const;
    DataFrame filterMax(const QString &column, double maxVal) const;

    // Statistics
    struct ColumnStats {
        QString name;
        double min;
        double max;
        double mean;
        double std;
        int count;
    };
    QVector<ColumnStats> describe() const;

    // State
    bool isEmpty() const;
    DataFrame copy() const;

    // Serialization (for session save/load)
    QByteArray serialize() const;
    static DataFrame deserialize(const QByteArray &data);

private:
    QStringList m_columnNames;
    QVector<QVector<double>> m_columns;

    int columnIndex(const QString &name) const;
};

#endif // DATAFRAME_H
