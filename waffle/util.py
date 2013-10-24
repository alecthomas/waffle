import datetime
import re

_parse_reltime_re = re.compile(r'([-+]?\d+)(ms|[dhms])')
_parse_reltime_units = {'s': 1, 'm': 60, 'h': 3600, 'd': 24 * 3600, 'ms': 0.001}


def parse_reltime(rt):
    """Parse a relative time string in the form 5s, 5h3m2s, etc.

    :returns: A datetime.timedelta().
    """
    if isinstance(rt, datetime.timedelta):
        return rt
    s = 0.0
    for n, u in _parse_reltime_re.findall(rt):
        s += float(n) * _parse_reltime_units[u]
    return datetime.timedelta(seconds=s)
