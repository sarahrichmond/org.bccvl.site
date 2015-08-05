from decimal import Decimal
import json
import re
import csv

class DecimalJSONEncoder(json.JSONEncoder):

    def default(self, o):
        """ converts Decimal to something the json module can serialize.
        Usually with python 2.7 float rounding this creates nice representations
        of numbers, but there might be cases where rounding may cause problems.
        E.g. if precision required is higher than default float rounding.
        """
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalJSONEncoder, self).default(o)


class Period(object):
    """
    Parse DCMI period strings and provide values as attributes.

    Format set period values as valid DCMI period.

    FIXME: currently uses date strings as is and does not try to interpret them.
           the same for formatting. date's have to be given as properly formatted strings.
    """

    start = end = scheme = name = None

    def __init__(self, str):
        '''
        TODO: assumes str is unicode
        '''
        sm = re.search(r'start=(.*?);', str)
        if sm:
            self.start = sm.group(1)
        sm = re.search(r'scheme=(.*?);', str)
        if sm:
            self.scheme = sm.group(1)
        sm = re.search(r'end=(.*?);', str)
        if sm:
            self.end = sm.group(1)
        sm = re.search(r'name=(.*?);', str)
        if sm:
            self.name = sm.group(1)

    def __unicode__(self):
        parts = []
        if self.start:
            parts.append("start=%s;" % self.start)
        if self.end:
            parts.append("end=%s;" % self.end)
        if self.name:
            parts.append("name=%s;" % self.name)
        if self.scheme:
            parts.append("scheme=%s;" % self.scheme)
        return u' '.join(parts)
        
"""
Validate the coordinates in the CSV file, and return a list of issues found if any.
"""
def ValidateData(csvFile, longitudeName = 'lon', latitudeName = 'lat'):
    csv_reader = csv.DictReader(csvFile, skipinitialspace = True)
    csv_reader.fieldnames = [f.strip() for f in csv_reader.fieldnames]
    headers = csv_reader.fieldnames
    issues = []
    line = 1
    err_fmt = "Line %d: %s"
        
    # check for longitude and latitude columns
    if not longitudeName in headers or not latitudeName in headers:
        # Don't have the coordinate columns
        issues.append(err_fmt %(line, "Missing 'lon' or/and 'lat' column(s)"))
        return issues
         
    # Validate the number of columns and coordinates
    num_cols = len(headers)
    for row in csv_reader:
        line += 1       
        # check that the row has the correct number of columns
        if len(row) != num_cols:
            msg = "Incorrect number of columns (%d columns found but %d expected)" %(len(row), num_cols)
            issues.append(err_fmt %(line, msg))
            continue
        try:
            # check that the coordinates are valid numbers
            lng_f = float(row[longitudeName])
            lat_f = float(row[latitudeName])
        except:
            msg = "Invalid coordinate data (lat='%s', lon='%s')" %(row[latitudeName], row[longitudeName])
            issues.append(err_fmt %(line, msg))
            continue
    return issues