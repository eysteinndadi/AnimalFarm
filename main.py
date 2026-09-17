import asyncio

from game import Game


def main():
    asyncio.run(Game().run())


if __name__ == "__main__":
    main()
