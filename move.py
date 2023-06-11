# -*- coding: utf-8 -*-
import argparse
import json
import logging
import os
import re
import sys

import pymysql

os.environ['PYWIKIBOT_DIR'] = os.path.dirname(os.path.realpath(__file__))
import pywikibot

from config import config_page_name, db_settings  # pylint: disable=E0611,W0614

os.environ['TZ'] = 'UTC'


class PrcAdminMover:
    def __init__(self, config_page_name, args):
        self.args = args

        self.site = pywikibot.Site()
        self.site.login()

        self.logger = logging.getLogger('prc_admin_mover')
        formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(formatter)
        self.logger.addHandler(stdout_handler)

        config_page = pywikibot.Page(self.site, config_page_name)
        self.cfg = json.loads(config_page.text)
        self.logger.debug('config: %s', json.dumps(self.cfg, indent=4, ensure_ascii=False))

    def main(self):
        self.logger.info('start')
        if not self.cfg['enable']:
            self.logger.warning('Disabled')
            return

        self.logger.info('Starting...')

        PRC_REGEX = r'^PRC_admin/(data|list|%)/(\d{2}|%)/(\d{2}|%)/(\d{2}|%)/(\d{3}|%)/(\d{3}|%)$'
        if not re.search(PRC_REGEX, self.args.source):
            self.logger.error('invalid source')
            return
        if not re.search(PRC_REGEX, self.args.destination):
            self.logger.error('invalid destination')
            return
        src_parts = self.args.source.split('/')
        dst_parts = self.args.destination.split('/')
        for i in range(1, 7):
            if (src_parts[i] == '%' or dst_parts[i] == '%') and src_parts[i] != dst_parts[i]:
                self.logger.error('source[%s] is %s, destination[%s] is %s', i, src_parts[i], i, dst_parts[i])
                return

        conn = pymysql.connect(**db_settings)
        with conn.cursor() as cur:
            cur.execute('use zhwiki_p')
            cur.execute('''
            SELECT page_title
            FROM page
            WHERE page_title LIKE %s
                AND page_namespace = 10
                AND page_is_redirect = 0
            ''', (args.source,))
            res = cur.fetchall()
        changes = []
        for row in res:
            old = row[0].decode().split('/')
            new = [old[0]]
            for i in range(1, 7):
                if src_parts[i] == '%':
                    new.append(old[i])
                else:
                    new.append(dst_parts[i])
            changes.append((
                '/'.join(old),
                '/'.join(new),
            ))
        with open('changes.csv', 'w', encoding='utf8') as f:
            for change in changes:
                print('Move {} to {}'.format(change[0], change[1]))
                f.write('%s,%s\n' % change)

        summary = self.cfg['summary'].format(area=self.args.area, requester=self.args.requester)
        print('Summary: {}'.format(summary))
        toMove = pywikibot.input_yn('Move these {} pages?'.format(len(changes)), 'N')
        if toMove:
            self.logger.info('Moving...')
            for idx, change in enumerate(changes, 1):
                old_title = 'Template:{}'.format(change[0])
                new_title = 'Template:{}'.format(change[1])
                page = pywikibot.Page(self.site, old_title)
                self.logger.info('(%s/%s) Moving %s to %s', idx, len(changes), old_title, new_title)
                page.move(new_title, reason=summary, movetalk=True, noredirect=True, movesubpages=False)
        else:
            self.logger.info('Skip')

        self.logger.info('Done')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('destination')
    parser.add_argument('--area', help='行政區劃', required=True)
    parser.add_argument('--requester', help='申請人', required=True)
    parser.add_argument('-d', '--debug', action='store_const', dest='loglevel', const=logging.DEBUG, default=logging.INFO)
    args = parser.parse_args()

    mover = PrcAdminMover(config_page_name, args)
    mover.logger.setLevel(args.loglevel)
    mover.logger.debug('args: %s', args)
    mover.main()
