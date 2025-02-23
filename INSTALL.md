# Installation

## Tesla Wall Connector (TWC) setup

This program only works with the [second generation wall connector](https://www.tesla.com/support/charging/gen-2-wall-connector).
Later models do not have the required RS485 bus.

Steps:
1. Disconnect power to your TWC and open it.
1. Connect a 2-wire signal cable to "IN" section of the RS-485 terminal block. Take note of D+ and D-.
1. Turn the rotary switch labelled SA3 to "F", for "Follower mode".
1. Close and reconnect power to the TWC

## Home Assistant setup

To avoid the need for a custom Home Assistant integration, wallconnector uses MQTT Discovery.
 
Steps:
1. Add the MQTT integration (Settings->Device & Services->Add integration)
1. Create a new non-admin user (Settings->People->Users->Add user).

## Computer setup

You need a computer that has:

   - Python 3 
   - A USB port for the USB RS485 converter 
   - A working network connection to your Home Assistant instance

This is called "the computer" in this documentation.
I use a Raspberry Pi Zero W with Raspbian, but any linux computer will do.   

(You could probably also run wallconnector directly on your Home Assistant computer
if that is more convenient for you, but I have not looked into the details of that.) 

Steps:

1. On the computer, clone this repo into your home directory (don't run as root) and go into it: 

        git clone https://github.com/zagor/wallconnector.git
        cd wallconnector 

1. Copy and edit the configuration file. 
   The `hostname` field is the hostname or IP address of your Home Assistant instance.
   The `username` and `password` fields are for the new user you created earlier.

        cp config.json.example config.json
        nano config.json

1. Create a python virtual environment:

        python3 -m venv .venv
        .venv/bin/pip install -r requirements.txt

1. Connect the RS485 wire to the USB dongle (ensure that D+ and D- are correct) and plug it in to the computer.

1. Add your username to the `dialout` group for permissions:

        sudo adduser $USER dialout

1. Install and activate the systemd service file:

        mkdir -p $HOME/.config/systemd/user
        cp wallconnector.service $HOME/.config/systemd/user
        loginctl enable-linger
        systemctl --user daemon-reload
        systemctl --user start wallconnector.service
 
1. Check service status:

        systemctl --user status wallconnector.service


## Finishing up

1. You will get a "new entity" notification in Home Assistant. Add it.
1. Test it:
   1. Start a charging session using your Tesla app or from within the car
   1. Check that the reported charging current changes in Home Assistant
   1. Change the max current in Home Assistant and see that it takes effect in the car
1. Run `journalctl ---follow --user-unit wallconnector.service` on the computer to see live log output from the program

### Notes about max current

While you can set max current to any decimal value, 
the TWC only changes the actual charging current in bigger and somewhat uneven steps of
around 0.3-0.5 A.

The measured charging current never goes to zero while charging is ongoing. 
If you set max current to zero the car will still draw around 0.5A.

The TWCs don't like very frequent max current changes. 
Try to let at least a couple of seconds elapse between each change. 
