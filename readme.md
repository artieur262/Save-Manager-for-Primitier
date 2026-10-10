# Primitier save manager

This project provides a small graphical interface to organise Primitier saves by world, instead of being limited to the game's slots.

## What the program does

- It shows the game slots (`save1.dat` to `save8.dat`) with, for each one, the world name, the seed, the mode (Creative or Survival), the date and the size.
- It lets you give a world a name: a `Mondes/<name>/` folder is created, with a `seed.txt` file containing the world's seed.
- It moves a save from a slot to its world's folder, which frees the slot.
- It copies a stored save back to a slot so you can play it again.
- It deletes a save by sending it to the Windows Recycle Bin.
- It offers a VR mode, with an enlarged interface that is usable in the headset.

## Running the program

```
py save_manager.py
```

You need Python 3.6 or newer, on Windows. There is nothing to install: the program only uses the standard library (including `tkinter`).

You can also run `save_manager.exe`, which works without Python. It is a snapshot of the script: if you change `save_manager.py`, rebuild it with:

```
py -m PyInstaller --onefile --windowed --name save_manager save_manager.py
```

The script and the exe can be stored in and launched from any folder: they find the current Windows user's `Documents\Primitier\Saves` folder on their own.

Avoid moving, copying or deleting saves while the game is running.

## How to use it

The window has two panels: the game slots on the left, your worlds on the right.

### Game slots (left)

- **Name this world**: gives a name to the world of the selected save and creates its folder. If the world already has a name, this renames it.
- **Move to its world →**: stores the save in its world's folder. If the world has no name yet, the program asks for one at that point. Double-clicking a slot does the same thing.
- **Delete**: sends the slot's save to the Recycle Bin, after confirmation.
- **Refresh**: reads the slots and worlds again, for example after saving in the game.

### My worlds (right)

Each world is shown with its seed, and expands to show the saves stored in it.

- **← Copy to a slot**: copies the selected save to the slot of your choice. The stored save stays in the world. If the slot is already in use, the program asks for confirmation before overwriting it.
- **Rename**: renames the world (and its folder).
- **Delete**: sends the selected stored save to the Recycle Bin, after confirmation. The world's folder and its `seed.txt` stay in place.
- **Open folder**: opens the world's folder in Windows Explorer.

### VR mode

The **VR mode** button, at the top right, turns on or off an interface designed for the headset:

- text and buttons are enlarged;
- a wide scrollbar appears next to each list;
- the window is maximised.

The mode is not remembered: the program always opens in normal mode.

The confirmation windows (Yes / No) are Windows' own and keep their normal size. Typing a world name or a slot number requires a keyboard.

## How saves are organised

A world is identified by its seed. A save always goes into the folder of the world with the same seed: it cannot be stored in the wrong world.

```
Saves/
├── save1.dat ... save8.dat      game slots
└── Mondes/
    └── <world name>/
        ├── seed.txt             the world's seed
        └── save_2026-07-06_04h47.dat
```

- A stored save is renamed after its last-modified date. If two saves have the same date, a number is appended (`_2`, `_3`...).
- To add a world by hand, create a folder in `Mondes/` with a `seed.txt` containing the seed.
- A folder without a valid `seed.txt` is ignored by the program.

## Save format

The `.dat` files are gzip-compressed JSON. The program only reads the beginning of the file, where the seed (`"seed"`) and the mode (`"isCreativeMode"`) are found. It never modifies the contents of a save.

## Settings

A few constants at the top of `save_manager.py`:

| Constant | Purpose | Value |
|---|---|---|
| `NOMBRE_SLOTS` | Number of slots shown | `8` |
| `DOSSIER_SAVES` | Folder of the game's saves | `Documents\Primitier\Saves` |
| `DOSSIER_MONDES` | Folder where worlds are stored | `Saves\Mondes` |
| `ECHELLE_VR` | Magnification in VR mode | `1.75` |
| `LARGEUR_DEFILEMENT_VR` | Scrollbar width in VR mode (pixels) | `40` |
