#!/usr/bin/env python3
"""Bridge USB MIDI input to ESP32 serial port at 115200 baud.

Creates a virtual MIDI port that appears in your DAW as a destination.
Any MIDI sent to that port is forwarded over serial to the ESP32.

Usage:
    python midi_serial_bridge.py /dev/ttyUSB0
    python midi_serial_bridge.py /dev/ttyUSB0 --midi-port "MIDI Controller Name"
    python midi_serial_bridge.py --list
"""

import argparse
import sys
import signal
import time

import mido
import serial


VIRTUAL_PORT_NAME = "MicroRack MIDI Bridge"


def list_midi_ports():
    ports = mido.get_input_names()
    if not ports:
        print("No MIDI input ports found.")
    else:
        print("Available MIDI input ports:")
        for i, name in enumerate(ports):
            print(f"  [{i}] {name}")


def main():
    parser = argparse.ArgumentParser(description="Bridge USB MIDI to ESP32 serial port")
    parser.add_argument("serial_port", nargs="?", help="Serial port path (e.g. /dev/ttyUSB0)")
    parser.add_argument("--midi-port", default=None,
                        help="Connect to an existing MIDI port instead of creating a virtual one")
    parser.add_argument("--list", action="store_true", help="List available MIDI input ports")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate (default: 115200)")
    args = parser.parse_args()

    if args.list:
        list_midi_ports()
        return

    if args.serial_port is None:
        parser.print_help()
        print(f"\nTip: run with --list to see available MIDI ports")
        sys.exit(1)

    # Open serial port
    try:
        ser = serial.Serial(args.serial_port, args.baud, timeout=1)
    except serial.SerialException as e:
        print(f"Error opening serial port {args.serial_port}: {e}", file=sys.stderr)
        sys.exit(1)

    # Open MIDI port
    try:
        if args.midi_port is not None:
            midi_in = mido.open_input(args.midi_port)
            print(f"MIDI input: {midi_in.name}")
        else:
            midi_in = mido.open_input(VIRTUAL_PORT_NAME, virtual=True)
            print(f"Created virtual MIDI port: \"{VIRTUAL_PORT_NAME}\"")
            print("Select this as a MIDI output in your DAW.")
    except (OSError, IOError) as e:
        print(f"Error opening MIDI port: {e}", file=sys.stderr)
        ser.close()
        sys.exit(1)

    print(f"Serial output: {args.serial_port} @ {args.baud} baud")
    print("Forwarding MIDI... (Ctrl+C to stop)")

    running = True

    def stop(signum, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    try:
        while running:
            for msg in midi_in.iter_pending():
                if msg.is_meta:
                    continue
                ser.write(bytes(msg.bytes()))
            time.sleep(0.001)
    finally:
        midi_in.close()
        ser.close()
        print("\nStopped.")


if __name__ == "__main__":
    main()
