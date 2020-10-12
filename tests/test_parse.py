import pandas as pd

import goodtables
from goodtables_pandas.parse import parse_string

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
