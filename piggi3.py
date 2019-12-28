import time
import logging
import json
import random
import threading
from enum import Enum

from agt import AlexaGadget

from ev3dev2.led import Leds
from ev3dev2.sound import Sound
from ev3dev2.sensor.lego import InfraredSensor

# Set the logging level to INFO to see messages from AlexaGadget
logging.basicConfig(level=logging.INFO)


class Command(Enum):
    """
    The list of preset commands and their invocation variation.
    These variations correspond to the skill slot values.
    """
    DETECT = ['detect', 'detect money', 'detect coins']


class EventName(Enum):
    """
    The list of custom event name sent from this gadget
    """
    DETECT = "Detect"
    PROXIMITY = "Proximity"
    SPEECH = "Speech"


class MindstormsGadget(AlexaGadget):
    """
    A Mindstorms gadget that can perform bi-directional interaction with an Alexa skill.
    """

    def __init__(self):
        """
        Performs Alexa Gadget initialization routines and ev3dev resource allocation.
        """
        super().__init__()

        # Robot state
        self.detect_mode = False

        # Connect Infrared Sensor
        self.sound = Sound()
        self.leds = Leds()
        self.ir = InfraredSensor()

        # Start threads
        threading.Thread(target=self._proximity_thread, daemon=True).start()

    def on_connected(self, device_addr):
        """
        Gadget connected to the paired Echo device.
        :param device_addr: the address of the device we connected to
        """
        self.leds.set_color("LEFT", "GREEN")
        self.leds.set_color("RIGHT", "GREEN")
        print("{} connected to Echo device".format(self.friendly_name))

    def on_disconnected(self, device_addr):
        """
        Gadget disconnected from the paired Echo device.
        :param device_addr: the address of the device we disconnected from
        """
        self.leds.set_color("LEFT", "BLACK")
        self.leds.set_color("RIGHT", "BLACK")
        print("{} disconnected from Echo device".format(self.friendly_name))

    def on_custom_mindstorms_gadget_control(self, directive):
        """
        Handles the Custom.Mindstorms.Gadget control directive.
        :param directive: the custom directive with the matching namespace and name
        """
        try:
            payload = json.loads(directive.payload.decode("utf-8"))
            print("Control payload: {}".format(payload))
            control_type = payload["type"]

            if control_type == "command":
                # Expected params: [command]
                self._activate(payload["command"])

        except KeyError:
            print("Missing expected parameters: {}".format(directive))

    def _activate(self, command, balance=0):
        """
        Handles preset commands.
        :param command: the preset command
        :param balance: the balance if applicable
        """
        print("Activate command: ({})".format(command))
        
        if command in Command.DETECT.value:
            self.detect_mode = True
            self._send_event(EventName.SPEECH, {'speechOut': "Detect mode activated"})

            self.leds.set_color("LEFT", "YELLOW", 1)
            self.leds.set_color("RIGHT", "YELLOW", 1)

    def _send_event(self, name: EventName, payload):
        """
        Sends a custom event to trigger a sentry action.
        :param name: the name of the custom event
        :param payload: the sentry JSON payload
        """
        self.send_custom_event('Custom.Mindstorms.Gadget', name.value, payload)

    def _proximity_thread(self):
        """
        Monitors the distance between the robot and an object when detect mode is activated.
        If the minimum distance is breached, send a custom event to trigger action on
        the Alexa skill.
        """
        count = 0
        while True:
            while self.detect_mode:
                distance = self.ir.proximity
                print("Proximity: {}".format(distance))
                count = count + 1 if distance < 2 else 0
                # must trigger for 2 hundredths to prevent false alarms
                if count > 1:
                    print("Coin detected. Sending event to skill")
                    self.leds.set_color("LEFT", "RED", 1)
                    self.leds.set_color("RIGHT", "RED", 1)

                    self._send_event(EventName.PROXIMITY, {'distance': distance})

                    # wait for a second after successful detection
                    time.sleep(1)
            time.sleep(0.01)

if __name__ == '__main__':
    # Startup sequence
    gadget = MindstormsGadget()
    gadget.sound.play_song((('C4', 'e'), ('D4', 'e'), ('E5', 'q')))
    gadget.leds.set_color("LEFT", "GREEN")
    gadget.leds.set_color("RIGHT", "GREEN")

    # Gadget main entry point
    gadget.main()

    # Shutdown sequence
    gadget.sound.play_song((('E5', 'e'), ('C4', 'e')))
    gadget.leds.set_color("LEFT", "BLACK")
    gadget.leds.set_color("RIGHT", "BLACK")
