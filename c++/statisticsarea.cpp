#include "statisticsarea.h"

#include <QHeaderView>
#include <QLabel>
#include <QEvent>
#include <QCryptographicHash>
#include <QDataStream>
#include <QBuffer>

StatisticsArea::StatisticsArea(QWidget* parent)
    : QWidget(parent)
{
    setupUi();
}

void StatisticsArea::setupUi()
{
    auto* layout = new QVBoxLayout(this);
    layout->setContentsMargins(0, 0, 0, 0);

    titleLabel = new QLabel(this);
    titleLabel->setStyleSheet("font-weight: bold; font-size: 11pt; padding: 4px;");
    layout->addWidget(titleLabel);

    table = new QTableWidget(this);
    table->setColumnCount(5);
    table->horizontalHeader()->setStretchLastSection(true);
    table->horizontalHeader()->setSectionResizeMode(QHeaderView::Stretch);
    table->setEditTriggers(QAbstractItemView::NoEditTriggers);
    table->setAlternatingRowColors(true);
    table->setSelectionMode(QAbstractItemView::NoSelection);
    table->setStyleSheet(R"(
        QTableWidget {
            border: 1px solid #bdc3c7;
            border-radius: 4px;
            gridline-color: #ecf0f1;
        }
        QHeaderView::section {
            background-color: #3498db;
            color: white;
            padding: 4px;
            border: none;
            font-weight: bold;
        }
        QTableWidget::item {
            padding: 3px;
        }
    )");

    layout->addWidget(table);
    setLayout(layout);
    retranslateUi();
}

void StatisticsArea::updateStats(const DataFrame& df)
{
    if (df.isEmpty()) {
        clearStats();
        return;
    }

    // Compute a hash of the data to check if we need to recalculate
    QByteArray hashInput;
    QBuffer buffer(&hashInput);
    buffer.open(QIODevice::WriteOnly);
    QDataStream stream(&buffer);
    QStringList cols = df.columnNames();
    stream << cols;
    stream << df.rowCount();
    for (const auto& col : cols) {
        QVector<double> data = df.column(col);
        // Hash first, last, and count for efficiency
        if (!data.isEmpty()) {
            stream << data.first() << data.last() << data.size();
        }
    }
    buffer.close();

    QByteArray dataHash = QCryptographicHash::hash(hashInput, QCryptographicHash::Md5);
    if (dataHash == lastDataHash)
        return; // Stats are already up to date

    lastDataHash = dataHash;

    // Get statistics
    QVector<DataFrame::ColumnStats> stats = df.describe();

    table->setRowCount(stats.size());

    for (int i = 0; i < stats.size(); ++i) {
        const auto& s = stats[i];

        auto* nameItem = new QTableWidgetItem(s.name);
        nameItem->setToolTip(tr("Count: %1").arg(s.count));
        table->setItem(i, 0, nameItem);

        auto* maxItem = new QTableWidgetItem(QString::number(s.max, 'f', 4));
        table->setItem(i, 1, maxItem);

        auto* meanItem = new QTableWidgetItem(QString::number(s.mean, 'f', 4));
        table->setItem(i, 2, meanItem);

        auto* minItem = new QTableWidgetItem(QString::number(s.min, 'f', 4));
        table->setItem(i, 3, minItem);

        auto* stdItem = new QTableWidgetItem(QString::number(s.std, 'f', 4));
        table->setItem(i, 4, stdItem);
    }
}

void StatisticsArea::updateStatsMulti(const QVector<QPair<QString, DataFrame>>& sets)
{
    // Collect non-empty datasets.
    QVector<QPair<QString, DataFrame>> active;
    for (const auto& s : sets)
        if (!s.second.isEmpty())
            active.append(s);

    if (active.isEmpty()) {
        clearStats();
        return;
    }
    if (active.size() == 1) {
        updateStats(active.first().second);
        return;
    }

    // Caching does not apply cleanly across multiple frames; always rebuild.
    lastDataHash.clear();

    int totalRows = 0;
    for (const auto& s : active)
        totalRows += s.second.describe().size();
    table->setRowCount(totalRows);

    int row = 0;
    for (const auto& s : active) {
        const QString& dsName = s.first;
        const auto stats = s.second.describe();
        for (const auto& st : stats) {
            auto* nameItem = new QTableWidgetItem(dsName + " · " + st.name);
            nameItem->setToolTip(tr("Count: %1").arg(st.count));
            table->setItem(row, 0, nameItem);
            table->setItem(row, 1, new QTableWidgetItem(QString::number(st.max, 'f', 4)));
            table->setItem(row, 2, new QTableWidgetItem(QString::number(st.mean, 'f', 4)));
            table->setItem(row, 3, new QTableWidgetItem(QString::number(st.min, 'f', 4)));
            table->setItem(row, 4, new QTableWidgetItem(QString::number(st.std, 'f', 4)));
            ++row;
        }
    }
}

void StatisticsArea::clearStats()
{
    table->setRowCount(0);
    lastDataHash.clear();
}

QVariantList StatisticsArea::getStats() const
{
    QVariantList result;
    for (int row = 0; row < table->rowCount(); ++row) {
        QVariantMap rowData;
        rowData["name"] = table->item(row, 0) ? table->item(row, 0)->text() : QString();
        rowData["max"] = table->item(row, 1) ? table->item(row, 1)->text() : QString();
        rowData["mean"] = table->item(row, 2) ? table->item(row, 2)->text() : QString();
        rowData["min"] = table->item(row, 3) ? table->item(row, 3)->text() : QString();
        rowData["std"] = table->item(row, 4) ? table->item(row, 4)->text() : QString();
        result.append(rowData);
    }
    return result;
}

void StatisticsArea::setStats(const QVariantList& stats)
{
    table->setRowCount(stats.size());
    for (int i = 0; i < stats.size(); ++i) {
        QVariantMap rowData = stats[i].toMap();
        table->setItem(i, 0, new QTableWidgetItem(rowData["name"].toString()));
        table->setItem(i, 1, new QTableWidgetItem(rowData["max"].toString()));
        table->setItem(i, 2, new QTableWidgetItem(rowData["mean"].toString()));
        table->setItem(i, 3, new QTableWidgetItem(rowData["min"].toString()));
        table->setItem(i, 4, new QTableWidgetItem(rowData["std"].toString()));
    }
}

void StatisticsArea::changeEvent(QEvent* event)
{
    if (event->type() == QEvent::LanguageChange)
        retranslateUi();
    QWidget::changeEvent(event);
}

void StatisticsArea::retranslateUi()
{
    titleLabel->setText(tr("Statistics"));
    table->setHorizontalHeaderLabels({tr("Statistic"), tr("Max"), tr("Mean"), tr("Min"), tr("Std")});
}
