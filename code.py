import sys
import os
import binascii
import supervisor

data_buffer = "" # from pc

def process_pc_command(cmd):
    print("# Processing command:", cmd, "length", len(cmd))

    if cmd == "ping":
        print("pong")
    elif cmd.startswith("getfile "):
        parts = cmd.split(" ")
        filename = parts[1]

        try:
            with open(filename, "rb") as f:
                print("ok:", binascii.b2a_base64(f.read()).decode('utf-8'))
        except Exception as e:
            print("error: file error:", e)
    elif cmd.startswith("list"):
        path = "."
        if " " in cmd:
            path = cmd.split(" ")[1]
        
        try:
            for item in os.listdir(path):
                # item 0 is st_mode
                is_file = os.stat(path + os.sep + item)[0] >> 15

                if is_file:
                    print("file:", item)
                else:
                    print("dir:", item)
        except Exception as e:
            print("error: io error:", e)
    else:
        print("error: unrecognized command")

def check_for_pc_command():
    global data_buffer

    while supervisor.runtime.serial_bytes_available:
        data = sys.stdin.read(1)
        data_buffer += data

        if data == "\n":
            # command terminator
            process_pc_command(data_buffer.strip("\n").strip("\r"))
            data_buffer = ""

while True:
    check_for_pc_command()
