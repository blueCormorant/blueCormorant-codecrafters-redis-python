
import threading
import socket

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

def is_bytes(obj):
    try:
        obj.decode()
        return True
    except (UnicodeDecodeError, AttributeError):
        return False

def handle_connection(client_connection):
    print(f"New connection: {client_connection}")
    while True:
        try:
            result = RESPDecoder(client_connection).decode()
            print(f"result = {result}")
            if type(result) is bytes:
                if result == b"ping":
                    client_connection.send(b"+PONG\r\n")
            elif type(result) is list:
                if len(result) <= 2:
                    if result[0] == b"echo":
                        arg = f"+{result[1].decode()}"
                        client_connection.send(arg.encode("UTF-8") + b"\r\n")
                    elif result[0] == b"ping":
                        client_connection.send(b"+PONG\r\n")
            else:
                client_connection.send(b"-ERR Unknown Command\r\n")
        except ConnectionError as error:
            print(error)
            break # Exit thread if the connection closes

def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")

    server_socket = socket.create_server(("localhost", 6379), reuse_port=True)
    while True:
        client_connection, _ = server_socket.accept() # wait for client
        threading.Thread(target=handle_connection, args=(client_connection,)).start()


if __name__ == "__main__":
    main()
