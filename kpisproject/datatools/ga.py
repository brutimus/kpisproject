#!/usr/bin/python

import httplib2, argparse, sys, datetime, re

from apiclient.discovery import build

from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client import tools

parser = argparse.ArgumentParser(description=__doc__,
      formatter_class=argparse.RawDescriptionHelpFormatter,
      parents=[tools.argparser])

CLIENT_SECRETS = 'client_secrets.json'
MISSING_CLIENT_SECRETS_MESSAGE = '%s is missing' % CLIENT_SECRETS

FLOW = flow_from_clientsecrets(CLIENT_SECRETS,
  scope='https://www.googleapis.com/auth/analytics.readonly',
  message=MISSING_CLIENT_SECRETS_MESSAGE)

TOKEN_FILE_NAME = 'analytics.dat'

def prepare_credentials():
  storage = Storage(TOKEN_FILE_NAME)
  credentials = storage.get()
  if credentials is None or credentials.invalid:
    credentials = tools.run_flow(FLOW, storage, parser.parse_args())
  return credentials

def initialize_service():
  http = httplib2.Http()

  #Get stored credentials or run the Auth Flow if none are found
  credentials = prepare_credentials()
  http = credentials.authorize(http)

  #Construct and return the authorized Analytics Service Object
  return build('analytics', 'v3', http=http)

def get_api_query(service, table_id, day):
  """Returns a query object to retrieve data from the Core Reporting API.

  Args:
    service: The service object built by the Google API Python client library.
    table_id: str The table ID form which to retrieve data.
  """

  return service.data().ga().get(
      ids=table_id,
      start_date=day.strftime('%Y-%m-%d'),
      end_date=day.strftime('%Y-%m-%d'),
      metrics='ga:uniquePageviews,ga:pageviews,ga:avgTimeOnPage',
      dimensions='ga:pagePath',
      sort='-ga:pageviews',
      # filters='ga:pagePath=@-611175-',
      # segment='gaid::l7IGkRQVQDiZFr0GRrQKXQ', # Local
      # segment='gaid::hGNTan1pStyd0Qkwhz-shA', # Non-Local
      # segment='sessions::condition::ga:metro=@Angeles', # Local
      # segment='sessions::condition::ga:metro!@Angeles', # Non-Local
      start_index='1',
      max_results='50000')

def get_api_query_for_ids(service, table_id, start_date, end_date, ids, offset=1):
  """Returns a query object to retrieve data from the Core Reporting API.

  Args:
    service: The service object built by the Google API Python client library.
    table_id: str The table ID form which to retrieve data.
  """

  return service.data().ga().get(
      ids=table_id,
      start_date=start_date.strftime('%Y-%m-%d'),
      end_date=end_date.strftime('%Y-%m-%d'),
      metrics='ga:uniquePageviews,ga:pageviews,ga:avgTimeOnPage',
      dimensions='ga:pagePath',
      sort='-ga:pageviews',
      filters=','.join('ga:pagePath=@-%s-' % x for x in ids),
      start_index=offset,
      max_results='10000')

def dict_ga(rows):
  id_re = re.compile(r'.+-(\d{5,})-.+')
  data = {}
  for row in rows:
    ga_id = id_re.match(row[0])
    if not ga_id:
      continue
    ga_id = int(ga_id.groups()[0])
    item = data[ga_id] = data.get(ga_id, [0, 0, 0])
    iV = item[0]
    iPV = item[1]
    iTOP = item[2]
    rV = int(row[1])
    rPV = int(row[2])
    rTOP = int(float(row[3]))

    # New V
    item[0] += rV
    # New PV
    item[1] += rPV
    # New TOP (Recalculate average)
    if iTOP == 0:
      item[2] = rTOP
    elif rTOP > 0:
      item[2] = ((iPV * iTOP) + (rPV * rTOP)) / (iPV + rPV)
  return data


if __name__ == '__main__':
  print dict_ga(get_api_query(initialize_service(), 'ga:42641304', datetime.date(2014, 4, 24)).execute().get('rows'))
  # print dict_ga(get_api_query_for_ids(
  #   initialize_service(),
  #   'ga:42641304',
  #   offset=1,
  #   start_date=datetime.date(2014, 4, 1),
  #   end_date=datetime.date(2014, 5, 6),
  #   ids=['609277','611175', '610508']
  # ).execute().get('rows'))
