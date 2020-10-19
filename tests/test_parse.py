import datetime

import pandas as pd
import pytest

import goodtables_pandas.options as OPTIONS
from goodtables_pandas.parse import (
    parse_boolean,
    parse_date,
    parse_datetime,
    parse_field,
    parse_geopoint,
    parse_integer,
    parse_number,
    parse_string,
    parse_year,
)


def test_parses_string():
    x = pd.Series(["", "a", "nan", float("nan")])
    expected = x
    parsed = parse_string(x)
    pd.testing.assert_series_equal(parsed, expected)


def test_parses_valid_email() -> None:
    x = pd.Series(
        [
            "a@z.com",
            "a.b@z.com",  # inner .
            "a@z-z.com",  # inner -
            "azAZ09!#$%&'*+-/=?^_`{|}~@azAZ09.com",  # unquoted special characters
            # local = 64 characters
            "0123456789012345678901234567890123456789012345678901234567890123@z.com",
            # label = 63 characters
            "a@012345678901234567890123456789012345678901234567890123456789012.com",
        ]
    )
    pd.testing.assert_series_equal(x, parse_string(x, format="email"))


def test_rejects_invalid_email() -> None:
    x = pd.Series(
        [
            " a@z.com",  # leading whitespace
            "a @z.com",  # inner whitespace
            "a@z.com ",  # trailing whitespace
            "az.com",  # missing @
            "a@@z.com",  # multiple @
            ".a@z.com",  # start .
            "a.@z.com",  # end .
            "a..b@z.com",  # consecutive .
            "a:b@z.com",  # unquoted special character
            "a@-z.com",  # start -
            "a@z-.com",  # end -
            "a@.z",  # empty label
            "a@z.",  # empty label
            "a@z..",  # empty label
            "a@z_z.com",  # invalid character
            # local > 64 characters
            "01234567890123456789012345678901234567890123456789012345678901234@z.com",
            # label > 63 characters
            "a@0123456789012345678901234567890123456789012345678901234567890123.com",
        ]
    )
    error = parse_string(x, format="email")
    pd.testing.assert_series_equal(x, pd.Series(error._message_substitutions["values"]))


def test_rejects_unsupported_email() -> None:
    x = pd.Series(
        [
            "a(comment)@z.com",  # comment in local
            "(comment)a@z.com",  # comment in local
            "a@(comment)z.com",  # comment in domain
            "a@z(comment).com",  # comment in domain
            "a@z.com(comment)",  # comment in domain
            "a@[192.168.2.1]",  # IP address literal in brackets
            "a@[IPv6:2001:db8::1]",  # IP address literal in brackets
            '"a:b"@z.com',  # quoted special character
            '".a"@z.com',  # quoted start .
            '"a."@z.com',  # quoted end .
            '"a..b"@z.com',  # quoted consecutive .
            "a@ουτοπία.δπθ.gr",  # non-ascii domain name
        ]
    )
    error = parse_string(x, format="email")
    pd.testing.assert_series_equal(x, pd.Series(error._message_substitutions["values"]))


def test_parses_valid_uri() -> None:
    x = pd.Series(
        [
            "https://john.doe@www.example.com:123/questions/?tag=work&order=new#top",
            "ldap://[2001:db8::7]/c=GB?objectClass?one",
            "mailto:John.Doe@example.com",
            "news:comp.infosystems.www.servers.unix",
            "tel:+1-816-555-1212",
            "telnet://192.0.2.16:80/",
            "urn:oasis:names:specification:docbook:dtd:xml:4.1.2",
            "https://example.com/path/resource.txt#fragment",
            "azAZ+.-://foo.bar",  # permitted special characters in scheme
        ]
    )
    pd.testing.assert_series_equal(x, parse_string(x, format="uri"))


def test_rejects_invalid_uri() -> None:
    x = pd.Series(
        [
            " http://foo.bar",  # leading whitespace
            "http://foo.bar ",  # trailing whitespace
            "http:// foo.bar",  # inner whitespace
            "http://",  # scheme only
            "foo.bar",  # no scheme
            "0http://foo.bar",  # scheme start not a letter
            "http:/foo.bar",  # single slash
            "http_://foo.bar",  # invalid scheme character
            "http//foo.bar",  # no colon
        ]
    )
    error = parse_string(x, format="email")
    pd.testing.assert_series_equal(x, pd.Series(error._message_substitutions["values"]))


def test_parses_valid_binary() -> None:
    x = pd.Series(
        [
            "YW55" "YW55IGNh",  # 4  # 8
            "YW55IGNhcm5h",  # 12
            "YW55IGNhcm5=",  # trailing =
            "YW55IGNhcm==",  # trailing ==
            " YW55IGN hcm = = ",  # whitespace
            "YW55IGNhcm+/",  # special characters
        ]
    )
    pd.testing.assert_series_equal(x, parse_string(x, format="binary"))


def test_rejects_invalid_binary() -> None:
    x = pd.Series(
        [
            "YW5",  # incorrect padding
            "YW55IGNh=",  # incorrect padding
            "YW55IGNhcm5h==",  # incorrect padding
            "YW55IGNhcm.?",  # invalid characters
        ]
    )
    error = parse_string(x, format="email")
    pd.testing.assert_series_equal(x, pd.Series(error._message_substitutions["values"]))


def test_parses_valid_uuid() -> None:
    x = pd.Series(
        [
            "00000000-0000-0000-0000-000000000000",
            "00112233-4455-6677-8899-aabbccddeeff",  # full character range
            "123e4567-e89b-12d3-a456-426614174000",
            "123E4567-E89B-12D3-A456-426614174000",  # uppercase
        ]
    )
    pd.testing.assert_series_equal(x, parse_string(x, format="uuid"))


def test_rejects_invalid_uuid() -> None:
    x = pd.Series(
        [
            "00000000000000000000000000000000",  # missing dashes
            " 00000000-0000-0000-0000-000000000000",  # leading whitespace
            "00000000-0000-0000-0000-000000000000 ",  # trailing whitespace
            "00000000-0000- 0000-0000-000000000000",  # inner whitespace
            "00112233-4455-6677-8899-aabbccddeegg",  # characters out of range (g)
            "00112233-4455-6677-8899-aabbccddee",  # wrong length
        ]
    )
    error = parse_string(x, format="email")
    pd.testing.assert_series_equal(x, pd.Series(error._message_substitutions["values"]))


@pytest.mark.parametrize("raise_first", [True, False])
def test_parses_valid_number(raise_first) -> None:
    OPTIONS.raise_first_invalid_number = raise_first
    df = pd.DataFrame(
        [
            ("nan", float("nan")),
            ("+nan", float("nan")),
            ("-nan", float("nan")),
            ("NaN", float("nan")),
            ("inf", float("inf")),
            ("+inf", float("inf")),
            ("-inf", float("-inf")),
            ("INF", float("inf")),
            # NOTE: Python supports 'infinity', Table Schema only supports 'inf'
            # https://docs.python.org/3.8/library/decimal.html
            ("infinity", float("inf")),
            ("1", 1.0),
            ("+1", 1.0),
            ("-1", -1.0),
            ("01", 1.0),
            ("-01", -1.0),
            ("1.", 1),
            ("1.000", 1.0),
            ("1.23", 1.23),
            ("+1.23", 1.23),
            ("-1.23", -1.23),
            (".1", 0.1),
            ("+.1", 0.1),
            ("-.1", -0.1),
            ("1e2", 1e2),
            ("1E2", 1e2),
            ("+1e2", 1e2),
            ("-1e2", -1e2),
            ("1e2", 1e2),
            ("1e+2", 1e2),
            ("1e-2", 1e-2),
            (".1e2", 0.1e2),
            ("1.e2", 1e2),
            ("1.2e2", 1.2e2),
            ("0e2", 0e2),
            ("1e23", 1e23),
        ]
    )
    pd.testing.assert_series_equal(parse_number(df[0]), df[1], check_names=False)


def test_rejects_invalid_number() -> None:
    x = pd.Series(["NA", "nan1", "++1", "--1", "1+", "1e2+1", "e2", "1e"])
    error = parse_number(x)
    pd.testing.assert_series_equal(x, pd.Series(error._message_substitutions["values"]))


def test_parses_valid_number_with_custom_characters() -> None:
    df = pd.DataFrame(
        [
            ("1 234", 1234.0),
            ("1 234,56", 1234.56),
            ("1 234 567,89", 1234567.89),
            ("1,23", 1.23),
            ("+1,23", 1.23),
            ("-1,23", -1.23),
            (",1", 0.1),
            ("+,1", 0.1),
            ("-,1", -0.1),
            (",1e2", 0.1e2),
        ]
    )
    parsed = parse_number(df[0], decimalChar=",", groupChar=" ")
    pd.testing.assert_series_equal(parsed, df[1], check_names=False)
    df = pd.DataFrame(
        [
            ("1,,234", 1234.0),
            ("1,,234..56", 1234.56),
            ("1,,234,,567..89", 1234567.89),
            ("1..23", 1.23),
            ("+1..23", 1.23),
            ("-1..23", -1.23),
            ("..1", 0.1),
            ("+..1", 0.1),
            ("-..1", -0.1),
            ("..1e2", 0.1e2),
        ]
    )
    parsed = parse_number(df[0], decimalChar="..", groupChar=",,")
    pd.testing.assert_series_equal(parsed, df[1], check_names=False)


def test_parses_valid_number_with_text():
    df = pd.DataFrame(
        [
            ("$nan", float("nan")),
            ("EUR NaN", float("nan")),
            ("inf%", float("inf")),
            ("€INF", float("inf")),
            ("$Inf", float("inf")),
            ("EUR -inf", float("-inf")),
            ("-INF %", float("-inf")),
            ("€-Inf", float("-inf")),
            ("$1+", 1.0),
            ("$+1", 1.0),
            ("-1 USD ", -1.0),
            ("1.23%", 1.23),
            ("EUR +1.23", 1.23),
            ("$ -1.23 USD", -1.23),
            (".1%", 0.1),
            ("Total: +.1", 0.1),
            ("** -.1 **", -0.1),
            ("$1e2", 1e2),
            ("1E2%", 1e2),
            ("$ +1e2 USD", 1e2),
            ("Total: -1e2", -1e2),
            ("1e2%", 1e2),
            ("EUR 1e+2", 1e2),
            ("E1e-2", 1e-2),
            (".1e2E", 0.1e2),
            ("1e23E", 1e23),
        ]
    )
    parsed = parse_number(df[0], bareNumber=False)
    pd.testing.assert_series_equal(parsed, df[1], check_names=False)


def test_rejects_ambiguous_number_with_text() -> None:
    x = pd.Series(["$nan inf", "E 0e2.1", "E 0e2-1", "E 0e2+1", "1e23E2"])
    error = parse_number(x, bareNumber=False)
    pd.testing.assert_series_equal(x, pd.Series(error._message_substitutions["values"]))


@pytest.mark.parametrize("raise_first", [True, False])
def test_parses_valid_integer(raise_first) -> None:
    OPTIONS.raise_first_invalid_integer = raise_first
    df = pd.DataFrame([("1", 1), ("+1", 1), ("-1", -1), ("001", 1), ("1234", 1234)])
    parsed = parse_integer(df[0])
    pd.testing.assert_series_equal(parsed, df[1].astype("Int64"), check_names=False)


def test_rejects_invalid_integer() -> None:
    x = pd.Series(
        [
            "1+",
            "1-",
            "1.23",
            "1.",
            "1.0",
            "++1",
            "nan",
            "inf",
        ]
    )
    error = parse_integer(x)
    pd.testing.assert_series_equal(x, pd.Series(error._message_substitutions["values"]))


def test_parses_valid_integer_with_text() -> None:
    df = pd.DataFrame(
        [
            ("$1+", 1),
            ("$+1", 1),
            ("-1 USD ", -1),
            ("123%", 123),
            ("EUR +123", 123),
            ("$ -123 USD", -123),
            ("Total: +1", 1),
            ("** -1 **", -1),
        ]
    )
    parsed = parse_integer(df[0], bareNumber=False)
    pd.testing.assert_series_equal(parsed, df[1].astype("Int64"), check_names=False)


def test_rejects_ambiguous_integer_with_text() -> None:
    x = pd.Series(
        [
            "1.2",
            "1e2",
            "1+2",
            "1 2",
        ]
    )
    error = parse_integer(x, bareNumber=False)
    pd.testing.assert_series_equal(x, pd.Series(error._message_substitutions["values"]))


def test_parses_valid_boolean() -> None:
    trueValues = "true", "True", "TRUE", "1"
    falseValues = "false", "False", "FALSE", "0"
    df = pd.DataFrame(
        {
            0: trueValues + falseValues,
            1: [True] * len(trueValues) + [False] * len(falseValues),
        }
    )
    parsed = parse_boolean(df[0], trueValues=trueValues, falseValues=falseValues)
    pd.testing.assert_series_equal(parsed, df[1].astype("Int64"), check_names=False)


def test_rejects_invalid_boolean() -> None:
    trueValues = "true", "True", "TRUE", "1"
    falseValues = "false", "False", "FALSE", "0"
    x = pd.Series(
        [
            "00",
            "folse",
            "01",
            "TRUe",
        ]
    )
    error = parse_boolean(x, trueValues=trueValues, falseValues=falseValues)
    pd.testing.assert_series_equal(x, pd.Series(error._message_substitutions["values"]))


def test_parses_valid_date() -> None:
    df = pd.DataFrame(
        [
            ("2010-01-01", pd.Timestamp(2010, 1, 1)),
            ("2020-12-31", pd.Timestamp(2020, 12, 31)),
        ]
    )
    parsed = parse_date(df[0])
    pd.testing.assert_series_equal(parsed, df[1], check_names=False)
    parsed = parse_date(df[0], format="%Y-%m-%d")
    pd.testing.assert_series_equal(parsed, df[1], check_names=False)
    df = pd.DataFrame(
        [
            ("01/01/10", pd.Timestamp(2010, 1, 1)),
            ("31/12/20", pd.Timestamp(2020, 12, 31)),
        ]
    )
    parsed = parse_date(df[0], format="%d/%m/%y")
    pd.testing.assert_series_equal(parsed, df[1], check_names=False)


def test_rejects_invalid_date() -> None:
    x = pd.Series(
        [
            "2010-02-29",  # non-existent leap year
            "2020-12-32",  # day out of range
            "2020-13-31",  # month out of range
            "2020-00-31",  # zero month
            "2020-12-00",  # zero day
            "31/12/20",  # wrong format
        ]
    )
    error = parse_date(x)
    pd.testing.assert_series_equal(x, pd.Series(error._message_substitutions["values"]))


@pytest.mark.xfail(reason="pd.Timestamp is limited to ~584 year range")
def test_parses_valid_outofrange_dates() -> None:
    df = pd.DataFrame(
        [
            ("1676-01-01", datetime.date(1676, 1, 1)),
            ("2263-12-31", datetime.date(2263, 12, 31)),
        ]
    )
    parsed = parse_date(df[0])
    assert (parsed == df[1]).all()


def test_parses_valid_datetime() -> None:
    df = pd.DataFrame(
        [
            ("2010-01-01T01:02:03Z", pd.Timestamp(2010, 1, 1, 1, 2, 3).tz_localize(0)),
            (
                "2020-12-31T12:34:56Z",
                pd.Timestamp(2020, 12, 31, 12, 34, 56).tz_localize(0),
            ),
        ]
    )
    parsed = parse_datetime(df[0])
    pd.testing.assert_series_equal(parsed, df[1], check_names=False)
    parsed = parse_datetime(df[0], format="%Y-%m-%dT%H:%M:%S%z")
    pd.testing.assert_series_equal(parsed, df[1], check_names=False)
    df = pd.DataFrame(
        [
            ("01/01/10 01:02:03", pd.Timestamp(2010, 1, 1, 1, 2, 3)),
            ("31/12/20 12:34:56", pd.Timestamp(2020, 12, 31, 12, 34, 56)),
        ]
    )
    parsed = parse_date(df[0], format="%d/%m/%y %H:%M:%S")
    pd.testing.assert_series_equal(parsed, df[1], check_names=False)


def test_rejects_invalid_datetime() -> None:
    x = pd.Series(
        [
            "2010-02-29T00:00:00Z",  # non-existent leap year
            "2020-12-32T00:00:00Z",  # day out of range
            "2020-13-31T00:00:00Z",  # month out of range
            "2020-00-31T00:00:00Z",  # zero month
            "2020-12-00T00:00:00Z",  # zero day
            "31/12/20T00:00:00Z",  # wrong format
            "2020-12-31T24:00:00Z",  # hour out of range
            "2020-12-31T00:60:00Z",  # minute out of range
        ]
    )
    error = parse_datetime(x)
    pd.testing.assert_series_equal(x, pd.Series(error._message_substitutions["values"]))


@pytest.mark.xfail(reason="pd.Timestamp wraps seconds > 59")
def test_rejects_datetime_with_outofrange_seconds() -> None:
    x = pd.Series(
        [
            "2020-12-31T00:00:61Z",  # second out of range
        ]
    )
    error = parse_datetime(x)
    pd.testing.assert_series_equal(x, pd.Series(error._message_substitutions["values"]))


def test_parses_valid_year() -> None:
    df = pd.DataFrame(
        [
            ("2020", 2020),
            ("0", 0),  # allows year 0
            ("-1", -1),  # allows years < 0
            ("10000", 10000),  # allows years > 9999
        ]
    )
    parsed = parse_year(df[0])
    pd.testing.assert_series_equal(parsed, df[1].astype("Int64"), check_names=False)


def test_rejects_invalid_year() -> None:
    x = pd.Series(
        [
            "nan",
            "x",
            "1.2",
        ]
    )
    error = parse_year(x)
    pd.testing.assert_series_equal(x, pd.Series(error._message_substitutions["values"]))


def test_parses_valid_geopoint() -> None:
    df = pd.DataFrame(
        [
            ("0.1, 2.3", (0.1, 2.3)),
            ("0.1,2.3", (0.1, 2.3)),  # no space after comma
            ("0, 1", (0.0, 1.0)),  # integer coordinates
            ("-0.1, -2.3", (-0.1, -2.3)),  # negative coordinates
            # special values (NOTE: invalid?)
            (
                "Infinity, NaN",
                (float("inf"), float("nan")),
            ),  # works in json.loads(lon|lat)
            ("inf, nan", (float("inf"), float("nan"))),  # fails in json.loads(lon|lat)
        ]
    )
    parsed = parse_geopoint(df[0])
    pd.testing.assert_series_equal(parsed, df[1], check_names=False)


def test_rejects_invalid_geopoint() -> None:
    x = pd.Series(
        [
            "0,  1",  # two spaces after comma (NOTE: valid?)
            " 0, 1 ",  # leading/trailing whitespace (NOTE: valid?)
            "0, 1, 2",  # too many coordinates
            "0",  # too few coordinates
            "x, y",  # non-numeric coordinates
        ]
    )
    error = parse_geopoint(x)
    pd.testing.assert_series_equal(x, pd.Series(error._message_substitutions["values"]))


def test_parses_valid_geopoint_array() -> None:
    df = pd.DataFrame(
        [
            ("[0.1, 2.3]", (0.1, 2.3)),
            ("[0.1,2.3]", (0.1, 2.3)),  # no space after comma
            (" [0.1, 2.3] ", (0.1, 2.3)),  # trailing/leading white space
            ("[0.1,  2.3]", (0.1, 2.3)),  # two spaces after comma
            ("[0, 1]", (0.0, 1.0)),  # integer coordinates
            ("[-0.1, -2.3]", (-0.1, -2.3)),  # negative coordinates
            # special values (NOTE: invalid?)
            ("[Infinity, NaN]", (float("inf"), float("nan"))),  # works in json.loads()
            ("[inf, nan]", (float("inf"), float("nan"))),  # fails in json.loads()
        ]
    )
    parsed = parse_geopoint(df[0], format="array")
    pd.testing.assert_series_equal(parsed, df[1], check_names=False)


def test_rejects_invalid_geopoint_array() -> None:
    x = pd.Series(
        [
            "[0, 1, 2]",  # too many coordinates
            "[0]",  # too few coordinates
            "[x, y]",  # non-numeric coordinates
            "x, y]",  # missing left bracket
            "[x, y",  # missing right bracket
            "x, y",  # missing brackets
        ]
    )
    error = parse_geopoint(x, format="array")
    pd.testing.assert_series_equal(x, pd.Series(error._message_substitutions["values"]))


def test_parses_valid_geopoint_object() -> None:
    df = pd.DataFrame(
        [
            ('{"lon": 0.1, "lat": 2.3}', (0.1, 2.3)),
            ('{"lat": 2.3, "lon": 0.1}', (0.1, 2.3)),  # lat, then lon
            ('{"lon": 0.1,"lat": 2.3}', (0.1, 2.3)),  # no space after comma
            (' {"lon": 0.1, "lat": 2.3} ', (0.1, 2.3)),  # trailing/leading white space
            ('{"lon": 0.1,  "lat": 2.3}', (0.1, 2.3)),  # two spaces after comma
            ('{"lon": 0, "lat": 1}', (0.0, 1.0)),  # integer coordinates
            ('{"lon": -0.1, "lat": -2.3}', (-0.1, -2.3)),  # negative coordinates
            # special values (NOTE: invalid?)
            (
                '{"lon": Infinity, "lat": NaN}',
                (float("inf"), float("nan")),
            ),  # works in json.loads()
            (
                '{"lon": inf, "lat": nan}',
                (float("inf"), float("nan")),
            ),  # fails in json.loads()
        ]
    )
    parsed = parse_geopoint(df[0], format="object")
    pd.testing.assert_series_equal(parsed, df[1], check_names=False)


def test_rejects_invalid_geopoint_object() -> None:
    x = pd.Series(
        [
            '{"lon": 0, "lat": 1, "z": 2}',  # too many coordinates
            '{"lon": 0}',  # too few coordinates
            '{"lon": x, "lat": y}',  # non-numeric coordinates
            '{"lon": "x", "lat": "y"}',  # non-numeric coordinates
            '{"LON": 0, "LAT": 1}',  # wrong key case
            '{"longitude": 0, "latitude": 1}',  # wrong keys
            "[0, 1]",  # array format
            "0, 1",  # default format
            '{"lon": 0, "lat": 1',  # missing right brace
        ]
    )
    error = parse_geopoint(x, format="object")
    pd.testing.assert_series_equal(x, pd.Series(error._message_substitutions["values"]))


@pytest.mark.parametrize(
    "x, field, dtype",
    [
        ("string", {"type": "string"}, "O"),
        ("foo@bar.com", {"type": "string", "format": "email"}, "O"),
        ("https://foo.bar", {"type": "string", "format": "uri"}, "O"),
        ("YW55", {"type": "string", "format": "binary"}, "O"),
        (
            "00000000-0000-0000-0000-000000000000",
            {"type": "string", "format": "uuid"},
            "O",
        ),
        ("1.0", {"type": "number"}, "float64"),
        ("1,0", {"type": "number", "decimalChar": ","}, "float64"),
        ("1 000", {"type": "number", "groupChar": " "}, "float64"),
        ("$1", {"type": "number", "bareNumber": False}, "float64"),
        ("1", {"type": "integer"}, "Int64"),
        ("$1", {"type": "integer", "bareNumber": False}, "Int64"),
        ("true", {"type": "boolean"}, "Int64"),
        ("2020-12-31", {"type": "date"}, "datetime64[ns]"),
        ("2020/12/31", {"type": "date", "format": "any"}, "datetime64[ns]"),
        ("2020/12/31", {"type": "date", "format": "%Y/%m/%d"}, "datetime64[ns]"),
        # Skip type:datetime, format:default - datetime64[ns, UTC], NaN datetime64[ns]
        (
            "2020/12/31 00:00:00",
            {"type": "datetime", "format": "any"},
            "datetime64[ns]",
        ),
        (
            "2020/12/31 00:00:00",
            {"type": "datetime", "format": "%Y/%m/%d %H:%M:%S"},
            "datetime64[ns]",
        ),
        ("2020", {"type": "year"}, "Int64"),
        ("0, 1", {"type": "geopoint"}, "O"),
        ("[0, 1]", {"type": "geopoint", "format": "array"}, "O"),
        ('{"lon": 0, "lat": 1}', {"type": "geopoint", "format": "object"}, "O"),
    ],
)
def test_propagates_null_and_maintains_dtype(x: str, field: str, dtype: str) -> None:
    print(field)
    # null only
    parsed = parse_field(pd.Series([float("nan")], dtype=str), **field)
    assert isinstance(parsed, pd.Series)
    assert parsed.isna().all()
    assert parsed.dtype == dtype
    # mixed
    parsed = parse_field(pd.Series([x, float("nan")], dtype=str), **field)
    assert isinstance(parsed, pd.Series)
    assert parsed[1:].isna().all()
    assert parsed.dtype == dtype
