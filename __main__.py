'''ttynet server main file'''
import socket
import threading
import traceback
import struct
import time
import ctypes
import os
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
                for thread_find in threading.enumerate():
                    if thread_find.getName() == 'tcp(%s)'%user_ip:
                        stop_thread(thread_find)
                break

    def get_tcp_user(self, linked_ip):
        '''get socket handle by user tcp ip, format: [['tcp user ip', tcp socket], [...]]'''
        tcp_list = []
        for user in self.user_list:
            if linked_ip == user[1]:
                tcp_list.append([user[0], user[2]])
        return tcp_list

    def linked_ip_list(self):
        '''get linked terminal ip'''
        ip_list = []
        for user in self.user_list:
            if user[1] not in ip_list:
                ip_list.append(user[1])
        return ip_list

    def info(self):
        '''get user list'''
        user_list_text = '\r\n---------------------user list----------------------\r\n'
        user_list_text += '%4s%16s%18s\r\n'%('-NO-', '-user IP-', '-linked IP-')
        if len(self.user_list) == 0:
            user_list_text += 'None'
        else:
            for (count, user) in enumerate(self.user_list):
                user_list_text += '%4s%16s%18s\r\n'%(count+1, user[0], user[1])
        return user_list_text


class TerminalList():
    '''
    terminal list class
    format : [['terminal ip', 'terminal mac', 'run time'], [...]]
    '''
    def __init__(self):
        '''init'''
        self.terminal_list = []
        self.broad_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.broad_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.broad_socket.bind(('', config.BROADCAST_PORT))
        threading.Thread(name='udp broadcast re', target=self.__broad_re__).start()

    def __broad_re__(self):
        '''udp broadcast re'''
        while True:
            try:
                re_broadcast, (re_ip, _) = self.broad_socket.recvfrom(1024)
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
                for (count, terminal) in enumerate(self.terminal_list):
                    if re_ip == terminal[0]:
                        self.terminal_list[count] = [re_ip, terminal_mac, terminal_run_time]
                        break
                else:
                    self.terminal_list.append([re_ip, terminal_mac, terminal_run_time])

    def __send_udp_broadcast__(self):
        '''udp broadcast to find terminal'''
        broad_list = \
        '19 65 78 22 00 00 77 68 6F 20 69 73 20 64 63 75 20 64 65 76 3F 00 19 65 78 22'.split(' ')
        broad_data = b''
        for data in broad_list:
            broad_data += struct.pack('B', int(data, 16))
        self.broad_socket.sendto(broad_data, ('<broadcast>', 19001))

    def delete(self, terminal_ip):
        '''delete tcp user from the list, (USELESS?)'''
        for (count, user) in enumerate(self.terminal_list):
            if terminal_ip == user[0]:
                del self.terminal_list[count]
                break

    def update(self):
        '''update terminal list'''
        self.terminal_list = []
        self.__send_udp_broadcast__()
        time.sleep(config.UDP_BROADCAST_TM)
        self.terminal_list.sort(key=lambda k: k[0])

    def info(self):
        '''get terminal list'''
        text = '\r\n-------------------terminal list-------------------\r\n'
        text += '%4s%16s%18s%14s\r\n'%('-NO-', '-IP-', '-terminal MAC-', '-run time-')
        if len(self.terminal_list) == 0:
            text += 'None\r\n'
        else:
            for (count, terminal) in enumerate(self.terminal_list):
                text += '%4s%16s%18s%14s\r\n'%(count+1, terminal[0], terminal[1], terminal[2])
        return text

    def the_ip(self, index):
        '''get ip by index(start from 1)'''
        if 1 <= index <= len(self.terminal_list):
            return self.terminal_list[index - 1][0]
        else:
            return None

TCP_USER_LIST = TcpUser()
TERMINAL_LIST = TerminalList()


def tcp_server_accept():
    '''accept tcp client'''
    tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_server.bind(('', config.TCP_PORT))
    tcp_server.listen(32)
    while True:
        try:
            tcp_client, (user_ip, _) = tcp_server.accept()
            print(user_ip, "connected")
            tcp_client.sendall\
            ('\r\n*****Welcome!*****\r\nPress ENTER to refresh terminal list.\r\n'\
            .encode('gb2312', errors='ignore'))
        except Exception:
            traceback.print_exc()
            break

        for thread_find in threading.enumerate():
            if thread_find.getName() == 'tcp(%s)'%user_ip:
                stop_thread(thread_find)
        threading.Thread(name='tcp(%s)'%user_ip, target=tcp_run, args=(tcp_client, user_ip)).start()


def tcp_run(tcp_client, user_ip):
    '''re tcp frame'''
    tcp_client.sendall('\r\nupdating...\r\n'.encode('gb2312', errors='ignore'))
    TERMINAL_LIST.update()
    tcp_client.sendall(TERMINAL_LIST.info().encode('gb2312', errors='ignore'))
    tcp_client.sendall('input a number or ip:'.encode('gb2312', errors='ignore'))
    while True:
        re_byte = tcp_client.recv(128)  # re terminal NO select or ip
        if re_byte == b'\r\n':
            tcp_client.sendall('\r\nupdating...\r\n'.encode('gb2312', errors='ignore'))
            TERMINAL_LIST.update()
            tcp_client.sendall(TERMINAL_LIST.info().encode('gb2312', errors='ignore'))
            tcp_client.sendall('input a number or ip:'.encode('gb2312', errors='ignore'))
            continue
        re_text = re_byte.decode('gb2312', errors='ignore').strip()
        if len(re_text) <= 2:  # try number
            try:
                terminal_no = int(re_byte.decode('gb2312', errors='ignore'))
            except Exception:
                continue
            target_terminal_ip = TERMINAL_LIST.the_ip(terminal_no)
            if target_terminal_ip is not None:
                TCP_USER_LIST.add(user_ip, target_terminal_ip, tcp_client)
                break
        elif len(list(filter(lambda x: x >= 0 and x <= 255,\
                map(int, filter(lambda x: x.isdigit(), re_text.split('.')))))) == 4:  # try ip
            target_terminal_ip = re_text
            TCP_USER_LIST.add(user_ip, target_terminal_ip, tcp_client)
            break
        else:
            continue

    tcp_client.sendall('connected to {0}'.format(target_terminal_ip)\
                        .encode('gb2312', errors='ignore'))
    while True:
        try:
            re_byte = tcp_client.recv(1024)
        except Exception:
            tcp_client.shutdown(2)  # SHUT_RDWR
            tcp_client.close()
            TCP_USER_LIST.delete(user_ip)
            print('TCP user %s quit'%user_ip)
            break

        if re_byte:
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
                print('send to udp', target_terminal_ip)
                config.UDP_SOCKET.sendto(re_byte, (target_terminal_ip, 19000))
            except Exception:
                traceback.print_exc()
                break  # fix?


def udp_run():
    '''re udp frame'''
    if not os.path.exists(config.LOG_PATH):
        os.makedirs(config.LOG_PATH)
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
            with open('%s%s.txt'%(config.LOG_PATH, addr[0]), 'a') as file_h:
                file_h.write(re_text)
            tcp_socket_list = TCP_USER_LIST.get_tcp_user(addr[0])
            for tcp_ip, tcp_socket in tcp_socket_list:
                try:
                    tcp_socket.sendall(re_byte)
                except Exception:
                    TCP_USER_LIST.delete(tcp_ip)
                    print('TCP user %s quit'%tcp_ip)
                    traceback.print_exc()


def udp_heartbeat():
    '''udp send heartbeat to terminal'''
    while True:
        for linked_ip in TCP_USER_LIST.linked_ip_list():
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
        return TCP_USER_LIST.info()
    elif command == 't':
        TERMINAL_LIST.update()
        return TERMINAL_LIST.info()
    else:
        return 'command not found\r\n'


def get_thread_info():
    '''get thread list text'''
    thread_info = '-------thread-------\r\n'
    for count, thread_alive in enumerate(threading.enumerate(), start=1):
        thread_info += str(count) + '.' + thread_alive.getName() + '\r\n'
    return thread_info


if __name__ == '__main__':
    config.UDP_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    config.UDP_SOCKET.bind(('', 19000))

    threading.Thread(name='tcp accept', target=tcp_server_accept).start()
    threading.Thread(name='udp re', target=udp_run).start()
    threading.Thread(name='udp heartbeat se', target=udp_heartbeat).start()

    print('TTYNet Server V1.0(2017.03.27) Designed by Kay')

    while True:
        time.sleep(60)
        # print(get_my_info(input()))
