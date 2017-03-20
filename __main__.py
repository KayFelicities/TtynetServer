'''udp terminal main file'''
import socket
import threading
import traceback
import struct
import time
import ctypes
import config


class TcpUser():
    '''
    connected tcp user(pc client)
    format : [['tcp user ip', 'linked terminal ip', tcp socket], [...]]
    '''
    def __init__(self):
        '''init'''
        self.user_list = []

    def add(self, user_ip, linked_ip, tcp_socket_handle):
        '''add tcp user'''
        for (count, user) in enumerate(self.user_list):
            if user_ip == user[0]:
                self.user_list[count] = [user_ip, linked_ip, tcp_socket_handle]
                break
        else:
            self.user_list.append([user_ip, linked_ip, tcp_socket_handle])

    def delete(self, user_ip):
        '''delete tcp user from the list'''
        for (count, user) in enumerate(self.user_list):
            if user_ip == user[0]:
                del self.user_list[count]
                break

    def socket_handle(self, linked_ip):
        '''get socket handle by user tcp ip'''
        for user in self.user_list:
            if linked_ip == user[1]:
                return user[2]
        return None

    def get_linked_ip(self):
        '''get linked terminal ip'''
        linked_ip_list = []
        for user in self.user_list:
            if user[1] not in linked_ip_list:
                linked_ip_list.append(user[1])
        return linked_ip_list


    def get_info(self):
        '''get user list'''
        user_list_text = '\r\n---------------------user list----------------------\r\n'
        user_list_text += '%4s%16s%18s\r\n'%('-NO-', '-user IP-', '-linked IP-')
        if len(self.user_list) == 0:
            user_list_text += 'None'
        else:
            for (count, user) in enumerate(self.user_list):
                user_list_text += '%4s%16s%18s\r\n'%(count+1, user[0], user[1])
        return user_list_text

TCP_USER_LIST = TcpUser()



def tcp_server_accept():
    '''accept tcp client'''
    tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_server.bind(('', config.TCP_PORT))
    tcp_server.listen(32)
    while True:
        try:
            tcp_client, addr = tcp_server.accept()
            print(addr, "connected")
            tcp_client.sendall\
            ('\r\n\r\n*****Welcome!*****\r\nPress ENTER to refresh terminal list.\n'\
            .encode('gb2312', errors='ignore'))
        except Exception:
            traceback.print_exc()
            break

        for thread_find in threading.enumerate():
            if thread_find.getName() == 'tcp(%s)'%addr[0]:
                stop_thread(thread_find)
        threading.Thread(name='tcp(%s)'%addr[0], target=tcp_run, args=(tcp_client, addr)).start()


def update_terminal_list():
    '''update terminal list and send list to tcp client'''
    config.TERMINAL_LIST = []
    udp_broadcast()
    time.sleep(1)
    config.TERMINAL_LIST.sort(key=lambda k: k[0])


def tcp_run(tcp_client, addr):
    '''re tcp frame'''
    tcp_client.sendall('\nupdating...\n'.encode('gb2312', errors='ignore'))
    update_terminal_list()
    tcp_client.sendall(get_terminal_list().encode('gb2312', errors='ignore'))
    while True:
        re_byte = tcp_client.recv(128)  # re terminal NO select
        if re_byte != b'':
            try:
                terminal_no = int(re_byte.decode('gb2312', errors='ignore'))
                target_terminal_addr = config.TERMINAL_LIST[terminal_no - 1][0]
            except Exception:
                print('exception')
                if re_byte == b'\r\n':
                    tcp_client.sendall('\nupdating...\n'.encode('gb2312', errors='ignore'))
                    update_terminal_list()
                    tcp_client.sendall(get_terminal_list().encode('gb2312', errors='ignore'))
                continue

            TCP_USER_LIST.add(addr[0], target_terminal_addr, tcp_client)
            break

    while True:
        try:
            re_byte = tcp_client.recv(1024)
        except Exception:
            tcp_client.shutdown(2)  # SHUT_RDWR
            tcp_client.close()
            TCP_USER_LIST.delete(addr[0])
            print('TCP user %s quit'%addr[0])
            break

        if re_byte != b'':
            print('re_byte:', re_byte)
            re_text = re_byte.decode('gb2312', errors='ignore')
            if len(re_text) == 0:
                print('tcp re ignored')
                continue
            print('tcp re:', re_text)

            # local command
            if re_text[0:2] == 's:':
                try:
                    tcp_client.sendall(get_my_info(re_text[2:]).encode('gb2312', errors='ignore'))
                except Exception:
                    traceback.print_exc()
                continue

            # data send to terminal
            try:
                print('send to udp', target_terminal_addr)
                config.UDP_SOCKET.sendto(re_byte, (target_terminal_addr, 19000))
            except Exception:
                traceback.print_exc()
                break  # fix?


def udp_run():
    '''re udp frame'''
    while True:
        try:
            re_byte, addr = config.UDP_SOCKET.recvfrom(65536)
        except Exception:
            traceback.print_exc()
            print('UDP err')

        if re_byte != b'':
            re_text = re_byte.decode('gb2312', errors='ignore')
            if len(re_text) == 0:
                print('udp re ignored')
                continue
            print('udp re:', re_text)
            with open('%s.txt'%addr[0], 'a') as file_h:
                file_h.write(re_text)
            tcp_socket = TCP_USER_LIST.socket_handle(addr[0])
            if tcp_socket is not None:
                try:
                    tcp_socket.sendall(re_byte)
                except Exception:
                    traceback.print_exc()


def udp_find():
    '''udp broadcast re'''
    while True:
        try:
            re_broadcast, addr = config.BROADCAST_SOCKET.recvfrom(1024)
            # print(str(re_broadcast))
        except Exception:
            traceback.print_exc()
            continue
        if re_broadcast != b'':
            terminal_info = list(map(lambda hex: '%02x'%hex, re_broadcast))
            # print('terminal_info:', terminal_info)
            if ''.join(terminal_info[0:4]) != '22786519': # magic num
                print('magic num err:', ''.join(terminal_info[0:4]))
                continue
            terminal_mac = ''.join(terminal_info[5:11])
            terminal_run_time = str(int(''.join(terminal_info[23:19:-1]), 16) // 60) + 'min'
            for (count, terminal) in enumerate(config.TERMINAL_LIST):
                if addr[0] == terminal[0]:
                    config.TERMINAL_LIST[count] = [addr[0], terminal_mac, terminal_run_time]
                    break
            else:
                config.TERMINAL_LIST.append([addr[0], terminal_mac, terminal_run_time])


def udp_broadcast():
    '''udp broadcast to find terminal'''
    broad_list = \
    '19 65 78 22 00 00 77 68 6F 20 69 73 20 64 63 75 20 64 65 76 3F 00 19 65 78 22'.split(' ')
    broad_data = b''
    for data in broad_list:
        broad_data += struct.pack('B', int(data, 16))
    config.BROADCAST_SOCKET.sendto(broad_data, ('<broadcast>', 19001))


def udp_heartbeat():
    '''udp send heartbeat to terminal'''
    while True:
        for linked_ip in TCP_USER_LIST.get_linked_ip():
            config.UDP_SOCKET.sendto(b'', (linked_ip, 19000))
            print('send hb to', linked_ip)
        time.sleep(config.UDP_HEARTBEAT_TM)


def stop_thread(thread):
    '''stop a thread'''
    tid = ctypes.c_long(thread.ident)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(SystemExit))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


def get_my_info(command):
    '''local command'''
    if command == '':
        return ''
    if command == 'i':
        return get_thread_info()
    elif command == 'u':
        return TCP_USER_LIST.get_info()
    elif command == 't':
        update_terminal_list()
        return get_terminal_list()
    else:
        return 'command not found\r\n'


def get_thread_info():
    '''get thread list text'''
    thread_info = '-------thread-------\r\n'
    for count, thread_alive in enumerate(threading.enumerate(), start=1):
        thread_info += str(count) + '.' + thread_alive.getName() + '\r\n'
    return thread_info


def get_terminal_list():
    '''get terminal list'''
    text = '\r\n-------------------terminal list-------------------\r\n'
    text += '%4s%16s%18s%14s\r\n'%('-NO-', '-IP-', '-terminal MAC-', '-run time-')
    if len(config.TERMINAL_LIST) == 0:
        text += 'None'
    else:
        for (count, terminal) in enumerate(config.TERMINAL_LIST):
            text += '%4s%16s%18s%14s\r\n'%(count+1, terminal[0], terminal[1], terminal[2])
    return text


if __name__ == '__main__':


    config.UDP_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    config.UDP_SOCKET.bind(('', 19000))

    config.BROADCAST_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    config.BROADCAST_SOCKET.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    config.BROADCAST_SOCKET.bind(('', config.BROADCAST_PORT))

    threading.Thread(name='tcp accept', target=tcp_server_accept).start()
    threading.Thread(name='udp re', target=udp_run).start()
    threading.Thread(name='udp broadcast re', target=udp_find).start()
    threading.Thread(name='udp heartbeat se', target=udp_heartbeat).start()

    while True:
        print(get_my_info(input()))
