#include "curvefit.h"

#include <algorithm>
#include <cmath>
#include <numeric>
#include <QDebug>

namespace CurveFit {

// Solve a linear system Ax = b using Gaussian elimination with partial pivoting
static QVector<double> solveLinearSystem(QVector<QVector<double>> A, QVector<double> b)
{
    int n = A.size();
    QVector<double> x(n, 0.0);

    // Forward elimination with partial pivoting
    for (int col = 0; col < n; ++col) {
        // Find pivot
        int maxRow = col;
        double maxVal = std::abs(A[col][col]);
        for (int row = col + 1; row < n; ++row) {
            if (std::abs(A[row][col]) > maxVal) {
                maxVal = std::abs(A[row][col]);
                maxRow = row;
            }
        }

        // Swap rows
        if (maxRow != col) {
            std::swap(A[col], A[maxRow]);
            std::swap(b[col], b[maxRow]);
        }

        if (std::abs(A[col][col]) < 1e-14)
            continue;

        // Eliminate below
        for (int row = col + 1; row < n; ++row) {
            double factor = A[row][col] / A[col][col];
            for (int j = col; j < n; ++j)
                A[row][j] -= factor * A[col][j];
            b[row] -= factor * b[col];
        }
    }

    // Back substitution
    for (int row = n - 1; row >= 0; --row) {
        if (std::abs(A[row][row]) < 1e-14) {
            x[row] = 0.0;
            continue;
        }
        double sum = b[row];
        for (int j = row + 1; j < n; ++j)
            sum -= A[row][j] * x[j];
        x[row] = sum / A[row][row];
    }

    return x;
}

double calculateRSquared(const QVector<double> &yTrue, const QVector<double> &yPred)
{
    if (yTrue.size() != yPred.size() || yTrue.isEmpty())
        return 0.0;

    int n = yTrue.size();
    double yMean = std::accumulate(yTrue.begin(), yTrue.end(), 0.0) / n;

    double ssTot = 0.0;
    double ssRes = 0.0;
    for (int i = 0; i < n; ++i) {
        double diffTot = yTrue[i] - yMean;
        double diffRes = yTrue[i] - yPred[i];
        ssTot += diffTot * diffTot;
        ssRes += diffRes * diffRes;
    }

    if (std::abs(ssTot) < 1e-14)
        return 1.0; // All y values are the same

    return 1.0 - ssRes / ssTot;
}

QString generatePolynomialEquation(const QVector<double> &coeffs, int degree)
{
    // coeffs[0] = coefficient for x^degree, coeffs[degree] = constant term
    // (matching numpy.polyfit convention: highest degree first)
    if (coeffs.isEmpty())
        return "y = 0";

    QString eq = "y = ";
    bool firstTerm = true;

    for (int i = 0; i <= degree; ++i) {
        double c = coeffs[i];
        int power = degree - i;

        if (std::abs(c) < 1e-15)
            continue;

        // Sign handling
        if (!firstTerm) {
            if (c > 0)
                eq += " + ";
            else {
                eq += " - ";
                c = -c;
            }
        } else {
            if (c < 0) {
                eq += "-";
                c = -c;
            }
        }

        // Format coefficient with appropriate precision
        QString coefStr;
        if (std::abs(c) >= 1e4 || (std::abs(c) < 1e-3 && std::abs(c) > 0)) {
            coefStr = QString::number(c, 'e', 4);
        } else {
            coefStr = QString::number(c, 'g', 6);
        }

        if (power == 0) {
            eq += coefStr;
        } else if (power == 1) {
            if (std::abs(c - 1.0) > 1e-10)
                eq += coefStr + "*x";
            else
                eq += "x";
        } else {
            if (std::abs(c - 1.0) > 1e-10)
                eq += coefStr + "*x^" + QString::number(power);
            else
                eq += "x^" + QString::number(power);
        }

        firstTerm = false;
    }

    if (firstTerm)
        eq += "0";

    return eq;
}

FitResult polynomialFit(const QVector<double> &xData, const QVector<double> &yData, int degree)
{
    FitResult result;
    result.rSquared = 0.0;

    if (xData.size() != yData.size() || xData.size() < degree + 1) {
        qWarning() << "polynomialFit: insufficient data points or size mismatch";
        return result;
    }

    int n = xData.size();
    int m = degree + 1; // Number of coefficients

    // Build the Vandermonde matrix X where X[i][j] = x_i^(degree - j)
    // This follows numpy convention: coefficients are highest degree first
    // Normal equations: (X^T X) c = X^T y

    // Compute X^T X (m x m matrix)
    QVector<QVector<double>> XtX(m, QVector<double>(m, 0.0));
    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < m; ++j) {
            int power = (degree - i) + (degree - j);
            double sum = 0.0;
            for (int k = 0; k < n; ++k)
                sum += std::pow(xData[k], power);
            XtX[i][j] = sum;
        }
    }

    // Compute X^T y (m vector)
    QVector<double> Xty(m, 0.0);
    for (int i = 0; i < m; ++i) {
        int power = degree - i;
        for (int k = 0; k < n; ++k)
            Xty[i] += std::pow(xData[k], power) * yData[k];
    }

    // Solve normal equations
    QVector<double> coeffs = solveLinearSystem(XtX, Xty);
    result.coefficients = coeffs;

    // Compute predicted values and R-squared
    QVector<double> yPred(n);
    for (int i = 0; i < n; ++i) {
        double val = 0.0;
        for (int j = 0; j < m; ++j)
            val += coeffs[j] * std::pow(xData[i], degree - j);
        yPred[i] = val;
    }

    result.rSquared = calculateRSquared(yData, yPred);
    result.equation = generatePolynomialEquation(coeffs, degree);

    // Create the fit function (capture coefficients by value)
    QVector<double> capturedCoeffs = coeffs;
    int capturedDegree = degree;
    result.fitFunction = [capturedCoeffs, capturedDegree](double x) -> double {
        double val = 0.0;
        int m = capturedCoeffs.size();
        for (int j = 0; j < m; ++j)
            val += capturedCoeffs[j] * std::pow(x, capturedDegree - j);
        return val;
    };

    qInfo() << "Polynomial fit (degree" << degree << "): R^2 =" << result.rSquared;
    return result;
}

FitResult exponentialFit(const QVector<double> &xData, const QVector<double> &yData)
{
    FitResult result;
    result.rSquared = 0.0;

    if (xData.size() != yData.size() || xData.size() < 2) {
        qWarning() << "exponentialFit: insufficient data points or size mismatch";
        return result;
    }

    int n = xData.size();

    // Exponential model: y = a * exp(b * x)
    // Log-linearization: ln(y) = ln(a) + b * x
    // This requires all y values to be positive

    // Filter out non-positive y values
    QVector<double> xValid, yValid, lnY;
    for (int i = 0; i < n; ++i) {
        if (yData[i] > 0.0) {
            xValid.append(xData[i]);
            yValid.append(yData[i]);
            lnY.append(std::log(yData[i]));
        }
    }

    if (xValid.size() < 2) {
        qWarning() << "exponentialFit: insufficient positive y values for log-linearization";
        return result;
    }

    int nv = xValid.size();

    // Linear regression on (x, ln(y)):  ln(y) = c0 + c1 * x
    // where c0 = ln(a), c1 = b
    double sumX = 0.0, sumY = 0.0, sumXX = 0.0, sumXY = 0.0;
    for (int i = 0; i < nv; ++i) {
        sumX += xValid[i];
        sumY += lnY[i];
        sumXX += xValid[i] * xValid[i];
        sumXY += xValid[i] * lnY[i];
    }

    double denom = nv * sumXX - sumX * sumX;
    if (std::abs(denom) < 1e-14) {
        qWarning() << "exponentialFit: degenerate data (all x values are the same)";
        return result;
    }

    double c1 = (nv * sumXY - sumX * sumY) / denom;  // b
    double c0 = (sumY - c1 * sumX) / nv;              // ln(a)

    double a = std::exp(c0);
    double b = c1;

    result.coefficients = {a, b};

    // Compute R-squared on original scale
    QVector<double> yPred(n);
    for (int i = 0; i < n; ++i)
        yPred[i] = a * std::exp(b * xData[i]);

    result.rSquared = calculateRSquared(yData, yPred);

    // Generate equation string
    QString aStr = (std::abs(a) >= 1e4 || (std::abs(a) < 1e-3 && std::abs(a) > 0))
                       ? QString::number(a, 'e', 4)
                       : QString::number(a, 'g', 6);
    QString bStr = (std::abs(b) >= 1e4 || (std::abs(b) < 1e-3 && std::abs(b) > 0))
                       ? QString::number(b, 'e', 4)
                       : QString::number(b, 'g', 6);
    result.equation = "y = " + aStr + " * exp(" + bStr + " * x)";

    // Create fit function
    result.fitFunction = [a, b](double x) -> double {
        return a * std::exp(b * x);
    };

    qInfo() << "Exponential fit: a =" << a << ", b =" << b << ", R^2 =" << result.rSquared;
    return result;
}

} // namespace CurveFit
