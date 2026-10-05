#ifndef SMOOTHING_H
#define SMOOTHING_H

#include <QString>
#include <QVector>

namespace Smoothing {

QVector<double> movingAverage(const QVector<double> &data, int windowSize);
QVector<double> savitzkyGolay(const QVector<double> &data, int windowSize, int polyOrder);
QVector<double> gaussianFilter(const QVector<double> &data, double sigma);
QVector<double> exponentialMovingAverage(const QVector<double> &data, double alpha);
QVector<double> medianFilter(const QVector<double> &data, int windowSize);
QVector<double> lowessSmoothing(const QVector<double> &data, double fraction);

QVector<double> applySmoothing(const QVector<double> &data, const QString &method,
                                int windowLength = 21, int polyOrder = 3, double sigma = 2.0,
                                double alpha = 0.3, double lowessFrac = 0.1);

} // namespace Smoothing

#endif // SMOOTHING_H
