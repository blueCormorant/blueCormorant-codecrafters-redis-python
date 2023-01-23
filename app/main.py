
import threading
import socket
import time

# Wraps socket.Socket adding support for buffered reading.
# 
class ConnectionBuffer:

    def __init__(self, connection):
        self.connection = connection
        self.buffer = b''
    
    # read from socket until delimiter
    def read_until_delimiter(self, delimiter):
        while delimiter not in self.buffer:
            data = self.connection.recv(1024)
            if not data: # socket has closed
                return None

            self.buffer += data
        
        data_before_delimiter, delimiter, self.buffer = self.buffer.partition(delimiter)
        return data_before_delimiter

    # read fixed length from socket
    def read(self, buffer_size):
        if len(self.buffer) < buffer_size:
            data = self.connection.recv(1024)
            if not data: # socket has closed
                return None

            self.buffer += data

        data, self.buffer = self.buffer[:buffer_size], self.buffer[buffer_size:]
        return data

class RESPDecoder:

    def __init__(self, connection):
        self.connection = ConnectionBuffer(connection)

    def decode(self):
        byte = self.connection.read(1)
        if byte == b"+":
            return self.decode_simple_string()
        elif byte == b"$":
            return self.decode_bulk_string()
        elif byte == b"*":
            return self.decode_array()
        elif byte is None:
            raise ConnectionError("Connection terminated")
        else:
            raise Exception(f"Unknown data type byte: {byte}")
           
    def decode_simple_string(self):
        return self.connection.read_until_delimiter(b"\r\n")

    def decode_bulk_string(self):
        bulk_string_length = int(self.connection.read_until_delimiter(b"\r\n"))
        bulk_string = self.connection.read(bulk_string_length)
        assert self.connection.read_until_delimiter(b"\r\n") == b""
        return bulk_string

    def decode_array(self):
        result = []
        array_length = int(self.connection.read_until_delimiter(b"\r\n"))

        for _ in range(array_length):
            result.append(self.decode())

        return result


class DataItem:

    def __init__(self, item, miliseconds=None):
        self.item = item
        self.miliseconds = miliseconds
        # Record expiry time in miliseconds
        try:
            self.expiry_time = time.time()*1000 + float(miliseconds)
        except:
            self.expiry_time = None

class DataStore:

    def __init__(self):
        self.data = {}

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self , key, value):
        self.data[key] = value

    def __iter__(self):
        return iter(self.data)

    def __str__(self):

        if len(self.data) == 0:
            return "{}"

        table, footer = "-"*10 + "\n", "-"*10
        for key in self.data:
            item = self.data[key]
            if item.expiry_time is None:
                table += f"{key}:{item.item}:None\n\n"
            else:
                table += f"{key}:{item.item}:{item.expiry_time/1000}\n\n"
                
        return table

def is_bytes(obj):
    try:
        obj.decode()
        return True
    except (UnicodeDecodeError, AttributeError):
        return False

def handle_connection(client_connection, data):
    while True:
        try:
            result = RESPDecoder(client_connection).decode()
            if type(result) is bytes:
                if result == b"ping":
                    client_connection.send(b"+PONG\r\n")
            elif type(result) is list:
                if result[0] == b"echo":
                    response = f"{result[1].decode()}"
                    client_connection.send(f"+{response}".encode("UTF-8") + b"\r\n")
                elif result[0] == b"ping":
                    client_connection.send(b"+PONG\r\n")
                elif result[0] == b"get":
                    key = result[1].decode()
                    value = data[key].item
                    try:
                        curr_time = time.time()*1000
                        if curr_time < data[key].expiry_time:
                            client_connection.send(f"+{value}".encode("UTF-8") + b"\r\n")
                        else:
                            client_connection.send(b"$-1\r\n")
                    except (KeyError, TypeError):
                        client_connection.send(f"+{value}".encode("UTF-8") + b"\r\n")
                if result[0] == b"set":
                    if len(result) == 3:
                        key = f"{result[1].decode()}"
                        value = f"{result[2].decode()}"
                        data[key] = DataItem(value)
                        client_connection.send(b"+OK\r\n")
                    elif len(result) == 5:
                        key = f"{result[1].decode()}"
                        value = f"{result[2].decode()}"
                        px = f"{result[3].decode()}"
                        miliseconds = f"{result[4].decode()}"
                        data[key] = DataItem(value, miliseconds)
                        client_connection.send(b"+OK\r\n")
            else:
                client_connection.send(b"-ERR Unknown Command\r\n")
        except ConnectionError as error:
            break # Exit thread if the connection closes

def main():
    data = DataStore()
    server_socket = socket.create_server(("localhost", 6379), reuse_port=True)
    while True:
        client_connection, _ = server_socket.accept() # wait for client
        threading.Thread(target=handle_connection, args=(client_connection, data)).start()

if __name__ == "__main__":
    main()
