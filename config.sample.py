# -*- coding: utf-8 -*-
config_page_name = ''

import configparser
import os

reader = configparser.ConfigParser()
reader.read(os.path.expanduser('~/replica.my.cnf'))
db_settings = {
    'host': 'zhwiki.analytics.db.svc.eqiad.wmflabs',
    'user': reader.get('client', 'user'),
    'password': reader.get('client', 'password'),
    'charset': 'utf8'
}
