// Excel (.xlsx / .xlsm) loading.
//
// An .xlsx file is a ZIP archive of XML parts. The worksheet XML of a large
// measurement export can be several hundred MB once decompressed, so the
// worksheet is inflated in chunks and scanned with a small purpose-built
// parser instead of being materialised in memory. Decompression uses the
// zlib bundled with Qt (Qt6::ZlibPrivate), so no extra dependency is needed.

#include "fileloaders.h"

#include <QDebug>
#include <QFile>
#include <QHash>
#include <QXmlStreamReader>
#include <QtEndian>

#include <zlib.h>

#include <algorithm>
#include <charconv>
#include <cmath>
#include <cstring>
#include <functional>
#include <limits>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace FileLoaders {
namespace {

constexpr double kNaN = std::numeric_limits<double>::quiet_NaN();
constexpr size_t npos = std::string_view::npos;
constexpr int kMaxExcelColumns = 16384;

[[noreturn]] void fail(const QString &message)
{
    throw std::runtime_error(message.toStdString());
}

[[noreturn]] void failCorrupt()
{
    fail(QStringLiteral("The Excel file is damaged or is not a valid .xlsx file."));
}

// ---------------------------------------------------------------------------
// Minimal read-only ZIP archive (stored and deflated entries, ZIP64 aware)
// ---------------------------------------------------------------------------

class ZipArchive {
public:
    using Sink = std::function<bool(const char *data, qsizetype size)>;

    explicit ZipArchive(const QString &path) : m_file(path)
    {
        if (!m_file.open(QIODevice::ReadOnly))
            fail(QStringLiteral("Cannot open file: %1").arg(path));
        m_size = m_file.size();
        if (m_size >= 4 && m_file.peek(4) == QByteArray("\xD0\xCF\x11\xE0", 4))
            fail(QStringLiteral("Legacy .xls files (Excel 97-2003) are not supported. "
                                "Please open the file in Excel and save it as .xlsx."));
        if (m_size < 22)
            failCorrupt();
        m_data = m_file.map(0, m_size);
        if (!m_data)
            fail(QStringLiteral("Cannot read file: %1").arg(path));
        readCentralDirectory();
    }

    bool contains(const QString &name) const { return m_entries.contains(name.toLower()); }

    QByteArray read(const QString &name) const
    {
        QByteArray out;
        stream(name, [&out](const char *data, qsizetype size) {
            out.append(data, size);
            return true;
        });
        return out;
    }

    // Passes the uncompressed entry to `sink` chunk by chunk. The sink returns
    // false to stop early.
    void stream(const QString &name, const Sink &sink) const;

private:
    struct Entry {
        quint16 flags = 0;
        quint16 method = 0;
        quint64 compSize = 0;
        quint64 uncompSize = 0;
        quint64 localOffset = 0;
    };

    void check(quint64 offset, quint64 length) const
    {
        if (offset > quint64(m_size) || length > quint64(m_size) - offset)
            failCorrupt();
    }
    quint16 u16(quint64 off) const { check(off, 2); return qFromLittleEndian<quint16>(m_data + off); }
    quint32 u32(quint64 off) const { check(off, 4); return qFromLittleEndian<quint32>(m_data + off); }
    quint64 u64(quint64 off) const { check(off, 8); return qFromLittleEndian<quint64>(m_data + off); }

    void readCentralDirectory();

    QFile m_file;
    const uchar *m_data = nullptr;
    qint64 m_size = 0;
    QHash<QString, Entry> m_entries;   // keyed by lower-case entry name
};

void ZipArchive::readCentralDirectory()
{
    if (u32(0) != 0x04034b50)
        failCorrupt();

    // The end-of-central-directory record sits at the end, before an optional comment.
    qint64 eocd = -1;
    const qint64 lowest = qMax<qint64>(0, m_size - 22 - 0xFFFF);
    for (qint64 p = m_size - 22; p >= lowest; --p) {
        if (u32(p) == 0x06054b50) {
            eocd = p;
            break;
        }
    }
    if (eocd < 0)
        failCorrupt();

    quint64 count = u16(eocd + 10);
    quint64 offset = u32(eocd + 16);
    if ((count == 0xFFFF || offset == 0xFFFFFFFF) && eocd >= 20 && u32(eocd - 20) == 0x07064b50) {
        const quint64 zip64 = u64(eocd - 20 + 8);
        if (u32(zip64) != 0x06064b50)
            failCorrupt();
        count = u64(zip64 + 32);
        offset = u64(zip64 + 48);
    }

    quint64 p = offset;
    for (quint64 i = 0; i < count; ++i) {
        if (u32(p) != 0x02014b50)
            failCorrupt();
        Entry e;
        e.flags = u16(p + 8);
        e.method = u16(p + 10);
        e.compSize = u32(p + 20);
        e.uncompSize = u32(p + 24);
        const quint16 nameLen = u16(p + 28);
        const quint16 extraLen = u16(p + 30);
        const quint16 commentLen = u16(p + 32);
        e.localOffset = u32(p + 42);
        check(p + 46, quint64(nameLen) + extraLen);

        QString name = QString::fromUtf8(reinterpret_cast<const char *>(m_data + p + 46), nameLen);

        // ZIP64 extended information replaces 32-bit fields set to 0xFFFFFFFF.
        quint64 x = p + 46 + nameLen;
        const quint64 extraEnd = x + extraLen;
        while (x + 4 <= extraEnd) {
            const quint16 id = u16(x);
            const quint16 size = u16(x + 2);
            quint64 field = x + 4;
            const quint64 fieldEnd = field + size;
            if (id == 0x0001) {
                if (e.uncompSize == 0xFFFFFFFF && field + 8 <= fieldEnd) { e.uncompSize = u64(field); field += 8; }
                if (e.compSize == 0xFFFFFFFF && field + 8 <= fieldEnd) { e.compSize = u64(field); field += 8; }
                if (e.localOffset == 0xFFFFFFFF && field + 8 <= fieldEnd) { e.localOffset = u64(field); }
            }
            x = fieldEnd;
        }

        m_entries.insert(name.replace('\\', '/').toLower(), e);
        p += 46 + quint64(nameLen) + extraLen + commentLen;
    }
}

void ZipArchive::stream(const QString &name, const Sink &sink) const
{
    const auto it = m_entries.constFind(name.toLower());
    if (it == m_entries.cend())
        fail(QStringLiteral("The Excel file is missing the part '%1'.").arg(name));
    const Entry &e = *it;
    if (e.flags & 0x1)
        fail(QStringLiteral("Password-protected Excel files are not supported."));

    const quint64 header = e.localOffset;
    if (u32(header) != 0x04034b50)
        failCorrupt();
    const quint64 dataOffset = header + 30 + u16(header + 26) + u16(header + 28);
    check(dataOffset, e.compSize);
    const uchar *src = m_data + dataOffset;

    if (e.method == 0) {   // stored
        for (quint64 done = 0; done < e.compSize;) {
            const qsizetype n = qsizetype(qMin<quint64>(e.compSize - done, 1 << 20));
            if (!sink(reinterpret_cast<const char *>(src + done), n))
                return;
            done += quint64(n);
        }
        return;
    }
    if (e.method != 8)
        fail(QStringLiteral("Unsupported compression method %1 in Excel file.").arg(e.method));

    z_stream zs{};
    if (inflateInit2(&zs, -MAX_WBITS) != Z_OK)
        fail(QStringLiteral("Failed to initialise the decompressor."));
    struct InflateGuard {
        z_stream *zs;
        ~InflateGuard() { inflateEnd(zs); }
    } guard{&zs};

    std::vector<char> out(1 << 20);
    quint64 consumed = 0;
    int ret = Z_OK;
    while (ret != Z_STREAM_END) {
        if (zs.avail_in == 0) {
            const quint64 remaining = e.compSize - consumed;
            if (remaining == 0)
                failCorrupt();
            const uInt n = uInt(qMin<quint64>(remaining, 1u << 30));
            zs.next_in = const_cast<Bytef *>(src + consumed);
            zs.avail_in = n;
            consumed += n;
        }
        zs.next_out = reinterpret_cast<Bytef *>(out.data());
        zs.avail_out = uInt(out.size());
        ret = inflate(&zs, Z_NO_FLUSH);
        if (ret != Z_OK && ret != Z_STREAM_END)
            failCorrupt();
        const qsizetype produced = qsizetype(out.size() - zs.avail_out);
        if (produced > 0 && !sink(out.data(), produced))
            return;
    }
}

// ---------------------------------------------------------------------------
// XML helpers for the streaming worksheet scanner
// ---------------------------------------------------------------------------

bool isNameEnd(char c)
{
    return c == ' ' || c == '\t' || c == '\r' || c == '\n' || c == '>' || c == '/';
}

// Local element name of a tag body ("x:c r=..." -> "c").
std::string_view localName(std::string_view tag)
{
    size_t end = 0;
    while (end < tag.size() && !isNameEnd(tag[end]))
        ++end;
    std::string_view name = tag.substr(0, end);
    const size_t colon = name.rfind(':');
    return colon == npos ? name : name.substr(colon + 1);
}

// Qualified element name of a tag body ("x:c r=..." -> "x:c").
std::string_view qualifiedName(std::string_view tag)
{
    size_t end = 0;
    while (end < tag.size() && !isNameEnd(tag[end]))
        ++end;
    return tag.substr(0, end);
}

// Calls fn(name, value) for each attribute of a tag body (text between '<' and '>').
template <typename Fn>
void forEachAttribute(std::string_view tag, Fn fn)
{
    size_t i = qualifiedName(tag).size();
    while (true) {
        while (i < tag.size() && (tag[i] == ' ' || tag[i] == '\t' || tag[i] == '\r' || tag[i] == '\n'))
            ++i;
        if (i >= tag.size() || tag[i] == '/')
            return;
        const size_t eq = tag.find('=', i);
        if (eq == npos)
            return;
        std::string_view name = tag.substr(i, eq - i);
        while (!name.empty() && (name.back() == ' ' || name.back() == '\t'))
            name.remove_suffix(1);
        size_t q = eq + 1;
        while (q < tag.size() && (tag[q] == ' ' || tag[q] == '\t'))
            ++q;
        if (q >= tag.size() || (tag[q] != '"' && tag[q] != '\''))
            return;
        const size_t close = tag.find(tag[q], q + 1);
        if (close == npos)
            return;
        fn(name, tag.substr(q + 1, close - q - 1));
        i = close + 1;
    }
}

// Position of the '<' of the first start tag with the given local name.
size_t findStartTag(std::string_view s, std::string_view name)
{
    for (size_t lt = s.find('<'); lt != npos; lt = s.find('<', lt + 1)) {
        size_t end = lt + 1;
        while (end < s.size() && !isNameEnd(s[end]))
            ++end;
        if (end >= s.size())
            return npos;
        if (localName(s.substr(lt + 1, end - lt - 1)) == name)
            return lt;
    }
    return npos;
}

QString decodeXmlText(std::string_view s)
{
    if (s.find('&') == npos)
        return QString::fromUtf8(s.data(), qsizetype(s.size()));

    std::string out;
    out.reserve(s.size());
    for (size_t i = 0; i < s.size();) {
        if (s[i] != '&') {
            out += s[i++];
            continue;
        }
        const size_t semi = s.find(';', i);
        if (semi == npos) {
            out.append(s.substr(i));
            break;
        }
        const std::string_view entity = s.substr(i + 1, semi - i - 1);
        if (entity == "amp") out += '&';
        else if (entity == "lt") out += '<';
        else if (entity == "gt") out += '>';
        else if (entity == "quot") out += '"';
        else if (entity == "apos") out += '\'';
        else if (entity.size() > 1 && entity[0] == '#') {
            const bool hex = entity[1] == 'x' || entity[1] == 'X';
            const std::string_view digits = entity.substr(hex ? 2 : 1);
            quint32 code = 0;
            const auto res = std::from_chars(digits.data(), digits.data() + digits.size(), code, hex ? 16 : 10);
            if (res.ec == std::errc() && res.ptr == digits.data() + digits.size()) {
                const char32_t cp = char32_t(code);
                out.append(QString::fromUcs4(&cp, 1).toStdString());
            }
            else
                out.append(s.substr(i, semi - i + 1));
        } else {
            out.append(s.substr(i, semi - i + 1));
        }
        i = semi + 1;
    }
    return QString::fromStdString(out);
}

double parseDouble(std::string_view s)
{
    while (!s.empty() && (s.front() == ' ' || s.front() == '+'))
        s.remove_prefix(1);
    double value = kNaN;
    const auto res = std::from_chars(s.data(), s.data() + s.size(), value);
    return res.ec == std::errc() ? value : kNaN;
}

// Converts text cell content to a number where possible ("1,5" -> 1.5).
double parseText(const QString &text)
{
    QString cleaned = text.trimmed();
    cleaned.replace(',', '.');
    bool ok = false;
    const double value = cleaned.toDouble(&ok);
    return ok ? value : kNaN;
}

// Zero-based column index of a cell reference ("AB12" -> 27), or -1.
int columnFromRef(std::string_view ref)
{
    int col = 0;
    size_t i = 0;
    for (; i < ref.size(); ++i) {
        char c = ref[i];
        if (c >= 'a' && c <= 'z')
            c = char(c - 'a' + 'A');
        if (c < 'A' || c > 'Z')
            break;
        col = col * 26 + (c - 'A' + 1);
        if (col > kMaxExcelColumns)
            return -1;
    }
    return i == 0 ? -1 : col - 1;
}

qint64 rowFromRef(std::string_view ref)
{
    size_t i = 0;
    while (i < ref.size() && !(ref[i] >= '0' && ref[i] <= '9'))
        ++i;
    qint64 row = 0;
    const auto res = std::from_chars(ref.data() + i, ref.data() + ref.size(), row);
    return res.ec == std::errc() ? row : 0;
}

QString columnLetters(int col)
{
    QString letters;
    for (int n = col + 1; n > 0; n = (n - 1) / 26)
        letters.prepend(QChar('A' + (n - 1) % 26));
    return letters;
}

// ---------------------------------------------------------------------------
// Streaming worksheet reader
// ---------------------------------------------------------------------------

// Builds numeric columns from <sheetData>. The first non-empty row is the
// header; columns without any numeric value (e.g. text labels) are dropped.
class SheetReader {
public:
    explicit SheetReader(const QStringList &sharedStrings) : m_sharedStrings(sharedStrings) {}

    // Returns false once the end of the sheet data has been reached.
    bool feed(const char *data, qsizetype size);
    DataFrame takeDataFrame();

private:
    size_t process(std::string_view s);
    void startRow(std::string_view tag);
    void readCell(std::string_view tag, std::string_view content);
    void storeHeader(int col, const QString &text);
    void storeValue(int col, double value);
    void ensureColumn(int col);

    const QStringList &m_sharedStrings;
    std::string m_buf;
    bool m_inSheetData = false;
    bool m_done = false;
    qint64 m_row = 0;        // current 1-based row number
    int m_col = -1;          // last zero-based column in the current row
    qint64 m_headerRow = 0;
    qsizetype m_reserve = 0;
    std::vector<QVector<double>> m_columns;
    std::vector<QString> m_headers;
    std::vector<bool> m_hasNumber;
};

bool SheetReader::feed(const char *data, qsizetype size)
{
    if (m_done)
        return false;
    m_buf.append(data, size_t(size));

    if (!m_inSheetData) {
        const size_t lt = findStartTag(m_buf, "sheetData");
        if (lt == npos)
            return true;
        const size_t gt = m_buf.find('>', lt);
        if (gt == npos)
            return true;

        // <dimension ref="A1:DE91841"/> gives the row count up front.
        const std::string_view head(m_buf.data(), lt);
        const size_t dim = findStartTag(head, "dimension");
        const size_t dimEnd = dim == npos ? npos : head.find('>', dim);
        if (dimEnd != npos) {
            forEachAttribute(head.substr(dim + 1, dimEnd - dim - 1), [this](std::string_view name, std::string_view value) {
                if (name == "ref") {
                    const size_t colon = value.find(':');
                    const qint64 lastRow = rowFromRef(colon == npos ? value : value.substr(colon + 1));
                    m_reserve = qsizetype(std::clamp<qint64>(lastRow - 1, 0, 50'000'000));
                }
            });
        }

        if (m_buf[gt - 1] == '/') {   // <sheetData/>: empty sheet
            m_done = true;
            return false;
        }
        m_buf.erase(0, gt + 1);
        m_inSheetData = true;
    }

    m_buf.erase(0, process(m_buf));
    return !m_done;
}

// Handles complete elements in `s` and returns how many bytes were consumed.
size_t SheetReader::process(std::string_view s)
{
    size_t pos = 0;
    while (true) {
        const size_t lt = s.find('<', pos);
        if (lt == npos)
            return s.size();
        const size_t gt = s.find('>', lt);
        if (gt == npos)
            return lt;

        const std::string_view tag = s.substr(lt + 1, gt - lt - 1);
        if (!tag.empty() && tag[0] == '/') {
            if (localName(tag.substr(1)) == "sheetData") {
                m_done = true;
                return gt + 1;
            }
            pos = gt + 1;
            continue;
        }

        const std::string_view name = localName(tag);
        const bool selfClosing = !tag.empty() && tag.back() == '/';

        if (name == "row") {
            startRow(tag);
            pos = gt + 1;
        } else if (name == "c") {
            if (selfClosing) {
                readCell(tag, {});
                pos = gt + 1;
                continue;
            }
            const std::string_view qname = qualifiedName(tag);
            size_t end;
            size_t closeLen;
            if (qname == "c") {
                end = s.find("</c>", gt + 1);
                closeLen = 4;
            } else {
                const std::string close = "</" + std::string(qname) + ">";
                end = s.find(close, gt + 1);
                closeLen = close.size();
            }
            if (end == npos)
                return lt;   // cell continues in the next chunk
            readCell(tag, s.substr(gt + 1, end - gt - 1));
            pos = end + closeLen;
        } else {
            pos = gt + 1;
        }
    }
}

void SheetReader::startRow(std::string_view tag)
{
    qint64 row = 0;
    forEachAttribute(tag, [&row](std::string_view name, std::string_view value) {
        if (name == "r")
            std::from_chars(value.data(), value.data() + value.size(), row);
    });
    m_row = row > 0 ? row : m_row + 1;
    m_col = -1;
}

void SheetReader::readCell(std::string_view tag, std::string_view content)
{
    int col = -1;
    std::string_view type;
    forEachAttribute(tag, [&](std::string_view name, std::string_view value) {
        if (name == "r")
            col = columnFromRef(value);
        else if (name == "t")
            type = value;
    });
    if (col < 0)
        col = m_col + 1;
    m_col = col;
    if (col >= kMaxExcelColumns || m_row <= 0)
        return;

    // Pull the <v> value or the inline string text out of the cell body.
    std::string_view rawValue;
    bool hasValue = false;
    QString inlineText;
    bool hasInline = false;
    int phoneticDepth = 0;
    for (size_t p = 0; p < content.size();) {
        const size_t lt = content.find('<', p);
        if (lt == npos)
            break;
        const size_t gt = content.find('>', lt);
        if (gt == npos)
            break;
        const std::string_view t = content.substr(lt + 1, gt - lt - 1);
        p = gt + 1;
        if (!t.empty() && t[0] == '/') {
            if (localName(t.substr(1)) == "rPh")
                --phoneticDepth;
            continue;
        }
        if (t.empty() || t.back() == '/')
            continue;
        const std::string_view name = localName(t);
        if (name == "rPh") {
            ++phoneticDepth;
        } else if (name == "v" || (name == "t" && phoneticDepth == 0)) {
            size_t end = content.find('<', gt + 1);
            if (end == npos)
                end = content.size();
            const std::string_view text = content.substr(gt + 1, end - gt - 1);
            if (name == "v") {
                rawValue = text;
                hasValue = true;
            } else {
                inlineText += decodeXmlText(text);
                hasInline = true;
            }
            p = end;
        }
    }

    bool isText = false;
    QString text;
    double number = kNaN;
    if (type == "inlineStr") {
        if (!hasInline)
            return;
        isText = true;
        text = inlineText;
    } else {
        if (!hasValue)
            return;
        if (type == "s") {
            int index = -1;
            std::from_chars(rawValue.data(), rawValue.data() + rawValue.size(), index);
            isText = true;
            text = m_sharedStrings.value(index);
        } else if (type == "str" || type == "d") {
            isText = true;
            text = decodeXmlText(rawValue);
        } else if (type == "b") {
            number = rawValue == "1" ? 1.0 : 0.0;
        } else if (type == "e") {
            number = kNaN;   // #DIV/0!, #N/A, ...
        } else {
            number = parseDouble(rawValue);
        }
    }

    if (m_headerRow == 0)
        m_headerRow = m_row;
    if (m_row == m_headerRow)
        storeHeader(col, isText ? text : QString::number(number, 'g', 15));
    else if (m_row > m_headerRow)
        storeValue(col, isText ? parseText(text) : number);
}

void SheetReader::ensureColumn(int col)
{
    if (size_t(col) >= m_columns.size()) {
        m_columns.resize(size_t(col) + 1);
        m_headers.resize(size_t(col) + 1);
        m_hasNumber.resize(size_t(col) + 1, false);
    }
}

void SheetReader::storeHeader(int col, const QString &text)
{
    ensureColumn(col);
    m_headers[size_t(col)] = text.trimmed();
}

void SheetReader::storeValue(int col, double value)
{
    ensureColumn(col);
    QVector<double> &column = m_columns[size_t(col)];
    if (column.isEmpty() && m_reserve > 0)
        column.reserve(m_reserve);

    const qsizetype index = qsizetype(m_row - m_headerRow - 1);
    if (index < column.size()) {
        column[index] = value;
    } else {
        if (index > column.size())
            column.resize(index, kNaN);
        column.append(value);
    }
    if (!std::isnan(value))
        m_hasNumber[size_t(col)] = true;
}

DataFrame SheetReader::takeDataFrame()
{
    qsizetype rows = 0;
    for (size_t c = 0; c < m_columns.size(); ++c) {
        if (m_hasNumber[c])
            rows = qMax(rows, m_columns[c].size());
    }

    QStringList names;
    std::vector<size_t> kept;
    for (size_t c = 0; c < m_columns.size(); ++c) {
        if (!m_hasNumber[c])
            continue;
        names.append(m_headers[c].isEmpty() ? QStringLiteral("Column_") + columnLetters(int(c))
                                            : m_headers[c]);
        kept.push_back(c);
    }
    names = makeUniqueNames(names);

    DataFrame df;
    for (size_t i = 0; i < kept.size(); ++i) {
        QVector<double> &column = m_columns[kept[i]];
        column.resize(rows, kNaN);
        df.addColumn(names[qsizetype(i)], std::move(column));
    }
    return df;
}

// ---------------------------------------------------------------------------
// Workbook structure
// ---------------------------------------------------------------------------

struct Relationship {
    QString type;
    QString target;
};

struct SheetInfo {
    QString name;
    QString path;
};

struct WorkbookInfo {
    QList<SheetInfo> sheets;
    QString sharedStringsPath;
};

QString directoryOf(const QString &part)
{
    const qsizetype slash = part.lastIndexOf('/');
    return slash < 0 ? QString() : part.left(slash);
}

QString resolveTarget(const QString &baseDir, const QString &target)
{
    if (target.startsWith('/'))
        return target.mid(1);
    QStringList parts = baseDir.isEmpty() ? QStringList() : baseDir.split('/');
    for (const QString &segment : target.split('/')) {
        if (segment == "..") {
            if (!parts.isEmpty())
                parts.removeLast();
        } else if (!segment.isEmpty() && segment != ".") {
            parts.append(segment);
        }
    }
    return parts.join('/');
}

QHash<QString, Relationship> readRelationships(const ZipArchive &zip, const QString &relsPath)
{
    QHash<QString, Relationship> rels;
    if (!zip.contains(relsPath))
        return rels;
    QXmlStreamReader xml(zip.read(relsPath));
    while (!xml.atEnd()) {
        if (xml.readNext() == QXmlStreamReader::StartElement && xml.name() == u"Relationship") {
            const QXmlStreamAttributes attrs = xml.attributes();
            rels.insert(attrs.value("Id").toString(),
                        {attrs.value("Type").toString(), attrs.value("Target").toString()});
        }
    }
    if (xml.hasError())
        failCorrupt();
    return rels;
}

WorkbookInfo readWorkbook(const ZipArchive &zip)
{
    QString workbookPath = QStringLiteral("xl/workbook.xml");
    for (const Relationship &rel : readRelationships(zip, QStringLiteral("_rels/.rels"))) {
        if (rel.type.endsWith(QLatin1String("/officeDocument"))) {
            workbookPath = resolveTarget(QString(), rel.target);
            break;
        }
    }
    if (!zip.contains(workbookPath))
        fail(QStringLiteral("The file does not contain an Excel workbook."));

    const QString baseDir = directoryOf(workbookPath);
    const QString relsPath = (baseDir.isEmpty() ? QString() : baseDir + '/') + "_rels/"
                             + workbookPath.mid(workbookPath.lastIndexOf('/') + 1) + ".rels";
    const QHash<QString, Relationship> rels = readRelationships(zip, relsPath);

    WorkbookInfo info;
    for (const Relationship &rel : rels) {
        if (rel.type.endsWith(QLatin1String("/sharedStrings")))
            info.sharedStringsPath = resolveTarget(baseDir, rel.target);
    }

    QXmlStreamReader xml(zip.read(workbookPath));
    while (!xml.atEnd()) {
        if (xml.readNext() != QXmlStreamReader::StartElement || xml.name() != u"sheet")
            continue;
        QString name;
        QString relId;
        for (const QXmlStreamAttribute &attr : xml.attributes()) {
            if (attr.name() == u"name")
                name = attr.value().toString();
            else if (attr.name() == u"id")
                relId = attr.value().toString();
        }
        // Chart sheets and other non-worksheet parts hold no cell data.
        const auto rel = rels.constFind(relId);
        if (rel != rels.cend() && rel->type.endsWith(QLatin1String("/worksheet")))
            info.sheets.append({name, resolveTarget(baseDir, rel->target)});
    }
    if (xml.hasError())
        failCorrupt();
    return info;
}

QStringList readSharedStrings(const ZipArchive &zip, const QString &path)
{
    QStringList strings;
    if (path.isEmpty() || !zip.contains(path))
        return strings;

    QXmlStreamReader xml(zip.read(path));
    QString current;
    int phoneticDepth = 0;
    while (!xml.atEnd()) {
        const QXmlStreamReader::TokenType token = xml.readNext();
        if (token == QXmlStreamReader::StartElement) {
            if (xml.name() == u"si")
                current.clear();
            else if (xml.name() == u"rPh")
                ++phoneticDepth;
            else if (xml.name() == u"t" && phoneticDepth == 0)
                current += xml.readElementText();
        } else if (token == QXmlStreamReader::EndElement) {
            if (xml.name() == u"si")
                strings.append(current);
            else if (xml.name() == u"rPh")
                --phoneticDepth;
        }
    }
    if (xml.hasError())
        failCorrupt();
    return strings;
}

} // namespace

QStringList getExcelSheets(const QString &filePath)
{
    ZipArchive zip(filePath);
    QStringList names;
    for (const SheetInfo &sheet : readWorkbook(zip).sheets)
        names.append(sheet.name);
    return names;
}

DataFrame loadExcelFile(const QString &filePath, const QString &sheetName)
{
    qInfo() << "Loading Excel file:" << filePath << "sheet:" << sheetName;

    ZipArchive zip(filePath);
    const WorkbookInfo workbook = readWorkbook(zip);
    if (workbook.sheets.isEmpty())
        fail(QStringLiteral("No worksheets found in the Excel file."));

    const SheetInfo *sheet = &workbook.sheets.first();
    if (!sheetName.isEmpty()) {
        sheet = nullptr;
        for (const SheetInfo &s : workbook.sheets) {
            if (s.name == sheetName) {
                sheet = &s;
                break;
            }
        }
        if (!sheet)
            fail(QStringLiteral("Sheet '%1' not found in the Excel file.").arg(sheetName));
    }

    const QStringList sharedStrings = readSharedStrings(zip, workbook.sharedStringsPath);
    SheetReader reader(sharedStrings);
    zip.stream(sheet->path, [&reader](const char *data, qsizetype size) {
        return reader.feed(data, size);
    });

    DataFrame df = reader.takeDataFrame();
    qInfo() << "Loaded Excel sheet" << sheet->name << ":" << df.rowCount() << "rows,"
            << df.columnCount() << "columns";
    return df;
}

} // namespace FileLoaders
