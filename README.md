# Tesla Wall Connector gen2 Home Assistant connector

Tesla Wall Connector (TWC) is an EV charging "wall box".

The TWC gen2 contains functionality where multiple TWC units can talk to each other over RS485 to balance the load between them so as not to exceed the total max current draw permitted.

This is small a python program that fakes being the master in such a multi-unit configuration, 
and uses it to expose the TWC to Home Assistant.

When connected, two Home Assistant entites are created:
 - `Charging current`: The current being drawn by the vehicle at this very moment. Updated every second.
 - `Max current`: A limit on how much current may be used for charging.

![Home Assistant screenshot](hass.png)

These two values can be used to implement fine-grained control of your charging. For example:
  - Balance the charging current against the surplus power generated by your solar panels.
  - Lower the charging current if the total household current exceeds the main fuse.

See [INSTALL.md](INSTALL.md) for installation instructions.

The TWC protocol was reverse engineered by [@dracoventions](https://github.com/dracoventions).
