import socket
import time

fhem_host = 'alarmpi.local'
fhem_port = 7072
fhem_fan_name = 'smartfan2s'
fan_level_interval = 15.0


def fan_command(arg):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((fhem_host, fhem_port))
        s.send(("set %s %s\n" % (fhem_fan_name, arg)).encode())
        s.close()
    except ConnectionError:
        pass


last_fan_level = None


def fan_level(level):
    global last_fan_level

    if last_fan_level is None or (time.time() - last_fan_level) > fan_level_interval:
        fan_command('level %d' % int(level))
        last_fan_level = time.time()


# the viscyc hooks:


def start():
    fan_command('angle_enable off')


def stop():
    fan_command('angle_enable on')


def send(rpm, rev_count, watts):
    wmin, wmax = 50, 120
    fmin, fmax = 20, 100

    fan_level_calc = ((watts - wmin) / (wmax - wmin)) * (fmax - fmin) + fmin
    fan_level_calc = min(fmax, fan_level_calc)
    fan_level_calc = max(fmin, fan_level_calc)
    fan_level_calc = int(fan_level_calc)

    fan_level(fan_level_calc)
