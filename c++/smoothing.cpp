#include "smoothing.h"

#include <algorithm>
#include <cmath>
#include <numeric>
#include <QDebug>

namespace Smoothing {

QVector<double> movingAverage(const QVector<double> &data, int windowSize)
{
    if (data.isEmpty() || windowSize <= 0)
        return data;

    // Ensure odd window size
    if (windowSize % 2 == 0)
        windowSize++;

    int n = data.size();
    QVector<double> result(n);
    int halfWin = windowSize / 2;

    for (int i = 0; i < n; ++i) {
        int start = qMax(0, i - halfWin);
        int end = qMin(n - 1, i + halfWin);
        double sum = 0.0;
        int count = 0;
        for (int j = start; j <= end; ++j) {
            if (!std::isnan(data[j])) {
                sum += data[j];
                count++;
            }
        }
        result[i] = (count > 0) ? sum / count : std::numeric_limits<double>::quiet_NaN();
    }

    return result;
}

// Solve a linear system Ax = b using Gaussian elimination with partial pivoting
// A is n x n, b is n x 1. Returns solution x.
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
            continue; // Singular or near-singular

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

QVector<double> savitzkyGolay(const QVector<double> &data, int windowSize, int polyOrder)
{
    if (data.isEmpty() || windowSize <= 0)
        return data;

    // Ensure odd window size
    if (windowSize % 2 == 0)
        windowSize++;

    // polyOrder must be less than windowSize
    if (polyOrder >= windowSize)
        polyOrder = windowSize - 1;

    int n = data.size();
    if (windowSize > n)
        windowSize = (n % 2 == 0) ? n - 1 : n;
    if (windowSize < 3)
        return data;

    int halfWin = windowSize / 2;

    // Compute Savitzky-Golay convolution coefficients
    // Build the Vandermonde-like matrix J for positions -halfWin .. +halfWin
    // coefficients = (J^T J)^{-1} J^T  (first row gives smoothing coefficients)
    int m = polyOrder + 1;
    int w = windowSize;

    // Build J: w rows x m cols, J[i][j] = i_pos^j where i_pos = i - halfWin
    QVector<QVector<double>> J(w, QVector<double>(m));
    for (int i = 0; i < w; ++i) {
        double pos = static_cast<double>(i - halfWin);
        double p = 1.0;
        for (int j = 0; j < m; ++j) {
            J[i][j] = p;
            p *= pos;
        }
    }

    // Compute J^T * J  (m x m)
    QVector<QVector<double>> JtJ(m, QVector<double>(m, 0.0));
    for (int i = 0; i < m; ++i)
        for (int j = 0; j < m; ++j)
            for (int k = 0; k < w; ++k)
                JtJ[i][j] += J[k][i] * J[k][j];

    // Compute J^T * e_k for k = 0..w-1, but we only need the smoothing coefficients
    // which correspond to the 0th derivative: first row of (J^T J)^{-1} J^T
    // Equivalently, solve (J^T J) * c = J^T * e_center for each column, but
    // it's easier to solve for the full coefficient matrix.

    // For smoothing (0th derivative), we want coefficients c such that
    // c[k] = row 0 of (J^T J)^{-1} * column k of J^T
    // = sum_j  inv(JtJ)[0][j] * J[k][j]

    // First, compute row 0 of inv(JtJ) by solving JtJ * x = e_0
    QVector<double> e0(m, 0.0);
    e0[0] = 1.0;
    QVector<double> invRow0 = solveLinearSystem(JtJ, e0);

    // Compute smoothing coefficients
    QVector<double> coeffs(w, 0.0);
    for (int k = 0; k < w; ++k) {
        for (int j = 0; j < m; ++j)
            coeffs[k] += invRow0[j] * J[k][j];
    }

    // Apply convolution
    QVector<double> result(n);
    for (int i = 0; i < n; ++i) {
        if (i < halfWin || i >= n - halfWin) {
            // For edges, use the original value
            result[i] = data[i];
        } else {
            double val = 0.0;
            for (int k = 0; k < w; ++k)
                val += coeffs[k] * data[i - halfWin + k];
            result[i] = val;
        }
    }

    return result;
}

QVector<double> gaussianFilter(const QVector<double> &data, double sigma)
{
    if (data.isEmpty() || sigma <= 0.0)
        return data;

    int n = data.size();

    // Kernel radius: 3*sigma is a good cutoff
    int radius = static_cast<int>(std::ceil(3.0 * sigma));
    if (radius < 1)
        radius = 1;
    int kernelSize = 2 * radius + 1;

    // Generate Gaussian kernel
    QVector<double> kernel(kernelSize);
    double sum = 0.0;
    for (int i = 0; i < kernelSize; ++i) {
        double x = static_cast<double>(i - radius);
        kernel[i] = std::exp(-0.5 * x * x / (sigma * sigma));
        sum += kernel[i];
    }
    // Normalize
    for (int i = 0; i < kernelSize; ++i)
        kernel[i] /= sum;

    // Convolve
    QVector<double> result(n);
    for (int i = 0; i < n; ++i) {
        double val = 0.0;
        double wSum = 0.0;
        for (int k = 0; k < kernelSize; ++k) {
            int idx = i - radius + k;
            if (idx >= 0 && idx < n && !std::isnan(data[idx])) {
                val += kernel[k] * data[idx];
                wSum += kernel[k];
            }
        }
        result[i] = (wSum > 0.0) ? val / wSum : data[i];
    }

    return result;
}

QVector<double> exponentialMovingAverage(const QVector<double> &data, double alpha)
{
    if (data.isEmpty())
        return data;

    alpha = qBound(0.0, alpha, 1.0);

    int n = data.size();
    QVector<double> result(n);
    result[0] = data[0];

    for (int i = 1; i < n; ++i) {
        if (std::isnan(data[i])) {
            result[i] = result[i - 1];
        } else if (std::isnan(result[i - 1])) {
            result[i] = data[i];
        } else {
            result[i] = alpha * data[i] + (1.0 - alpha) * result[i - 1];
        }
    }

    return result;
}

QVector<double> medianFilter(const QVector<double> &data, int windowSize)
{
    if (data.isEmpty() || windowSize <= 0)
        return data;

    // Ensure odd window size
    if (windowSize % 2 == 0)
        windowSize++;

    int n = data.size();
    int halfWin = windowSize / 2;
    QVector<double> result(n);

    for (int i = 0; i < n; ++i) {
        int start = qMax(0, i - halfWin);
        int end = qMin(n - 1, i + halfWin);

        QVector<double> window;
        for (int j = start; j <= end; ++j) {
            if (!std::isnan(data[j]))
                window.append(data[j]);
        }

        if (window.isEmpty()) {
            result[i] = std::numeric_limits<double>::quiet_NaN();
        } else {
            int mid = window.size() / 2;
            std::nth_element(window.begin(), window.begin() + mid, window.end());
            result[i] = window[mid];
        }
    }

    return result;
}

QVector<double> lowessSmoothing(const QVector<double> &data, double fraction)
{
    if (data.isEmpty())
        return data;

    fraction = qBound(0.01, fraction, 1.0);

    int n = data.size();
    int windowSize = qMax(3, static_cast<int>(fraction * n));
    if (windowSize % 2 == 0)
        windowSize++;
    int halfWin = windowSize / 2;

    QVector<double> result(n);

    // Tricube weight function
    auto tricube = [](double u) -> double {
        if (u >= 1.0) return 0.0;
        double t = 1.0 - u * u * u;
        return t * t * t;
    };

    for (int i = 0; i < n; ++i) {
        int start = qMax(0, i - halfWin);
        int end = qMin(n - 1, i + halfWin);

        // Find the maximum distance for normalization
        double maxDist = 0.0;
        for (int j = start; j <= end; ++j) {
            double d = std::abs(static_cast<double>(j - i));
            if (d > maxDist)
                maxDist = d;
        }
        if (maxDist < 1.0)
            maxDist = 1.0;

        // Weighted least squares (linear fit: y = a + b*x)
        double sumW = 0.0, sumWx = 0.0, sumWy = 0.0, sumWxx = 0.0, sumWxy = 0.0;
        for (int j = start; j <= end; ++j) {
            if (std::isnan(data[j]))
                continue;
            double dist = std::abs(static_cast<double>(j - i)) / maxDist;
            double w = tricube(dist);
            double x = static_cast<double>(j);
            double y = data[j];
            sumW += w;
            sumWx += w * x;
            sumWy += w * y;
            sumWxx += w * x * x;
            sumWxy += w * x * y;
        }

        if (sumW < 1e-14) {
            result[i] = data[i];
            continue;
        }

        double denom = sumW * sumWxx - sumWx * sumWx;
        if (std::abs(denom) < 1e-14) {
            result[i] = sumWy / sumW; // Fall back to weighted average
        } else {
            double a = (sumWxx * sumWy - sumWx * sumWxy) / denom;
            double b = (sumW * sumWxy - sumWx * sumWy) / denom;
            result[i] = a + b * static_cast<double>(i);
        }
    }

    return result;
}

QVector<double> applySmoothing(const QVector<double> &data, const QString &method,
                                int windowLength, int polyOrder, double sigma,
                                double alpha, double lowessFrac)
{
    QString m = method.toLower().trimmed();

    if (m == "moving_average" || m == "moving average")
        return movingAverage(data, windowLength);
    if (m == "savitzky-golay" || m == "savitzky_golay" || m == "sg")
        return savitzkyGolay(data, windowLength, polyOrder);
    if (m == "gaussian" || m == "gaussian_filter")
        return gaussianFilter(data, sigma);
    if (m == "ema" || m == "exponential_moving_average" || m == "exponential_moving_avg"
        || m == "exponential moving average" || m == "exponential moving avg")
        return exponentialMovingAverage(data, alpha);
    if (m == "median" || m == "median_filter")
        return medianFilter(data, windowLength);
    if (m == "lowess" || m == "lowess_smoothing" || m == "lowess_local_regression"
        || m == "lowess local regression")
        return lowessSmoothing(data, lowessFrac);

    qWarning() << "Unknown smoothing method:" << method << "- returning original data";
    return data;
}

} // namespace Smoothing
