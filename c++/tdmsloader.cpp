// NI TDMS (Technical Data Management Streaming) loading.
//
// Implements the TDMS 2.0 file format (LabVIEW / DIAdem): a sequence of
// segments, each with a lead-in, optional metadata (objects, raw data
// indexes, properties) and raw channel data. Every numeric channel becomes a
// DataFrame column named "<group>/<channel>"; shorter channels are padded
// with NaN, matching the former Python (npTDMS) loader.

#include "fileloaders.h"

#include <QDebug>
#include <QFile>
#include <QHash>
#include <QtEndian>

#include <algorithm>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <vector>

namespace FileLoaders {
namespace {

constexpr double kNaN = std::numeric_limits<double>::quiet_NaN();

// Lead-in table of contents flags
constexpr quint32 kTocMetaData = 1u << 1;
constexpr quint32 kTocNewObjList = 1u << 2;
constexpr quint32 kTocRawData = 1u << 3;
constexpr quint32 kTocInterleavedData = 1u << 5;
constexpr quint32 kTocBigEndian = 1u << 6;
constexpr quint32 kTocDAQmxRawData = 1u << 7;

constexpr quint32 kNoRawData = 0xFFFFFFFF;
constexpr quint32 kSameRawIndex = 0x00000000;
constexpr quint32 kDAQmxFormatChanging = 0x69120000;
constexpr quint32 kDAQmxDigitalLine = 0x69130000;

enum DataType : quint32 {
    tdsTypeVoid = 0x00,
    tdsTypeI8 = 0x01,
    tdsTypeI16 = 0x02,
    tdsTypeI32 = 0x03,
    tdsTypeI64 = 0x04,
    tdsTypeU8 = 0x05,
    tdsTypeU16 = 0x06,
    tdsTypeU32 = 0x07,
    tdsTypeU64 = 0x08,
    tdsTypeSingleFloat = 0x09,
    tdsTypeDoubleFloat = 0x0A,
    tdsTypeExtendedFloat = 0x0B,
    tdsTypeSingleFloatWithUnit = 0x19,
    tdsTypeDoubleFloatWithUnit = 0x1A,
    tdsTypeString = 0x20,
    tdsTypeBoolean = 0x21,
    tdsTypeTimeStamp = 0x44,
    tdsTypeFixedPoint = 0x4F,
    tdsTypeComplexSingleFloat = 0x08000C,
    tdsTypeComplexDoubleFloat = 0x10000D,
    tdsTypeDAQmxRawData = 0xFFFFFFFF,
};

[[noreturn]] void fail(const QString &message)
{
    throw std::runtime_error(message.toStdString());
}

// Size in bytes of one value, 0 for variable-length or unknown types.
quint64 typeSize(quint32 type)
{
    switch (type) {
    case tdsTypeI8: case tdsTypeU8: case tdsTypeBoolean: return 1;
    case tdsTypeI16: case tdsTypeU16: return 2;
    case tdsTypeI32: case tdsTypeU32: case tdsTypeSingleFloat: case tdsTypeSingleFloatWithUnit: return 4;
    case tdsTypeI64: case tdsTypeU64: case tdsTypeDoubleFloat: case tdsTypeDoubleFloatWithUnit:
    case tdsTypeComplexSingleFloat: return 8;
    case tdsTypeExtendedFloat: case tdsTypeTimeStamp: case tdsTypeComplexDoubleFloat: return 16;
    default: return 0;
    }
}

bool isNumericType(quint32 type)
{
    switch (type) {
    case tdsTypeI8: case tdsTypeI16: case tdsTypeI32: case tdsTypeI64:
    case tdsTypeU8: case tdsTypeU16: case tdsTypeU32: case tdsTypeU64:
    case tdsTypeSingleFloat: case tdsTypeDoubleFloat:
    case tdsTypeSingleFloatWithUnit: case tdsTypeDoubleFloatWithUnit:
    case tdsTypeBoolean: case tdsTypeTimeStamp:
        return true;
    default:
        return false;
    }
}

template <typename T>
T readRaw(const uchar *p, bool bigEndian)
{
    return bigEndian ? qFromBigEndian<T>(p) : qFromLittleEndian<T>(p);
}

template <typename F, typename U>
F readFloat(const uchar *p, bool bigEndian)
{
    const U bits = readRaw<U>(p, bigEndian);
    F value;
    std::memcpy(&value, &bits, sizeof value);
    return value;
}

// Converts one value of a numeric type to double. Timestamps become seconds
// since the Unix epoch.
double readValue(const uchar *p, quint32 type, bool bigEndian)
{
    switch (type) {
    case tdsTypeI8: return double(qint8(*p));
    case tdsTypeU8: return double(*p);
    case tdsTypeBoolean: return *p ? 1.0 : 0.0;
    case tdsTypeI16: return double(readRaw<qint16>(p, bigEndian));
    case tdsTypeU16: return double(readRaw<quint16>(p, bigEndian));
    case tdsTypeI32: return double(readRaw<qint32>(p, bigEndian));
    case tdsTypeU32: return double(readRaw<quint32>(p, bigEndian));
    case tdsTypeI64: return double(readRaw<qint64>(p, bigEndian));
    case tdsTypeU64: return double(readRaw<quint64>(p, bigEndian));
    case tdsTypeSingleFloat:
    case tdsTypeSingleFloatWithUnit: return double(readFloat<float, quint32>(p, bigEndian));
    case tdsTypeDoubleFloat:
    case tdsTypeDoubleFloatWithUnit: return readFloat<double, quint64>(p, bigEndian);
    case tdsTypeTimeStamp: {
        // Seconds since 1904-01-01 UTC plus a 2^-64 fraction.
        const quint64 fraction = readRaw<quint64>(bigEndian ? p + 8 : p, bigEndian);
        const qint64 seconds = readRaw<qint64>(bigEndian ? p : p + 8, bigEndian);
        constexpr double kSeconds1904To1970 = 2082844800.0;
        return double(seconds) - kSeconds1904To1970 + double(fraction) / 18446744073709551616.0;
    }
    default: return kNaN;
    }
}

// Bounds-checked reader over the memory-mapped file.
class Cursor {
public:
    Cursor(const uchar *data, quint64 pos, quint64 end, bool bigEndian)
        : m_data(data), m_pos(pos), m_end(end), m_bigEndian(bigEndian) {}

    template <typename T>
    T read()
    {
        need(sizeof(T));
        const T value = readRaw<T>(m_data + m_pos, m_bigEndian);
        m_pos += sizeof(T);
        return value;
    }

    QString readString()
    {
        const quint32 length = read<quint32>();
        need(length);
        const QString s = QString::fromUtf8(reinterpret_cast<const char *>(m_data + m_pos), qsizetype(length));
        m_pos += length;
        return s;
    }

    void skip(quint64 n)
    {
        need(n);
        m_pos += n;
    }

private:
    void need(quint64 n) const
    {
        if (n > m_end - m_pos)
            fail(QStringLiteral("The TDMS file is damaged (metadata extends past the end of its segment)."));
    }

    const uchar *m_data;
    quint64 m_pos;
    quint64 m_end;
    bool m_bigEndian;
};

void skipPropertyValue(Cursor &in, quint32 type)
{
    if (type == tdsTypeString) {
        in.skip(in.read<quint32>());
        return;
    }
    const quint64 size = typeSize(type);
    if (size == 0 && type != tdsTypeVoid)
        fail(QStringLiteral("Unsupported TDMS property data type 0x%1.").arg(type, 0, 16));
    in.skip(size);
}

// Splits an object path "/'Group'/'Channel'" into its components.
QStringList splitObjectPath(const QString &path)
{
    QStringList parts;
    qsizetype i = 0;
    while (i < path.size()) {
        if (path[i] != '/')
            break;
        ++i;
        if (i >= path.size() || path[i] != '\'')
            break;
        ++i;
        QString part;
        while (i < path.size()) {
            if (path[i] == '\'') {
                if (i + 1 < path.size() && path[i + 1] == '\'') {   // escaped quote
                    part += '\'';
                    i += 2;
                    continue;
                }
                ++i;
                break;
            }
            part += path[i++];
        }
        parts.append(part);
    }
    return parts;
}

struct RawIndex {
    bool hasData = false;
    bool daqmx = false;
    quint32 dataType = tdsTypeVoid;
    quint64 numValues = 0;
    quint64 chunkBytes = 0;   // bytes of this object per raw data chunk
};

struct TdmsObject {
    QString path;
    bool isChannel = false;
    RawIndex index;
    bool indexSeen = false;
    QVector<double> data;
};

void readRawIndex(Cursor &in, TdmsObject &obj)
{
    const quint32 header = in.read<quint32>();
    if (header == kNoRawData) {
        obj.index.hasData = false;
        return;
    }
    if (header == kSameRawIndex) {
        if (!obj.indexSeen)
            fail(QStringLiteral("The TDMS file is damaged (channel %1 reuses a missing data index).").arg(obj.path));
        obj.index.hasData = true;
        return;
    }

    RawIndex index;
    index.hasData = true;
    if (header == kDAQmxFormatChanging || header == kDAQmxDigitalLine) {
        index.daqmx = true;
        index.dataType = in.read<quint32>();
        in.read<quint32>();   // array dimension
        index.numValues = in.read<quint64>();
        const quint32 scalers = in.read<quint32>();
        in.skip(quint64(scalers) * (header == kDAQmxDigitalLine ? 17 : 20));
        const quint32 widths = in.read<quint32>();
        in.skip(quint64(widths) * 4);
    } else {
        index.dataType = in.read<quint32>();
        const quint32 dimension = in.read<quint32>();
        if (dimension != 1)
            fail(QStringLiteral("Unsupported TDMS array dimension %1.").arg(dimension));
        index.numValues = in.read<quint64>();
        if (index.dataType == tdsTypeString)
            index.chunkBytes = in.read<quint64>();
        else
            index.chunkBytes = index.numValues * typeSize(index.dataType);
    }
    obj.index = index;
    obj.indexSeen = true;
}

} // namespace

DataFrame loadTdmsFile(const QString &filePath)
{
    qInfo() << "Loading TDMS file:" << filePath;

    QFile file(filePath);
    if (!file.open(QIODevice::ReadOnly))
        fail(QStringLiteral("Cannot open file: %1").arg(filePath));
    const quint64 size = quint64(file.size());
    if (size < 28)
        fail(QStringLiteral("The file is not a valid TDMS file."));
    const uchar *data = file.map(0, qint64(size));
    if (!data)
        fail(QStringLiteral("Cannot read file: %1").arg(filePath));

    std::vector<TdmsObject> objects;
    QHash<QString, size_t> objectIndex;
    std::vector<size_t> activeObjects;   // objects with raw data, in raw data order
    bool warnedDAQmx = false;
    bool warnedTruncated = false;

    quint64 pos = 0;
    int segmentCount = 0;
    while (pos + 28 <= size) {
        if (std::memcmp(data + pos, "TDSm", 4) != 0) {
            if (pos == 0)
                fail(QStringLiteral("The file is not a valid TDMS file."));
            qWarning() << "TDMS: unexpected data at offset" << pos << "- ignoring the rest of the file";
            break;
        }

        const quint32 toc = qFromLittleEndian<quint32>(data + pos + 4);
        const bool bigEndian = toc & kTocBigEndian;
        const quint64 nextOffset = readRaw<quint64>(data + pos + 12, bigEndian);
        const quint64 rawOffset = readRaw<quint64>(data + pos + 20, bigEndian);
        const quint64 segStart = pos + 28;

        // An unfinished segment (writer crashed) has its next-segment offset
        // set to all ones; its data runs to the end of the file.
        quint64 segEnd = size;
        if (nextOffset != std::numeric_limits<quint64>::max() && nextOffset <= size - segStart)
            segEnd = segStart + nextOffset;
        else if (!warnedTruncated) {
            qWarning() << "TDMS: last segment is incomplete, reading the available data";
            warnedTruncated = true;
        }
        const quint64 rawStart = rawOffset <= segEnd - segStart ? segStart + rawOffset : segEnd;

        if (toc & kTocMetaData) {
            if (toc & kTocNewObjList)
                activeObjects.clear();

            Cursor in(data, segStart, rawStart, bigEndian);
            const quint32 objectCount = in.read<quint32>();
            for (quint32 i = 0; i < objectCount; ++i) {
                const QString path = in.readString();
                size_t idx;
                const auto found = objectIndex.constFind(path);
                if (found == objectIndex.cend()) {
                    idx = objects.size();
                    objectIndex.insert(path, idx);
                    TdmsObject obj;
                    obj.path = path;
                    obj.isChannel = splitObjectPath(path).size() == 2;
                    objects.push_back(std::move(obj));
                } else {
                    idx = *found;
                }

                readRawIndex(in, objects[idx]);
                if (objects[idx].index.hasData
                    && std::find(activeObjects.begin(), activeObjects.end(), idx) == activeObjects.end())
                    activeObjects.push_back(idx);

                const quint32 propertyCount = in.read<quint32>();
                for (quint32 p = 0; p < propertyCount; ++p) {
                    in.readString();
                    skipPropertyValue(in, in.read<quint32>());
                }
            }
        }

        if ((toc & kTocRawData) && rawStart < segEnd) {
            const bool interleaved = toc & kTocInterleavedData;
            std::vector<size_t> channels;
            quint64 chunkBytes = 0;
            bool daqmx = toc & kTocDAQmxRawData;
            for (size_t idx : activeObjects) {
                const RawIndex &index = objects[idx].index;
                if (!index.hasData)
                    continue;
                daqmx = daqmx || index.daqmx;
                channels.push_back(idx);
                chunkBytes += index.chunkBytes;
            }

            if (daqmx) {
                // DAQmx raw data needs NI scaling information to be meaningful.
                if (!warnedDAQmx)
                    qWarning() << "TDMS: DAQmx raw data is not supported and was skipped";
                warnedDAQmx = true;
            } else if (chunkBytes > 0) {
                const quint64 rawBytes = segEnd - rawStart;
                const quint64 chunks = (rawBytes + chunkBytes - 1) / chunkBytes;
                const uchar *p = data + rawStart;
                const uchar *end = data + segEnd;

                for (quint64 chunk = 0; chunk < chunks && p < end; ++chunk) {
                    if (interleaved) {
                        // Values of all channels alternate: one row per sample.
                        quint64 rowBytes = 0;
                        bool numericRow = true;
                        for (size_t idx : channels) {
                            const quint64 s = typeSize(objects[idx].index.dataType);
                            rowBytes += s;
                            numericRow = numericRow && s > 0;
                        }
                        if (!numericRow || rowBytes == 0)
                            fail(QStringLiteral("Unsupported interleaved TDMS data layout."));
                        const quint64 rows = qMin<quint64>(objects[channels.front()].index.numValues,
                                                           quint64(end - p) / rowBytes);
                        for (size_t idx : channels)
                            objects[idx].data.reserve(objects[idx].data.size() + qsizetype(rows));
                        for (quint64 r = 0; r < rows; ++r) {
                            for (size_t idx : channels) {
                                TdmsObject &obj = objects[idx];
                                if (obj.isChannel && isNumericType(obj.index.dataType))
                                    obj.data.append(readValue(p, obj.index.dataType, bigEndian));
                                p += typeSize(obj.index.dataType);
                            }
                        }
                        if (rows < objects[channels.front()].index.numValues)
                            p = end;
                    } else {
                        // Each channel's values are contiguous within the chunk.
                        for (size_t idx : channels) {
                            TdmsObject &obj = objects[idx];
                            const quint64 available = quint64(end - p);
                            if (obj.isChannel && isNumericType(obj.index.dataType)) {
                                const quint64 valueSize = typeSize(obj.index.dataType);
                                const quint64 count = qMin(obj.index.numValues, available / valueSize);
                                obj.data.reserve(obj.data.size() + qsizetype(count));
                                for (quint64 v = 0; v < count; ++v)
                                    obj.data.append(readValue(p + v * valueSize, obj.index.dataType, bigEndian));
                            }
                            p += qMin(obj.index.chunkBytes, available);
                        }
                    }
                }
            }
        }

        ++segmentCount;
        pos = segEnd;
    }

    // Assemble the DataFrame: numeric channels in file order, padded with NaN.
    QStringList names;
    std::vector<size_t> kept;
    qsizetype rows = 0;
    for (size_t i = 0; i < objects.size(); ++i) {
        const TdmsObject &obj = objects[i];
        if (!obj.isChannel || obj.data.isEmpty())
            continue;
        names.append(splitObjectPath(obj.path).join('/'));
        kept.push_back(i);
        rows = qMax(rows, obj.data.size());
    }
    names = makeUniqueNames(names);

    DataFrame df;
    for (size_t i = 0; i < kept.size(); ++i) {
        QVector<double> &column = objects[kept[i]].data;
        column.resize(rows, kNaN);
        df.addColumn(names[qsizetype(i)], std::move(column));
    }

    if (df.isEmpty() && warnedDAQmx)
        fail(QStringLiteral("This TDMS file contains DAQmx raw data, which is not supported. "
                            "Please export the channels as scaled data."));

    qInfo() << "Loaded TDMS file:" << segmentCount << "segments," << df.rowCount() << "rows,"
            << df.columnCount() << "columns";
    return df;
}

} // namespace FileLoaders
