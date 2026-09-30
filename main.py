# /// script
# dependencies = [
#   "pygame-ce",
# ]
# ///
import asyncio

import pygame  # noqa: F401 - pygbag scans main.py for this to load pygame-wasm

from game import Game


def main():
    asyncio.run(Game().run())


if __name__ == "__main__":
    main()
