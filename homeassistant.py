from ha_mqtt_discoverable import Settings, DeviceInfo
from ha_mqtt_discoverable.sensors import Number, NumberInfo, Sensor, SensorInfo
from paho.mqtt.client import Client, MQTTMessage

import json

charging_current: Sensor = None
max_current: Number = None
last_charging_current: float = 0
set_current_callback: callable = None

with open('config.json') as f:
    config = json.load(f)
    print('Read config')


def max_current_callback(_: Client, __, message: MQTTMessage):
    value = float(message.payload.decode())
    print(f'Received {value} from HA')
    # write it to the WC
    if set_current_callback:
        value = set_current_callback(value)
    global max_current
    max_current.set_value(value)


def update_charging_current(current: float):
    global charging_current, last_charging_current
    if charging_current and current != last_charging_current:
        charging_current.set_state(current)
        last_charging_current = current


def create_ha_device(model: str, serial: str, version: str, amp_callback: callable):
    global set_current_callback
    set_current_callback = amp_callback
    id_prefix = 'tesla_wall_connector'

    mqtt_settings = Settings.MQTT(host=config['hostname'],
                                  username=config['username'],
                                  password=config['password'])

    device_info = DeviceInfo(name='Tesla Wall Connector',
                             manufacturer='Tesla',
                             model=model,
                             sw_version=version,
                             identifiers=serial)

    charging_current_info = SensorInfo(name='Charging current',
                                       min=0, step=0.01,
                                       device_class='current',
                                       device=device_info,
                                       unit_of_measurement='A',
                                       unique_id=id_prefix + '_charging_current')
    charging_current_settings = Settings(mqtt=mqtt_settings,
                                         entity=charging_current_info)
    global charging_current
    charging_current = Sensor(charging_current_settings)
    charging_current.set_state(0)

    max_current_info = NumberInfo(name='Max current',
                                  min=0, max=config['max_current'], step=0.01,
                                  mode='slider',
                                  device_class='current',
                                  device=device_info,
                                  unit_of_measurement='A',
                                  unique_id=id_prefix + '_max_current')
    max_current_settings = Settings(mqtt=mqtt_settings,
                                    entity=max_current_info)
    global max_current
    max_current = Number(max_current_settings, max_current_callback)
    max_current.set_value(config['max_current'])
