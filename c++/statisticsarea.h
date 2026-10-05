#pragma once

#include <QWidget>
#include <QTableWidget>
#include <QVBoxLayout>
#include <QHash>
#include <QByteArray>

#include "dataframe.h"

class StatisticsArea : public QWidget {
    Q_OBJECT

public:
    explicit StatisticsArea(QWidget* parent = nullptr);

    void updateStats(const DataFrame& df);
    void clearStats();

    // Session save/load support
    QVariantList getStats() const;
    void setStats(const QVariantList& stats);

private:
    void setupUi();

    QTableWidget* table;

    // Cache: hash of column data -> stats, to avoid redundant recalculation
    QByteArray lastDataHash;
};
