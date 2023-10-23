# gravitational tracker

import datetime
import os
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import click
import numpy as np
from astropy.time import Time
from gwpy.table import EventTable
from rich import print as pprint
from rich.console import Console

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
import pygame as pg  # noqa: E402

# Initialize Pygame
pg.init()
pg.mixer.init(channels=12)

# Sound Uhrzeitabhaengig machen, zur nachvollziehbarkeit

# Kurz Website erklären https://gracedb.ligo.org/superevents/public/O4/


@dataclass
class SoundFile:
    name: Path
    sound: pg.mixer.Sound

    def __repr__(self) -> str:
        return f'SoundFile(name="{str(self.name)}",sound={hex(id(self.sound))},({self.sound.get_length()}s))'


def to_sound(path: Path):
    sf = SoundFile(path, pg.mixer.Sound(str(path)))
    print(f"Found sound {sf.name} ({sf.sound.get_length()}s): {sf.sound}")
    return sf


@dataclass
class SoundInChannel:
    sf: SoundFile
    channel: pg.mixer.Channel
    volume: float = None
    pan: float = None
    loops: int = None
    fadeout: None = None
    start_time_monotonic_ns: int = None
    start_time_ns: int = None

    def __repr__(self):
        """Just like the default __repr__ but supports reformatting some values."""

        def time_convert(name, value):
            if name == "start_time_monotonic_ns":
                now = time.monotonic_ns()
                ns_since_start = now - value
                return f"{ns_since_start / 1e9!r}"
            elif name == "start_time_ns":
                value = datetime.datetime.fromtimestamp(value / 1e9).isoformat()
                return f"{value!r}"
            else:
                return f"{value!r}"

        fields = (
            f"{name}={time_convert(name, value)}"
            for field in self.__dataclass_fields__.values()
            if field.repr
            # This just assigns shorter names to code to improve readability above.
            # It's like the new assignment operator.
            for name, value in ((field.name, self.__getattribute__(field.name)),)
        )
        return f'{self.__class__.__name__}({", ".join(fields)})'


main_sounds_folder = Path() / "sounds" / "1_Haupt-Loops 1min"

M1a = to_sound(main_sounds_folder / "M1a_Sine140-loop.mp3")
M1b = to_sound(main_sounds_folder / "M1b_Sine140,5-loop.mp3")
M2a = to_sound(main_sounds_folder / "M2a-Sine139,5-loop.mp3")
M2b = to_sound(main_sounds_folder / "M2b_Sine139-loop.mp3")
M3a = to_sound(main_sounds_folder / "M3a_Sine90-50-loop.mp3")
M3b = to_sound(main_sounds_folder / "M3b_Sine90,5-50-loop.mp3")

M1 = M1a, M1b
M2 = M2a, M2b
M3 = M3a, M3b

T44_00_50 = to_sound(main_sounds_folder / "Triangle_44,00-50-loop.mp3")
T44_22_70 = to_sound(main_sounds_folder / "Triangle_44,22-ca70-loop.mp3")
T44_23_100 = to_sound(main_sounds_folder / "Triangle_44,23-100-loop.mp3")
T44_25_85 = to_sound(main_sounds_folder / "Triangle_44,25-ca85-loop.mp3")

instruments_path = Path() / "sounds" / "2_Instrumente" / "Instrumente 2 sec loops-ohne Pause"

T200_70 = to_sound(instruments_path / "Triangle_200-ca70 2 sec oh.mp3")
T201_30 = to_sound(instruments_path / "Triangle_201_ca30 2 sec oh.mp3")
T202_20 = to_sound(instruments_path / "Triangle_202_ca20 2 sec oh.mp3")
T203_70 = to_sound(instruments_path / "Triangle_203_ca70 2 sec oh.mp3")

for sf in [*M1, *M2, *M3]:
    print(f"Found sound {sf.name} ({sf.sound.get_length():.4}s): {sf.sound}")

# Triangle_44,22-ca70�-loop mittig drüberlegen

# Create a custom event for music end
MUSIC_END = pg.USEREVENT + 1
pg.mixer.music.set_endevent(MUSIC_END)

channel_mapping = {}
next_channel_id = 0


def _key_find(d: dict, v):
    for k, vv in d.items():
        if vv.channel == v:
            return k
    return None


def play_panned(sound_file: SoundFile, volume, pan, loops=-1):
    if not 0 <= volume <= 1:
        Console().log("Warn: Volume must be between 0 and 1. Setting to 0.2!")
        volume = 0.2
    if not -1 <= pan <= 1:
        Console().log("Warn: Pan must be between -1 and 1. Setting to 0!")
        pan = 0

    name = sound_file.name
    sound = sound_file.sound
    # print("search channel")
    channel = pg.mixer.find_channel()
    if not channel:
        print("All channels taken.")
        return
    else:
        if channel not in channel_mapping.values():
            global next_channel_id
            channel_mapping[next_channel_id] = SoundInChannel(sound_file, channel)
            next_channel_id += 1
    # print("found channel")

    channel_id = _key_find(channel_mapping, channel)

    left_panning = 0.5 - (pan / 2)
    right_panning = 0.5 + (pan / 2)

    left_loudness = left_panning * volume
    right_loudness = right_panning * volume

    channel.set_volume(left_loudness, right_loudness)

    vol_str = [" "] * 11
    vol_steps = np.linspace(0, 1, num=11)
    for (i,), v in np.ndenumerate(vol_steps):
        if v < volume:
            vol_str[i] = "*"

    pan_str = [" "] * 11
    pan_steps = np.linspace(-1, 1, num=11)
    pan_str[np.abs(pan_steps - pan).argmin()] = "*"
    if pan_str[5] == " ":
        pan_str[5] = "|"

    print(
        f"[{''.join(vol_str)}] [{''.join(pan_str)}] Playing {name} on channel {channel_id} {str(channel)}."
        f"{volume:.3f}, {pan:.3f}, {left_loudness:.3f}, {right_loudness:.3f}."
    )

    res = channel.play(sound, loops=loops)
    channel_mapping[channel_id].start_time_monotonic_ns = time.monotonic_ns()
    channel_mapping[channel_id].start_time_ns = time.time_ns()
    channel_mapping[channel_id].volume = volume
    channel_mapping[channel_id].pan = pan
    channel_mapping[channel_id].loops = loops
    channel_mapping[channel_id].fadeout = 10000 * random.randint(0, 3)
    channel.fadeout(channel_mapping[channel_id].fadeout)
    channel.set_endevent(MUSIC_END)


def test_panned():
    name, sound = M1[0]

    play_panned(sound, 1, 0, name)
    time.sleep(4)
    play_panned(sound, 1, -0.5, name)
    time.sleep(4)
    play_panned(sound, 1, -1, name)
    time.sleep(4)
    play_panned(sound, 1, 1, name)
    time.sleep(4)
    sys.exit()


# test_panned()

console = Console()
console.rule("GW")


CATALOG = "GWTC-3-confident"

# events = EventTable.fetch_open_data(CATALOG)
# events.write("events.json", format='pandas.json')

events = EventTable.read("events.json", format="pandas.json")


## keys ['final_mass_source_upper', 'total_mass_source', 'mass_2_source_lower',
# 'mass_2_source', 'final_mass_source', 'p_astro', 'far', 'luminosity_distance',
# 'network_matched_filter_snr_upper', 'mass_1_source_upper', 'chirp_mass_source_lower',
# 'mass_1_source', 'chirp_mass_source_upper', 'final_mass_source_lower', 'chi_eff_upper',
# 'mass_1_source_lower', 'luminosity_distance_upper', 'luminosity_distance_lower', 'reference',
# 'total_mass_source_upper', 'catalog.shortName', 'version', 'jsonurl', 'GPS', 'chi_eff',
# 'p_astro_upper', 'total_mass_source_lower', 'redshift_lower', 'redshift_upper', 'chirp_mass_source',
# 'far_upper', 'network_matched_filter_snr', 'chirp_mass_lower', 'commonName', 'far_lower',
# 'mass_2_source_upper', 'network_matched_filter_snr_lower', 'chirp_mass_upper', 'p_astro_lower',
# 'chi_eff_lower', 'redshift', 'chirp_mass'])


# sound-Auswahl und Häufigkeit je nach Abstand zur Quelle, Massen …
# Massendifferenz -> Panning

# 4 bis 8 letzte GW

# Entfernung / Lokalität darstellen (rechts/links)

# Pink noise drüber legen

@click.command()
def main():
    clock = pg.time.Clock()
    running = True

    while running:
        clock.tick(60)
        pprint(channel_mapping)
        for event in pg.event.get():
            print(event)
            for i, chan in list(channel_mapping.items()):
                if not chan.channel.get_busy():
                    del channel_mapping[i]

        # Select random event
        event = random.choice(events)

        m1 = event["mass_1_source"]
        m2 = event["mass_2_source"]
        chirp_m = event["chirp_mass"]
        m_total = event["mass_1_source"] + event["mass_2_source"]
        luminosity_distance = event["luminosity_distance"]
        short_name = event["catalog.shortName"]
        common_name = event["commonName"]
        GPS_time = event["GPS"]
        # detector = events['detector']

        t_iso = Time(GPS_time, format="gps")
        t_utc = Time(t_iso, format="iso", scale="utc")

        console.print(
            f"[black]{t_utc}[/] [b]{common_name}[/b] distance {luminosity_distance}. M1 [red]{m1}[/] M2 [red]{m2}[/]"
        )

        # vol from 0 to 1
        volume = luminosity_distance / 8000.0

        sf_left, sf_right = random.choice([M1, M2, M3])

        # m1
        # pan from -1 to 1
        panning = -1
        play_panned(sf_left, volume=volume, pan=panning)

        # m2
        # pan from -1 to 1
        panning = 1
        play_panned(sf_right, volume=volume, pan=panning)

        time.sleep(5)
        continue

        while True:
            # i = random.randint(10)
            overlay = [
                T44_00_50,
                T44_22_70,
                T44_23_100,
                T44_25_85,
            ]
            ov = random.choice(overlay)
            play_panned(ov, volume=0.2, pan=0.1, loops=4)

            time.sleep(5)

            instrument = [
                T200_70,
                T201_30,
                T202_20,
                T203_70,
            ]

            inst = random.choice(instrument)
            play_panned(inst, volume=0.5, pan=0, loops=4)

            time.sleep(5)

        time.sleep(100)

    pg.quit()


if __name__ == "__main__":
    main()

    while True:
        # break

        time.sleep(random.randint(0, 4))

        # vol from 0 to 1
        volume = random.random()
        # pan from -1 to 1
        panning = random.random() * 2 - 1

        name, sound = random.choice(sounds)

        play_panned(sound, volume=volume, pan=panning, name=name)

    print(events)
    breakpoint()

    # Quit Pygame
    pg.quit()
