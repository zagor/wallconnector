import threading
import time
import serial
import homeassistant


GET_SERIAL_NUMBER = b'\xFB\x19'
GET_MODEL_NUMBER = b'\xFB\x1A'
GET_FIRMWARE_VER = b'\xFB\x1B'
GET_PLUG_STATE = b'\xFB\xB4'


def send(message: bytes, length=15):
    msg = bytearray(message)
    msg += b'\0' * (length - len(msg))
    msg.append(sum(message[1:]) & 0xff)

    i = 0
    while i < len(msg):
        if msg[i] == 0xc0:
            msg[i:i+1] = b'\xdb\xdc'
            i += 1
        elif msg[i] == 0xdb:
            msg[i:i+1] = b'\xdb\xdd'
            i += 1
        i += 1
    msg.insert(0, 0xc0)
    msg.append(0xc0)
    tty.write(msg)
    # print(f'>{msg}')


def send_linkready():
    for _ in range(5):
        send(b'\xFC\xE1\x77\x77\x77', length=13)
        print('>linkready1')
        time.sleep(0.1)
    for _ in range(5):
        send(b'\xFC\xE2\x77\x77\x77', length=13)
        print('>linkready2')
        time.sleep(0.1)


def send_max_current(current: float):
    if current < 6:
        current += 640
    amps = int(current * 100).to_bytes(2, 'big')
    send(b'\xFB\xE0\x77\x77' + slave_id + b'\x09' + amps)


def send_heartbeat():
    global max_current
    if max_current != slave_max_current:
        send_max_current(max_current)
        print(f'>heartbeat max {max_current} A')
    else:
        # nop
        send(b'\xFB\xE0\x77\x77' + slave_id)
        print('>heartbeat nop')


def parse_heartbeat(msg: bytes):
    sender = hex(int.from_bytes(msg[2:4]))
    # receiver = hex(int.from_bytes(msg[4:6]))
    state = msg[6]
    global slave_max_current
    slave_max_current = float(int.from_bytes(msg[7:9])) / 100
    if slave_max_current >= 640:
        slave_max_current -= 640
    slave_max_current = round(slave_max_current, 2)
    drawn_current = round(float(int.from_bytes(msg[9:11])) / 100 * slave_current_calibration, 2)
    print(f'<slave heartbeat from {sender}, '
          f'state {state}, limit {slave_max_current} A, '
          f'drawing {drawn_current} A')
    global heartbeat_count
    heartbeat_count += 1
    if heartbeat_count & 1 == 0:
        homeassistant.update_charging_current(drawn_current)


def set_max_amps(current: float) -> float:
    global max_current, set_current_timeout
    with lock:
        if now > set_current_timeout:
            max_current = current
            set_current_timeout = now + 5
    return max_current


def parse_message():
    global input_buffer
    # print(f'<{input_buffer}')
    while True:
        start = input_buffer.find(0xC0)
        end = input_buffer.find(0xC0, start + 1)
        if end - start < 13:
            # noise or mismatched start/end. remove first fragment.
            input_buffer = input_buffer[end:]
            if input_buffer.count(0xC0) >= 2:
                # there are still two frame marks in the buffer,
                # try finding a valid message again
                continue
            else:
                return
        else:
            break
    msg = input_buffer[start+1:end]
    received_checksum = msg[-1]
    msg = msg[:-1]  # remove checksum
    checksum = sum(msg[1:]) & 0xFF
    if checksum != received_checksum:
        print(f'<{input_buffer}')
        print(f'Calculated checksum {checksum:02x}, got {received_checksum:02x}')
    else:
        global slave_serial, slave_model, slave_firmware
        match int.from_bytes(msg[:2]):
            case 0xFD19:  # serial number
                # Response: FD 19 41 31 36 4B 30 30 xx xx xx xx xx 75
                slave_serial = msg[2:].decode('ascii')
                print(f'<serial number {slave_serial}')
                print('>get_model_number')
                send(GET_MODEL_NUMBER)
            case 0xFD1A:  # model number
                slave_model = msg[2:9].decode('ascii')
                print(f'<model number {slave_model}')
                print('>get_firmware_version')
                send(GET_FIRMWARE_VER)
            case 0xFD1B:  # firmware version
                slave_firmware = f'{msg[2]}.{msg[3]}.{msg[4]}'
                print(f'<firmware version {slave_firmware}')
                homeassistant.create_ha_device(model=slave_model,
                                               serial=slave_serial,
                                               version=slave_firmware,
                                               amp_callback=set_max_amps)
            case 0xFDB4:  # plug state
                print(f'<plug state {msg[4]}')
            case 0xFDE0:  # slave heartbeat
                parse_heartbeat(msg)
                if not slave_serial:
                    slave_serial = '-'
                    print('>get_serial_number')
                    send(GET_SERIAL_NUMBER)
            case 0xFDE2:  # slave link ready
                global slave_id, protocol_version
                slave_id = msg[2:4]
                max_amps = msg[5]
                match len(msg):
                    case 13: protocol_version = 1
                    case 15: protocol_version = 2
                    case _ as unknown:
                        raise RuntimeError(f'Unknown protocol. Message length {unknown}')
                print(f'<link ready ID {slave_id[0]:+2x} max_amps {max_amps} A')
            case _ as unknown:
                print(f'Got unknown response code {unknown: 02x}')
    input_buffer = input_buffer[end+1:]


def read_tty():
    global input_buffer
    input_buffer += tty.read(tty.in_waiting)
    frame_marks = input_buffer.count(0xC0)
    if frame_marks == 0:
        # ignore noise between frame markers
        input_buffer.clear()
    elif frame_marks > 1:
        parse_message()


# main
tty = serial.Serial('/dev/ttyUSB0')

send_linkready()

last_heartbeat = 0
heartbeat_interval = 1.0
input_buffer = bytearray()
tty: serial.Serial
slave_id: bytes = bytes()
slave_serial = ''
slave_model = ''
slave_firmware = ''

max_current = 16
slave_max_current = 0
set_current_timeout = 0
protocol_version = 0
heartbeat_count = 0
slave_current_calibration = 0.95  # it reports ~5 percent too high

lock = threading.Lock()

while True:
    now = time.monotonic()
    if tty.in_waiting:
        read_tty()
    elif slave_id and now > last_heartbeat + heartbeat_interval:
        send_heartbeat()
        send_heartbeat()
        last_heartbeat = now

    time.sleep(0.1)
