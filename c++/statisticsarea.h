#pragma once

#include <QLabel>
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
    // Show statistics for several datasets at once, one group of rows per
    // dataset (each stat row prefixed with the dataset name).
    void updateStatsMulti(const QVector<QPair<QString, DataFrame>>& sets);
    void clearStats();

    // Session save/load support
    QVariantList getStats() const;
    void setStats(const QVariantList& stats);

protected:
    void changeEvent(QEvent* event) override;

private:
    void setupUi();
    void retranslateUi();
    QLabel* titleLabel = nullptr;


    QTableWidget* table;

    // Cache: hash of column data -> stats, to avoid redundant recalculation
    QByteArray lastDataHash;
};
