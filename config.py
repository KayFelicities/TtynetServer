'''global args'''


UDP_SOCKET = None
BROADCAST_SOCKET = None

BROADCAST_PORT = 19005  # must >19000

TCP_PORT = 20017

UDP_HEARTBEAT_TM = 60  # unit: second

TERMINAL_LIST = []  # ['terminal ip', 'terminal mac', 'run time']
# USER_LIST = []  # ['tcp user ip', 'linked terminal ip', tcp socket]
