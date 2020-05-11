import datetime

import gd
import pypresence

__version__ = "0.1.4"


def get_timestamp() -> int:
    return int(datetime.datetime.now().timestamp())


CLIENT_ID = 704721375050334300
GD_PROCESS = "GeometryDash.exe"
LOOP = gd.utils.acquire_loop()
MESSAGES = {
    gd.memory.Scene.MAIN: "Idle",
    gd.memory.Scene.SELECT: "Selecting level",
    gd.memory.Scene.EDITOR_OR_LEVEL: "Watching level info",
    gd.memory.Scene.SEARCH: "Searching levels",
    gd.memory.Scene.LEADERBOARD: "Browsing leaderboards",
    gd.memory.Scene.ONLINE: "Online",
    gd.memory.Scene.OFFICIAL_LEVELS: "Selecting official level",
}
START = get_timestamp()


client = gd.Client(loop=LOOP)
memory = gd.memory.Memory(GD_PROCESS)
presence = pypresence.AioPresence(str(CLIENT_ID), loop=LOOP)


def parse_difficulty(level: gd.typing.Optional[gd.Level]) -> str:
    if level is None:
        return "na"

    parts = level.difficulty.name.lower().split("_")

    if level.is_epic():
        parts.append("epic")

    elif level.is_featured():
        parts.append("featured")

    return "-".join(parts)


@gd.tasks.loop(seconds=1, loop=LOOP)
async def main_loop() -> None:
    global START

    try:
        memory.reload()

    except RuntimeError:
        START = get_timestamp()
        await presence.clear()
        return

    scene = memory.get_scene()
    best_record = memory.get_normal_percent()
    editor_object_count = memory.get_object_count()
    level_id = memory.get_level_id()
    level_name = memory.get_level_name()
    level_type = memory.get_level_type()
    level = None

    if level_type == gd.memory.LevelType.NULL:
        if memory.is_in_editor():
            state = f"In Editor ({editor_object_count} objects)"
            details = "Editing level"

        else:
            state = f"In {scene}"
            details = MESSAGES.get(scene, "Unknown")

    else:
        state = f"{level_name} ({best_record}% best) [ID: {level_id}]"

        if level_type == gd.memory.LevelType.OFFICIAL:
            level = gd.Level.official(level_id, client=client)
            details = "Playing official level"

        elif level_type == gd.memory.LevelType.EDITOR:
            level = gd.Level(client=client)
            details = "Playtesting level"

        else:
            try:
                level = await client.get_level(level_id, get_data=False)
            except gd.ClientException:
                pass

            details = "Playing online level"

    difficulty = parse_difficulty(level)

    await presence.update(
        pid=memory.process_id,
        state=state,
        details=details,
        start=START,
        large_image="gd",
        large_text="gd.rpc",
        small_image=difficulty,
        small_text=difficulty,
    )


async def connect() -> None:
    await presence.connect()


def run() -> None:

    print(f"Running gd.rpc v.{__version__}... Press [Ctrl + C] to stop.")

    LOOP.run_until_complete(connect())

    main_loop.start()

    try:
        LOOP.run_forever()
    except KeyboardInterrupt:
        gd.utils.cancel_all_tasks(LOOP)
        presence.close()


if __name__ == "__main__":
    run()
