from collections import namedtuple

TOKEN = 'OTE5NDE5ODM0MjY0MDc2MzQ5.YbVicg.NhAiDrUJn1orPOMA65DaTtaQ1Ak'
OWNER_IDS = [508346978288271360]
DEFAULT_PREFIXES = ('akb-',)

LOCAL_USER = 'Buco'
PREVENT_LOCAL_COMMANDS = True
_db_conf = namedtuple('db_conf', ['host', 'port', 'user', 'password', 'db'])
DB_CONF = _db_conf(host='127.0.0.1', port=5432, user='arnaud', password='Psqlaboude1!', db='akb')