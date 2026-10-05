#ifndef CURVEFIT_H
#define CURVEFIT_H

#include <QString>
#include <QVector>
#include <functional>

namespace CurveFit {

struct FitResult {
    QVector<double> coefficients;
    QString equation;
    double rSquared;
    std::function<double(double)> fitFunction;
};

FitResult polynomialFit(const QVector<double> &xData, const QVector<double> &yData, int degree);
FitResult exponentialFit(const QVector<double> &xData, const QVector<double> &yData);
double calculateRSquared(const QVector<double> &yTrue, const QVector<double> &yPred);
QString generatePolynomialEquation(const QVector<double> &coeffs, int degree);

} // namespace CurveFit

#endif // CURVEFIT_H
