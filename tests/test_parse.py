import pandas as pd

import goodtables
from goodtables_pandas.parse import parse_string, parse_number, parse_integer

def test_parses_string():
    x = pd.Series(['', 'a', 'nan', float('nan')])
    expected = x
    parsed = parse_string(x)
    pd.testing.assert_series_equal(parsed, expected)

def test_parses_valid_email() -> None:
    x = pd.Series([
        'a@z.com',
        'a.b@z.com', # inner .
        'a@z-z.com', # inner -
        "azAZ09!#$%&'*+-/=?^_`{|}~@azAZ09.com", # unquoted special characters
        '0123456789012345678901234567890123456789012345678901234567890123@z.com', # local = 64 characters
        'a@012345678901234567890123456789012345678901234567890123456789012.com', # label = 63 characters
    ])
    pd.testing.assert_series_equal(x, parse_string(x, format='email'))

def test_rejects_invalid_email() -> None:
    x = pd.Series([
        ' a@z.com', # leading whitespace
        'a @z.com', # inner whitespace
        'a@z.com ', # trailing whitespace
        'az.com', # missing @
        'a@@z.com', # multiple @
        '.a@z.com', # start .
        'a.@z.com', # end .
        'a..b@z.com', # consecutive .
        'a:b@z.com', # unquoted special character
        'a@-z.com', # start -
        'a@z-.com', # end -
        'a@.z', # empty label
        'a@z.', # empty label
        'a@z..', # empty label
        'a@z_z.com', # invalid character
        '01234567890123456789012345678901234567890123456789012345678901234@z.com', # local > 64 characters
        'a@0123456789012345678901234567890123456789012345678901234567890123.com', # label > 63 characters
    ])
    error = parse_string(x, format='email')
    pd.testing.assert_series_equal(x, pd.Series(error._message_substitutions['values']))

def test_rejects_unsupported_email() -> None:
    x = pd.Series([
        'a(comment)@z.com', # comment in local
        '(comment)a@z.com', # comment in local
        'a@(comment)z.com', # comment in domain
        'a@z(comment).com', # comment in domain
        'a@z.com(comment)', # comment in domain
        'a@[192.168.2.1]', # IP address literal in brackets
        'a@[IPv6:2001:db8::1]', # IP address literal in brackets
        '"a:b"@z.com', # quoted special character
        '".a"@z.com', # quoted start .
        '"a."@z.com', # quoted end .
        '"a..b"@z.com', # quoted consecutive .
        'a@ουτοπία.δπθ.gr', # non-ascii domain name
    ])
    error = parse_string(x, format='email')
    pd.testing.assert_series_equal(x, pd.Series(error._message_substitutions['values']))

def test_parses_valid_uri() -> None:
    x = pd.Series([
        'https://john.doe@www.example.com:123/forum/questions/?tag=work&order=new#top',
        'ldap://[2001:db8::7]/c=GB?objectClass?one',
        'mailto:John.Doe@example.com',
        'news:comp.infosystems.www.servers.unix',
        'tel:+1-816-555-1212',
        'telnet://192.0.2.16:80/',
        'urn:oasis:names:specification:docbook:dtd:xml:4.1.2',
        'https://example.com/path/resource.txt#fragment',
        'azAZ+.-://foo.bar', # permitted special characters in scheme
    ])
    pd.testing.assert_series_equal(x, parse_string(x, format='uri'))

def test_rejects_invalid_uri() -> None:
    x = pd.Series([
        ' http://foo.bar', # leading whitespace
        'http://foo.bar ', # trailing whitespace
        'http:// foo.bar', # inner whitespace
        'http://', # scheme only
        'foo.bar', # no scheme
        '0http://foo.bar', # scheme start not a letter
        'http:/foo.bar', # single slash
        'http_://foo.bar', # invalid scheme character
        'http//foo.bar', # no colon
    ])
    error = parse_string(x, format='email')
    pd.testing.assert_series_equal(x, pd.Series(error._message_substitutions['values']))

def test_parses_valid_binary() -> None:
    x = pd.Series([
        'YW55' # 4
        'YW55IGNh', # 8
        'YW55IGNhcm5h', # 12
        'YW55IGNhcm5=', # trailing =
        'YW55IGNhcm==', # trailing ==
        ' YW55IGN hcm = = ', # whitespace
        'YW55IGNhcm+/', # special characters
    ])
    pd.testing.assert_series_equal(x, parse_string(x, format='binary'))

def test_rejects_invalid_binary() -> None:
    x = pd.Series([
        'YW5', # incorrect padding
        'YW55IGNh=', # incorrect padding
        'YW55IGNhcm5h==', # incorrect padding
        'YW55IGNhcm.?', # invalid characters
    ])
    error = parse_string(x, format='email')
    pd.testing.assert_series_equal(x, pd.Series(error._message_substitutions['values']))

def test_parses_valid_uuid() -> None:
    x = pd.Series([
        '00000000-0000-0000-0000-000000000000',
        '00112233-4455-6677-8899-aabbccddeeff', # full character range
        '123e4567-e89b-12d3-a456-426614174000',
        '123E4567-E89B-12D3-A456-426614174000', # uppercase
    ])
    pd.testing.assert_series_equal(x, parse_string(x, format='uuid'))

def test_rejects_invalid_uuid() -> None:
    x = pd.Series([
        '00000000000000000000000000000000', # missing dashes
        ' 00000000-0000-0000-0000-000000000000', # leading whitespace
        '00000000-0000-0000-0000-000000000000 ', # trailing whitespace
        '00000000-0000- 0000-0000-000000000000', # inner whitespace
        '00112233-4455-6677-8899-aabbccddeegg', # characters out of range (g)
        '00112233-4455-6677-8899-aabbccddee', # wrong length
    ])
    error = parse_string(x, format='email')
    pd.testing.assert_series_equal(x, pd.Series(error._message_substitutions['values']))

def test_parses_valid_number() -> None:
    df = pd.DataFrame([
        ('nan', float('nan')),
        ('+nan', float('nan')),
        ('-nan', float('nan')),
        ('NaN', float('nan')),
        ('inf', float('inf')),
        ('+inf', float('inf')),
        ('-inf', float('-inf')),
        ('INF', float('inf')),
        # NOTE: Python supports 'infinity', Table Schema only supports 'inf'
        # https://docs.python.org/3.8/library/decimal.html
        ('infinity', float('inf')),
        ('1', 1.0),
        ('+1', 1.0),
        ('-1', -1.0),
        ('01', 1.0),
        ('-01', -1.0),
        ('1.', 1),
        ('1.000', 1.0),
        ('1.23', 1.23),
        ('+1.23', 1.23),
        ('-1.23', -1.23),
        ('.1', 0.1),
        ('+.1', 0.1),
        ('-.1', -0.1),
        ('1e2', 1e2),
        ('1E2', 1e2),
        ('+1e2', 1e2),
        ('-1e2', -1e2),
        ('1e2', 1e2),
        ('1e+2', 1e2),
        ('1e-2', 1e-2),
        ('.1e2', .1e2),
        ('1.e2', 1e2),
        ('1.2e2', 1.2e2),
        ('0e2', 0e2),
        ('1e23', 1e23),
    ])
    pd.testing.assert_series_equal(parse_number(df[0]), df[1], check_names=False)

def test_rejects_invalid_number() -> None:
    x = pd.Series([
        'NA',
        'nan1',
        '++1',
        '--1',
        '1+',
        '1e2+1',
        'e2',
        '1e'
    ])
    error = parse_number(x)
    pd.testing.assert_series_equal(x, pd.Series(error._message_substitutions['values']))

def test_parses_valid_number_with_custom_characters() -> None:
    df = pd.DataFrame([
        ('1 234', 1234.0),
        ('1 234,56', 1234.56),
        ('1 234 567,89', 1234567.89),
        ('1,23', 1.23),
        ('+1,23', 1.23),
        ('-1,23', -1.23),
        (',1', 0.1),
        ('+,1', 0.1),
        ('-,1', -0.1),
        (',1e2', .1e2),
    ])
    parsed = parse_number(df[0], decimalChar=',', groupChar=' ')
    pd.testing.assert_series_equal(parsed, df[1], check_names=False)
    df = pd.DataFrame([
        ('1,,234', 1234.0),
        ('1,,234..56', 1234.56),
        ('1,,234,,567..89', 1234567.89),
        ('1..23', 1.23),
        ('+1..23', 1.23),
        ('-1..23', -1.23),
        ('..1', 0.1),
        ('+..1', 0.1),
        ('-..1', -0.1),
        ('..1e2', .1e2),
    ])
    parsed = parse_number(df[0], decimalChar='..', groupChar=',,')
    pd.testing.assert_series_equal(parsed, df[1], check_names=False)

def test_parses_valid_number_with_text():
    df = pd.DataFrame([
        ('$nan', float('nan')),
        ('EUR NaN', float('nan')),
        ('inf%', float('inf')),
        ('€INF', float('inf')),
        ('$Inf', float('inf')),
        ('EUR -inf', float('-inf')),
        ('-INF %', float('-inf')),
        ('€-Inf', float('-inf')),
        ('$1+', 1.0),
        ('$+1', 1.0),
        ('-1 USD ', -1.0),
        ('1.23%', 1.23),
        ('EUR +1.23', 1.23),
        ('$ -1.23 USD', -1.23),
        ('.1%', 0.1),
        ('Total: +.1', 0.1),
        ('** -.1 **', -0.1),
        ('$1e2', 1e2),
        ('1E2%', 1e2),
        ('$ +1e2 USD', 1e2),
        ('Total: -1e2', -1e2),
        ('1e2%', 1e2),
        ('EUR 1e+2', 1e2),
        ('E1e-2', 1e-2),
        ('.1e2E', .1e2),
        ('E 0e2.1', 0e2),
        ('E 0e2-1', 0e2),
        ('E 0e2+1', 0e2),
        ('1e23E', 1e23),
    ])
    parsed = parse_number(df[0], bareNumber=False)
    pd.testing.assert_series_equal(parsed, df[1], check_names=False)

def test_parses_valid_integer() -> None:
    df = pd.DataFrame([
        ('1', 1),
        ('+1', 1),
        ('-1', -1),
        ('001', 1),
        ('1234', 1234)
    ])
    parsed = parse_integer(df[0])
    pd.testing.assert_series_equal(parsed, df[1].astype('Int64'), check_names=False)

def test_rejects_invalid_integer() -> None:
    x = pd.Series([
        '1+',
        '1-',
        '1.23',
        '1.',
        '1.0',
        '++1',
        'nan',
        'inf',
    ])
    error = parse_integer(x)
    pd.testing.assert_series_equal(x, pd.Series(error._message_substitutions['values']))

def test_parses_valid_integer_with_text() -> None:
    df = pd.DataFrame([
        ('$1+', 1),
        ('$+1', 1),
        ('-1 USD ', -1),
        ('123%', 123),
        ('EUR +123', 123),
        ('$ -123 USD', -123),
        ('Total: +1', 1),
        ('** -1 **', -1)
    ])
    parsed = parse_integer(df[0], bareNumber=False)
    pd.testing.assert_series_equal(parsed, df[1].astype('Int64'), check_names=False)

def test_rejects_ambiguous_integer_with_text() -> None:
    x = pd.Series([
        '1.2',
        '1e2',
        '1+2',
        '1 2',
    ])
    error = parse_integer(x, bareNumber=False)
    pd.testing.assert_series_equal(x, pd.Series(error._message_substitutions['values']))
