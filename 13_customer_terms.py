#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
from xmlrpc import client as xmlrpclib
import multiprocessing as mp

from scriptconfig import URL, DB, UID, PSW, WORKERS

# =================================== C U S T O M E R ========================================

def update_customer_terms(pid, data_pool, write_ids, error_ids):
    sock = xmlrpclib.ServerProxy(URL, allow_none=True)
    while data_pool:
        try:
            data = data_pool.pop()
            code = data.get('TERM-CODE')
            vals = {'name': data.get('TERM-DESC').strip(),
                    'note': data.get('TERM-DESC').strip(),
                    'active': True,
                    'order_type': 'sale',
                    'code': code,
                    'discount_per': data.get('TERM-DISC-PCT', 0),
                    'due_days': data.get('TERM-DISC-DAYS', 0),
                    }

            res = write_ids.get(code, [])
            if res:
                sock.execute(DB, UID, PSW, 'account.payment.term', 'write', res, vals)
                print(pid, 'UPDATE - CUSTOMER TERM', res)
            else:
                vals['line_ids'] = [(0, 0, {'type': 'balance', 'days': int(data.get('TERM-NET-DUE', 0) or 0)})]
                res = sock.execute(DB, UID, PSW, 'account.payment.term', 'create', vals)
                print(pid, 'CREATE - CUSTOMER TERM', res)
            if not data_pool:
                break
        except:
            break



def sync_terms():
    manager = mp.Manager()
    data_pool = manager.list()
    error_ids = manager.list()
    write_ids = manager.dict()
    process_Q = []

    fp = open('files/rclterm1.csv', 'r')
    csv_reader = csv.DictReader(fp)

    for vals in csv_reader:
        data_pool.append(vals)

    fp.close()

    domain = [('order_type', '=', 'sale')]
    sock = xmlrpclib.ServerProxy(URL, allow_none=True)

    res = sock.execute(DB, UID, PSW, 'account.payment.term', 'search_read', domain, ['id', 'code'])
    write_ids = {term['code']: term['id'] for term in res}


    res = None
    term_codes = None

    for i in range(WORKERS):
        pid = "Worker-%d" % (i + 1)
        worker = mp.Process(name=pid, target=update_customer_terms, args=(pid, data_pool, write_ids, error_ids))
        process_Q.append(worker)
        worker.start()

    for worker in process_Q:
        worker.join()


if __name__ == "__main__":

    # PARTNER
    sync_terms()
