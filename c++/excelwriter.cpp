// Excel (.xlsx) export.
//
// An .xlsx file is a ZIP archive of XML parts. Worksheets are generated and
// deflated in chunks straight into the output file, so exporting a large
// measurement does not build the whole worksheet XML in memory. Compression
// uses the zlib bundled with Qt (Qt6::ZlibPrivate), as the loader does.

#include "fileloaders.h"

#include <QDateTime>
#include <QSaveFile>
#include <QSet>
#include <QtEndian>

#include <zlib.h>

#include <charconv>
#include <cmath>
#include <cstring>
#include <stdexcept>
#include <string>
#include <vector>

namespace FileLoaders {
namespace {

constexpr int kMaxExcelRows = 1048576;
constexpr int kMaxExcelColumns = 16384;
constexpr int kMaxCellText = 32767;
constexpr size_t kFlushThreshold = 1 << 20;

[[noreturn]] void fail(const QString &message)
{
    throw std::runtime_error(message.toStdString());
}

template <typename T>
void putLE(QByteArray &out, T value)
{
    char buf[sizeof(T)];
    qToLittleEndian(value, buf);
    out.append(buf, sizeof(T));
}

// ---------------------------------------------------------------------------
// Minimal write-only ZIP archive (deflated entries with data descriptors)
// ---------------------------------------------------------------------------

class ZipWriter {
public:
    explicit ZipWriter(const QString &path) : m_file(path)
    {
        if (!m_file.open(QIODevice::WriteOnly))
            fail(QStringLiteral("Cannot open file for writing: %1").arg(path));

        const QDateTime now = QDateTime::currentDateTime();
        const QDate d = now.date();
        const QTime t = now.time();
        m_dosDate = quint16(((qMax(d.year(), 1980) - 1980) << 9) | (d.month() << 5) | d.day());
        m_dosTime = quint16((t.hour() << 11) | (t.minute() << 5) | (t.second() / 2));
    }

    ~ZipWriter()
    {
        if (m_inEntry)
            deflateEnd(&m_zs);
    }

    void beginEntry(const QString &name)
    {
        Entry e;
        e.name = name.toUtf8();
        e.offset = m_offset;

        QByteArray header;
        putLE<quint32>(header, 0x04034b50);
        putLE<quint16>(header, 20);          // version needed
        putLE<quint16>(header, kFlags);
        putLE<quint16>(header, 8);           // deflate
        putLE<quint16>(header, m_dosTime);
        putLE<quint16>(header, m_dosDate);
        putLE<quint32>(header, 0);           // crc, sizes: in the data descriptor
        putLE<quint32>(header, 0);
        putLE<quint32>(header, 0);
        putLE<quint16>(header, quint16(e.name.size()));
        putLE<quint16>(header, 0);
        header.append(e.name);
        writeRaw(header);

        m_entries.append(e);
        std::memset(&m_zs, 0, sizeof(m_zs));
        if (deflateInit2(&m_zs, Z_DEFAULT_COMPRESSION, Z_DEFLATED, -MAX_WBITS, 8,
                         Z_DEFAULT_STRATEGY) != Z_OK)
            fail(QStringLiteral("Cannot initialise compression."));
        m_inEntry = true;
    }

    void write(const char *data, size_t size)
    {
        Entry &e = m_entries.last();
        e.crc = crc32(e.crc, reinterpret_cast<const Bytef *>(data), uInt(size));
        e.uncompressed += size;
        m_zs.next_in = reinterpret_cast<Bytef *>(const_cast<char *>(data));
        m_zs.avail_in = uInt(size);
        pump(Z_NO_FLUSH);
    }

    void write(const QByteArray &data) { write(data.constData(), size_t(data.size())); }

    void endEntry()
    {
        m_zs.next_in = nullptr;
        m_zs.avail_in = 0;
        pump(Z_FINISH);
        deflateEnd(&m_zs);
        m_inEntry = false;

        Entry &e = m_entries.last();
        e.compressed = m_offset - e.offset - 30 - quint64(e.name.size());
        if (e.compressed > 0xFFFFFFFFu || e.uncompressed > 0xFFFFFFFFu)
            fail(QStringLiteral("The data is too large for an Excel file. Please save as CSV."));

        QByteArray descriptor;
        putLE<quint32>(descriptor, 0x08074b50);
        putLE<quint32>(descriptor, quint32(e.crc));
        putLE<quint32>(descriptor, quint32(e.compressed));
        putLE<quint32>(descriptor, quint32(e.uncompressed));
        writeRaw(descriptor);
    }

    void addEntry(const QString &name, const QByteArray &data)
    {
        beginEntry(name);
        write(data);
        endEntry();
    }

    void finish()
    {
        const quint64 cdOffset = m_offset;
        QByteArray cd;
        for (const Entry &e : m_entries) {
            putLE<quint32>(cd, 0x02014b50);
            putLE<quint16>(cd, 20);          // version made by
            putLE<quint16>(cd, 20);          // version needed
            putLE<quint16>(cd, kFlags);
            putLE<quint16>(cd, 8);
            putLE<quint16>(cd, m_dosTime);
            putLE<quint16>(cd, m_dosDate);
            putLE<quint32>(cd, quint32(e.crc));
            putLE<quint32>(cd, quint32(e.compressed));
            putLE<quint32>(cd, quint32(e.uncompressed));
            putLE<quint16>(cd, quint16(e.name.size()));
            putLE<quint16>(cd, 0);           // extra
            putLE<quint16>(cd, 0);           // comment
            putLE<quint16>(cd, 0);           // disk
            putLE<quint16>(cd, 0);           // internal attributes
            putLE<quint32>(cd, 0);           // external attributes
            putLE<quint32>(cd, quint32(e.offset));
            cd.append(e.name);
        }
        writeRaw(cd);
        if (m_offset > 0xFFFFFFFFu)
            fail(QStringLiteral("The data is too large for an Excel file. Please save as CSV."));

        QByteArray eocd;
        putLE<quint32>(eocd, 0x06054b50);
        putLE<quint16>(eocd, 0);
        putLE<quint16>(eocd, 0);
        putLE<quint16>(eocd, quint16(m_entries.size()));
        putLE<quint16>(eocd, quint16(m_entries.size()));
        putLE<quint32>(eocd, quint32(cd.size()));
        putLE<quint32>(eocd, quint32(cdOffset));
        putLE<quint16>(eocd, 0);
        writeRaw(eocd);

        if (!m_file.commit())
            fail(QStringLiteral("Could not write file: %1").arg(m_file.errorString()));
    }

private:
    static constexpr quint16 kFlags = 0x0808;   // data descriptor + UTF-8 names

    struct Entry {
        QByteArray name;
        quint64 offset = 0;
        quint64 compressed = 0;
        quint64 uncompressed = 0;
        uLong crc = 0;
    };

    void pump(int flush)
    {
        char out[64 * 1024];
        do {
            m_zs.next_out = reinterpret_cast<Bytef *>(out);
            m_zs.avail_out = sizeof(out);
            const int rc = deflate(&m_zs, flush);
            if (rc == Z_STREAM_ERROR)
                fail(QStringLiteral("Compression failed."));
            const qsizetype produced = qsizetype(sizeof(out) - m_zs.avail_out);
            if (produced > 0)
                writeRaw(out, produced);
            if (flush == Z_FINISH && rc == Z_STREAM_END)
                break;
        } while (m_zs.avail_out == 0 || (flush == Z_FINISH));
    }

    void writeRaw(const char *data, qsizetype size)
    {
        if (m_file.write(data, size) != size)
            fail(QStringLiteral("Could not write file: %1").arg(m_file.errorString()));
        m_offset += quint64(size);
    }

    void writeRaw(const QByteArray &data) { writeRaw(data.constData(), data.size()); }

    QSaveFile m_file;
    QVector<Entry> m_entries;
    z_stream m_zs {};
    bool m_inEntry = false;
    quint64 m_offset = 0;
    quint16 m_dosDate = 0;
    quint16 m_dosTime = 0;
};

// ---------------------------------------------------------------------------
// Worksheet XML
// ---------------------------------------------------------------------------

void appendEscaped(std::string &out, const QString &text)
{
    const QByteArray utf8 = text.left(kMaxCellText).toUtf8();
    for (char ch : utf8) {
        const unsigned char c = static_cast<unsigned char>(ch);
        switch (ch) {
        case '&': out += "&amp;"; break;
        case '<': out += "&lt;"; break;
        case '>': out += "&gt;"; break;
        case '"': out += "&quot;"; break;
        default:
            // Control characters other than tab/newline are not allowed in XML.
            if (c >= 0x20 || ch == '\t' || ch == '\n' || ch == '\r')
                out += ch;
        }
    }
}

QString columnLetters(int index)
{
    QString s;
    for (++index; index > 0; index = (index - 1) / 26)
        s.prepend(QChar('A' + (index - 1) % 26));
    return s;
}

class SheetXml {
public:
    SheetXml(ZipWriter &zip, int columns, bool freezeHeader) : m_zip(zip)
    {
        for (int c = 0; c < columns; ++c)
            m_letters.push_back(columnLetters(c).toStdString());

        m_buf = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
                "<worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">";
        if (freezeHeader)
            m_buf += "<sheetViews><sheetView workbookViewId=\"0\">"
                     "<pane ySplit=\"1\" topLeftCell=\"A2\" activePane=\"bottomLeft\" state=\"frozen\"/>"
                     "</sheetView></sheetViews>";
        if (columns > 0)
            m_buf += "<cols><col min=\"1\" max=\"" + std::to_string(columns)
                     + "\" width=\"18\" customWidth=\"1\"/></cols>";
        m_buf += "<sheetData>";
    }

    void beginRow()
    {
        ++m_row;
        m_col = 0;
        m_rowRef = std::to_string(m_row);
        m_buf += "<row r=\"" + m_rowRef + "\">";
    }

    void endRow()
    {
        m_buf += "</row>";
        if (m_buf.size() >= kFlushThreshold)
            flush();
    }

    void skipCell() { ++m_col; }

    void number(double v)
    {
        if (!std::isfinite(v)) {
            skipCell();
            return;
        }
        char num[32];
        const auto res = std::to_chars(num, num + sizeof(num), v);
        openCell(nullptr, false);
        m_buf += "><v>";
        m_buf.append(num, res.ptr);
        m_buf += "</v></c>";
    }

    void boolean(bool v)
    {
        openCell("b", false);
        m_buf += v ? "><v>1</v></c>" : "><v>0</v></c>";
    }

    void text(const QString &s, bool bold)
    {
        if (s.isEmpty()) {
            skipCell();
            return;
        }
        openCell("inlineStr", bold);
        m_buf += "><is><t xml:space=\"preserve\">";
        appendEscaped(m_buf, s);
        m_buf += "</t></is></c>";
    }

    void value(const QVariant &v, bool bold)
    {
        switch (v.typeId()) {
        case QMetaType::Bool:
            boolean(v.toBool());
            break;
        case QMetaType::Int: case QMetaType::UInt: case QMetaType::LongLong:
        case QMetaType::ULongLong: case QMetaType::Double: case QMetaType::Float:
            if (!bold) {
                number(v.toDouble());
                break;
            }
            [[fallthrough]];
        default:
            text(v.toString(), bold);
        }
    }

    void finish()
    {
        m_buf += "</sheetData></worksheet>";
        flush();
    }

private:
    void openCell(const char *type, bool bold)
    {
        m_buf += "<c r=\"";
        m_buf += m_letters[size_t(m_col++)];
        m_buf += m_rowRef;
        m_buf += '"';
        if (type) {
            m_buf += " t=\"";
            m_buf += type;
            m_buf += '"';
        }
        if (bold)
            m_buf += " s=\"1\"";
    }

    void flush()
    {
        m_zip.write(m_buf.data(), m_buf.size());
        m_buf.clear();
    }

    ZipWriter &m_zip;
    std::vector<std::string> m_letters;
    std::string m_buf;
    std::string m_rowRef;
    int m_row = 0;
    int m_col = 0;
};

void writeDataSheet(SheetXml &xml, const DataFrame &df)
{
    const QStringList names = df.columnNames();
    std::vector<const QVector<double> *> columns;
    for (const QString &name : names)
        columns.push_back(&df.columnRef(name));

    xml.beginRow();
    for (const QString &name : names)
        xml.text(name, true);
    xml.endRow();

    const int rows = df.rowCount();
    for (int r = 0; r < rows; ++r) {
        xml.beginRow();
        for (const auto *col : columns) {
            if (r < col->size())
                xml.number((*col)[r]);
            else
                xml.skipCell();
        }
        xml.endRow();
    }
}

void writeRowsSheet(SheetXml &xml, const QList<QVariantList> &rows)
{
    for (int r = 0; r < rows.size(); ++r) {
        xml.beginRow();
        for (const QVariant &v : rows[r])
            xml.value(v, r == 0);
        xml.endRow();
    }
}

QStringList uniqueSheetNames(const QVector<ExcelSheet> &sheets)
{
    QStringList names;
    QSet<QString> seen;
    for (int i = 0; i < sheets.size(); ++i) {
        QString base = sheets[i].name;
        for (QChar bad : QStringLiteral("[]:*?/\\"))
            base.replace(bad, QLatin1Char('_'));
        base = base.trimmed();
        while (base.startsWith(QLatin1Char('\'')))
            base.remove(0, 1);
        while (base.endsWith(QLatin1Char('\'')))
            base.chop(1);
        if (base.isEmpty())
            base = QStringLiteral("Sheet%1").arg(i + 1);
        base = base.left(31);

        QString name = base;
        for (int n = 2; seen.contains(name.toLower()); ++n) {
            const QString suffix = QStringLiteral(" (%1)").arg(n);
            name = base.left(31 - suffix.size()) + suffix;
        }
        seen.insert(name.toLower());
        names << name;
    }
    return names;
}

QString escapedAttr(const QString &s)
{
    std::string out;
    appendEscaped(out, s);
    return QString::fromStdString(out);
}

} // namespace

void saveExcelFile(const QString &filePath, const QVector<ExcelSheet> &sheets)
{
    if (sheets.isEmpty())
        fail(QStringLiteral("Nothing to export."));

    for (const ExcelSheet &sheet : sheets) {
        const qsizetype rows = sheet.data.isEmpty() ? sheet.rows.size()
                                                    : qsizetype(sheet.data.rowCount()) + 1;
        qsizetype columns = sheet.data.columnCount();
        for (const QVariantList &row : sheet.rows)
            columns = qMax(columns, row.size());
        if (rows > kMaxExcelRows)
            fail(QStringLiteral("Sheet '%1' has %2 rows, but Excel allows at most %3. "
                                "Please save the data as CSV instead.")
                     .arg(sheet.name).arg(rows).arg(kMaxExcelRows));
        if (columns > kMaxExcelColumns)
            fail(QStringLiteral("Sheet '%1' has %2 columns, but Excel allows at most %3. "
                                "Please save the data as CSV instead.")
                     .arg(sheet.name).arg(columns).arg(kMaxExcelColumns));
    }

    const QStringList names = uniqueSheetNames(sheets);
    const int count = int(sheets.size());

    QByteArray contentTypes =
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
        "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
        "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
        "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
        "<Override PartName=\"/xl/workbook.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/>"
        "<Override PartName=\"/xl/styles.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml\"/>";
    QByteArray workbook =
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
        "<workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" "
        "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\"><sheets>";
    QByteArray workbookRels =
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">";
    for (int i = 1; i <= count; ++i) {
        const QByteArray n = QByteArray::number(i);
        contentTypes += "<Override PartName=\"/xl/worksheets/sheet" + n + ".xml\" ContentType=\""
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml\"/>";
        workbook += "<sheet name=\"" + escapedAttr(names[i - 1]).toUtf8() + "\" sheetId=\"" + n
                    + "\" r:id=\"rId" + n + "\"/>";
        workbookRels += "<Relationship Id=\"rId" + n + "\" Type=\"http://schemas.openxmlformats.org/"
                        "officeDocument/2006/relationships/worksheet\" Target=\"worksheets/sheet" + n + ".xml\"/>";
    }
    contentTypes += "</Types>";
    workbook += "</sheets></workbook>";
    workbookRels += "<Relationship Id=\"rId" + QByteArray::number(count + 1) + "\" Type=\""
                    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles\" "
                    "Target=\"styles.xml\"/></Relationships>";

    const QByteArray rootRels =
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
        "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/"
        "relationships/officeDocument\" Target=\"xl/workbook.xml\"/></Relationships>";

    // Style 0 = default, style 1 = bold (header rows).
    const QByteArray styles =
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
        "<styleSheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\">"
        "<fonts count=\"2\"><font><sz val=\"11\"/><name val=\"Calibri\"/></font>"
        "<font><b/><sz val=\"11\"/><name val=\"Calibri\"/></font></fonts>"
        "<fills count=\"2\"><fill><patternFill patternType=\"none\"/></fill>"
        "<fill><patternFill patternType=\"gray125\"/></fill></fills>"
        "<borders count=\"1\"><border><left/><right/><top/><bottom/><diagonal/></border></borders>"
        "<cellStyleXfs count=\"1\"><xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"0\"/></cellStyleXfs>"
        "<cellXfs count=\"2\"><xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"0\" xfId=\"0\"/>"
        "<xf numFmtId=\"0\" fontId=\"1\" fillId=\"0\" borderId=\"0\" xfId=\"0\" applyFont=\"1\"/></cellXfs>"
        "<cellStyles count=\"1\"><cellStyle name=\"Normal\" xfId=\"0\" builtinId=\"0\"/></cellStyles>"
        "</styleSheet>";

    ZipWriter zip(filePath);
    zip.addEntry(QStringLiteral("[Content_Types].xml"), contentTypes);
    zip.addEntry(QStringLiteral("_rels/.rels"), rootRels);
    zip.addEntry(QStringLiteral("xl/workbook.xml"), workbook);
    zip.addEntry(QStringLiteral("xl/_rels/workbook.xml.rels"), workbookRels);
    zip.addEntry(QStringLiteral("xl/styles.xml"), styles);

    for (int i = 0; i < count; ++i) {
        const ExcelSheet &sheet = sheets[i];
        const bool isData = !sheet.data.isEmpty();
        int columns = sheet.data.columnCount();
        for (const QVariantList &row : sheet.rows)
            columns = qMax(columns, int(row.size()));

        zip.beginEntry(QStringLiteral("xl/worksheets/sheet%1.xml").arg(i + 1));
        SheetXml xml(zip, columns, isData);
        if (isData)
            writeDataSheet(xml, sheet.data);
        else
            writeRowsSheet(xml, sheet.rows);
        xml.finish();
        zip.endEntry();
    }

    zip.finish();
}

} // namespace FileLoaders
