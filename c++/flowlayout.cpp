#include "flowlayout.h"

#include <QWidget>

FlowLayout::FlowLayout(QWidget* parent, int hSpacing, int vSpacing)
    : QLayout(parent)
    , hSpace(hSpacing)
    , vSpace(vSpacing)
{
    setContentsMargins(0, 0, 0, 0);
}

FlowLayout::~FlowLayout()
{
    while (QLayoutItem* item = takeAt(0))
        delete item;
}

void FlowLayout::addItem(QLayoutItem* item)
{
    items.append(item);
}

int FlowLayout::count() const
{
    return items.size();
}

QLayoutItem* FlowLayout::itemAt(int index) const
{
    return items.value(index);
}

QLayoutItem* FlowLayout::takeAt(int index)
{
    return (index >= 0 && index < items.size()) ? items.takeAt(index) : nullptr;
}

int FlowLayout::heightForWidth(int width) const
{
    return doLayout(QRect(0, 0, width, 0), true);
}

QSize FlowLayout::minimumSize() const
{
    QSize size;
    for (const QLayoutItem* item : items)
        size = size.expandedTo(item->minimumSize());
    const QMargins m = contentsMargins();
    return size + QSize(m.left() + m.right(), m.top() + m.bottom());
}

QSize FlowLayout::sizeHint() const
{
    // Preferred: everything on one line.
    int width = 0;
    int height = 0;
    for (const QLayoutItem* item : items) {
        if (item->isEmpty())
            continue;
        const QSize hint = item->sizeHint();
        width += hint.width() + (width > 0 ? hSpace : 0);
        height = qMax(height, hint.height());
    }
    const QMargins m = contentsMargins();
    return QSize(width + m.left() + m.right(), height + m.top() + m.bottom());
}

void FlowLayout::setGeometry(const QRect& rect)
{
    QLayout::setGeometry(rect);
    doLayout(rect, false);
}

int FlowLayout::doLayout(const QRect& rect, bool testOnly) const
{
    const QRect area = rect.marginsRemoved(contentsMargins());
    const int maxWidth = qMax(1, area.width());

    // Split the items into lines, then place each line vertically centred.
    QList<QList<QLayoutItem*>> lines(1);
    int lineWidth = 0;
    for (QLayoutItem* item : items) {
        if (item->isEmpty())
            continue;
        const int w = qMin(item->sizeHint().width(), maxWidth);
        if (!lines.last().isEmpty() && lineWidth + hSpace + w > maxWidth) {
            lines.append(QList<QLayoutItem*>());
            lineWidth = 0;
        }
        lineWidth += (lines.last().isEmpty() ? 0 : hSpace) + w;
        lines.last().append(item);
    }

    int y = area.y();
    for (const QList<QLayoutItem*>& line : lines) {
        if (line.isEmpty())
            continue;
        int lineHeight = 0;
        for (const QLayoutItem* item : line)
            lineHeight = qMax(lineHeight, item->sizeHint().height());
        if (!testOnly) {
            int x = area.x();
            for (QLayoutItem* item : line) {
                const QSize hint = item->sizeHint();
                const int w = qMin(hint.width(), maxWidth);
                item->setGeometry(QRect(x, y + (lineHeight - hint.height()) / 2, w, hint.height()));
                x += w + hSpace;
            }
        }
        y += lineHeight + vSpace;
    }
    if (y > area.y())
        y -= vSpace;

    const QMargins m = contentsMargins();
    return y - rect.y() + m.bottom();
}
