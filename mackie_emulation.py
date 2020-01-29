import time
import tkinter
import rtmidi
from functools import partial
from rtmidi.midiconstants import NOTE_OFF, NOTE_ON


def setup_midi_callbacks(_num_strips):
    vpot_values = []
    display_first_lines = []
    display_second_lines = []

    for s in range(0, _num_strips):
        vpot = tkinter.DoubleVar()
        vpot.set(23)
        vpot_values.append(vpot)
        line1 = tkinter.StringVar()
        line1.set(("line1, %s" % s))
        display_first_lines.append(line1)
        line2 = tkinter.StringVar()
        line2.set(("line2, %s" % s))
        display_second_lines.append(line2)

    return {
        "vpot_values": vpot_values,
        "display_first_lines": display_first_lines,
        "display_second_lines": display_second_lines
    }


def draw_vpot_window(_main_window, _surface_state, _midi_out_handler, _strip_index):
    vpot = tkinter.PanedWindow(_main_window)
    vpot.grid(row=0, column=_strip_index)
    slider = tkinter.Scale(vpot, orient=tkinter.VERTICAL, variable=_surface_state["vpot_values"][_strip_index])
    slider.grid(row=0, column=0)
    button = tkinter.Button(vpot, text="Press vpot", command=lambda: _midi_out_handler.vpot_clicked(_strip_index))
    button.grid(row=1, column=0)


def draw_scribble_script(_main_window, _surface_state, _strip_index):
    scribble = tkinter.PanedWindow(_main_window)
    scribble.grid(row=1, column=_strip_index)
    line1 = tkinter.Label(scribble, height=1, width=15,
                          textvariable=_surface_state["display_first_lines"][_strip_index])
    line1.grid(row=0, column=0)
    line2 = tkinter.Label(scribble, height=1, width=15,
                          textvariable=_surface_state["display_second_lines"][_strip_index])
    line2.grid(row=1, column=0)


def draw_strip(_main_window, _surface_state, _midi_out_handler, _strip_index):
    draw_vpot_window(_main_window, _surface_state, _midi_out_handler, _strip_index)
    draw_scribble_script(_main_window, _surface_state, _strip_index)


def draw_assign_section(_main_window, _surface_state, _midi_out_handler, draw_in_main_window_column):
    assign_window = tkinter.PanedWindow(_main_window)
    assign_window.grid(row=0, column=draw_in_main_window_column)
    track_view = tkinter.Button(assign_window, text="Track",
                                command=lambda: _midi_out_handler.set_subview_mode("Track"))
    track_view.grid(row=0, column=0)

    pan_view = tkinter.Button(assign_window, text="Pan",
                              command=lambda: _midi_out_handler.set_subview_mode("Pan"))
    pan_view.grid(row=0, column=1)

    eq_view = tkinter.Button(assign_window, text="EQ",
                             command=lambda: _midi_out_handler.set_subview_mode("EQ"))
    eq_view.grid(row=0, column=2)

    send_view = tkinter.Button(assign_window, text="Send",
                               command=lambda: _midi_out_handler.set_subview_mode("Send"))
    send_view.grid(row=0, column=3)

    plugin_view = tkinter.Button(assign_window, text="Plug-In",
                                 command=lambda: _midi_out_handler.set_subview_mode("Plug-In"))
    plugin_view.grid(row=0, column=4)

    inst_view = tkinter.Button(assign_window, text="Inst", command=lambda: _midi_out_handler.set_subview_mode("Inst"))
    inst_view.grid(row=0, column=5)


def draw_cursor_keys(_main_window, _midi_out_handler, _columns_used_in_main):
    cursors = tkinter.PanedWindow(_main_window)
    cursors.grid(row=2, column=0, columnspan=_columns_used_in_main)
    left = tkinter.Button(cursors, text="<", command=lambda: _midi_out_handler.handle_cursor("left"))
    left.grid(row=0, column=0)
    right = tkinter.Button(cursors, text=">", command=lambda: _midi_out_handler.handle_cursor("right"))
    right.grid(row=0, column=1)


def draw_ui(_main_window, _surface_state, _midi_out_handler):
    _num_strips = len(_surface_state["vpot_values"])
    for s in range(0, _num_strips):
        draw_strip(_main_window, _surface_state, _midi_out_handler, s)

    draw_assign_section(_main_window, _surface_state, _midi_out_handler, num_strips + 1)
    draw_cursor_keys(_main_window, _midi_out_handler, num_strips + 1)


def update_display(_position, _hex_codes, _surface_state):
    # print("position: %s" % (_position))
    line = 1
    strip_index = int(_position / 7)
    if _position > 0x37:
        line = 2
        strip_index = int((_position - 0x38) / 7)

    # print("updating line %s of strip %s" % (line, strip_index))

    display_lines = _surface_state["display_first_lines"] if line == 1 else _surface_state["display_second_lines"]

    msg_as_string = ""
    for hex_code in _hex_codes:
        # convert illegal characters to asterisk
        if (hex_code < 0x20) or (hex_code > 0x7F):
            msg_as_string += '*'
        else:
            msg_as_string += chr(hex_code)

    # print("message in display will be: %s" % msg_as_string)
    # print("There are %s displays for line %s" % (len(display_lines), line))
    display_lines[strip_index].set(msg_as_string)


def handle_sys_ex(_message, _surface_state, _midi_out_handler):
    # print("handle_sys_ex:", _message)
    if _message[0:5] != [0xF0, 0x00, 0x00, 0x66, 0x14]:
        return False

    if _message[5:] == [0x00, 0xF7]:
        sysex_message = [0x01]
        serial_number = '__mcu_emu__'
        _serial_number_bytes = []
        for char in serial_number:
            _serial_number_bytes.append(ord(char))
        sysex_message.extend(_serial_number_bytes)
        challenge = 'test'
        _challenge_bytes = []
        for char in challenge:
            _challenge_bytes.append(ord(char))
        sysex_message.extend(_challenge_bytes)
        _midi_out_handler.send_midi_sysex(sysex_message)

        return True

    if _message[5] == 0x12:
        position = _message[6]
        hex_codes = _message[7:-1]
        update_display(position, hex_codes, _surface_state)        
        return True
    
    return False


def handle_midi(_message, _surface_state, _midi_out_handler):
    pass


def handle_mackie_in(_surface_state, _midi_out_handler, event, data=None):
    _message, _deltatime = event
    # print("%r" % (_message))
    if not handle_sys_ex(_message, _surface_state, _midi_out_handler):
        handle_midi(_message, _surface_state, _midi_out_handler)


class MidiOutputHandler(object):
    def __init__(self, __midi_out):
        self._midi_out = __midi_out

    def send_midi_sysex(self, _sysex):
        # print("sending ", _sysex)
        header = [0xF0, 0x00, 0x00, 0x66, 0x14]
        _final_message = header + _sysex + [0xF7]
        self._midi_out.send_message(_final_message)

    def vpot_clicked(self, _strip_index):
        note = 0x20 + _strip_index
        self._midi_out.send_message([NOTE_ON, note, 127])
        self._midi_out.send_message([NOTE_OFF, note, 64])

    def handle_cursor(self, _cursor_clicked):
        if _cursor_clicked == "left":
            note = 0x62
            self._midi_out.send_message([NOTE_ON, note, 127])
            self._midi_out.send_message([NOTE_OFF, note, 64])
        elif _cursor_clicked == "right":
            note = 0x63
            self._midi_out.send_message([NOTE_ON, note, 127])
            self._midi_out.send_message([NOTE_OFF, note, 64])
        else:
            print("Unknown cursor button clicked")

    def set_subview_mode(self, _subview_type):
        if _subview_type == "Track":
            note = 0x28
        elif _subview_type == "Pan":
            note = 0x2A
        elif _subview_type == "EQ":
            note = 0x2C
        elif _subview_type == "Plug-In":
            note = 0x2B
        elif _subview_type == "Send":
            note = 0x29
        elif _subview_type == "Inst":
            note = 0x2D
        else:
            print("Unknown subview type ", _subview_type)
            return

        self._midi_out.send_message([NOTE_ON, note, 127])


if __name__ == '__main__':
    midi_out = rtmidi.MidiOut()
    midi_out.open_virtual_port("Not_a_mackie_device")
    midi_out_handler = MidiOutputHandler(midi_out)

    num_strips = 8
    main_window = tkinter.Tk()
    surface_state = setup_midi_callbacks(num_strips)
    draw_ui(main_window, surface_state, midi_out_handler)

    midi_in = rtmidi.MidiIn()
    midi_in.ignore_types(sysex=False)
    midi_in.open_virtual_port("IN_Relay_Mackie")
    handle_mackie_in_with_state = partial(handle_mackie_in, surface_state, midi_out_handler)
    midi_in.set_callback(handle_mackie_in_with_state)

    main_window.mainloop()
