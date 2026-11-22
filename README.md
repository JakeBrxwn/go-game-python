# Go Python

Play the board game Go in a window or in a terminal: against a friend,
against a bot, or watch bots play each other.

![The game window mid-match: a 13 x 13 board, with each player's area beside it](https://github.com/JakeBrxwn/go-game-python/releases/latest/download/go-python-screenshot.png)

Go Python started as a college project from when I first began my journey
as an engineer over six years ago, and this fork gives it new life as a
desktop app.

## Features

- A game window with a menu, a setup screen, and each player's score as
  the game goes.
- Original synthesized sound in the window. A wooden tap marks a stone,
  a high bell marks a capture, and a lower descending bell marks the loss
  of your stones. A horn phrase celebrates a win and soft drums mark defeat.
  With several humans or while watching bots, everyone hears the capture
  and winner cues. The window also works without an audio device.
- A terminal game, where you type moves like `D4`. It is a separate,
  lighter app that never loads the window code.
- 2 to 4 players, each one a person, a random bot or a smart bot.
- Watch bots play each other, in the window or the terminal.
- Boards from 6 x 6 to 30 x 30.
- The simple ko rule or superko. Suicide is never allowed.
- Area scoring: your stones plus the empty points only you surround.
- Hints in the terminal: type `hint` and the smart bot suggests a move.
- Downloads for Linux, Windows and macOS that need no Python.

## Download and run

Each [release](https://github.com/JakeBrxwn/go-game-python/releases/latest)
has the game window and the terminal game for each OS, as single files:

| OS | Game window | Terminal game |
|---|---|---|
| Linux, x86-64 | `go-python-linux-x86_64` | `go-python-tui-linux-x86_64` |
| Windows, x86-64 | `go-python-windows-x86_64.exe` | `go-python-tui-windows-x86_64.exe` |
| macOS, Apple silicon | `go-python-macos-arm64` | `go-python-tui-macos-arm64` |

On any other system, such as an Intel Mac, Linux on ARM or Windows on ARM,
[install with pipx](#install-with-pipx) instead.

The files are not signed, as signing needs paid certificates, so Windows and
macOS warn you the first time. The steps below get past the warning.

### Linux

The Linux files are built on Ubuntu 22.04, so they need glibc 2.35 or newer
(Ubuntu 22.04, Debian 12, Fedora 36, or later); on older systems, install
with pipx. In a terminal, in the folder you downloaded to:

```sh
chmod +x go-python-linux-x86_64
./go-python-linux-x86_64
```

The terminal game is the same: `chmod +x go-python-tui-linux-x86_64`, then
`./go-python-tui-linux-x86_64`.

### Windows

Your browser may warn that the file is not commonly downloaded: choose to
keep it. Then double-click `go-python-windows-x86_64.exe`. If Windows says
"Windows protected your PC", click **More info**, then **Run anyway**.

Double-clicking `go-python-tui-windows-x86_64.exe` opens the terminal game
in a console window. You can also start it from PowerShell, in the folder
you downloaded to:

```powershell
.\go-python-tui-windows-x86_64.exe
```

### macOS

macOS refuses to open unsigned files downloaded from the internet. In
Terminal, in the folder you downloaded to:

```sh
chmod +x go-python-macos-arm64
xattr -d com.apple.quarantine go-python-macos-arm64
./go-python-macos-arm64
```

`xattr -d` removes the mark macOS puts on downloaded files, which is what
blocks them. If it says `No such xattr`, the file had no mark, so carry on.
The terminal game takes the same three steps with
`go-python-tui-macos-arm64`.

### Check a download

`SHA256SUMS`, in the same release, lists the SHA-256 hash of every file. On
Linux, this checks every file you downloaded, in the folder that holds them
and `SHA256SUMS`:

```sh
sha256sum --check --ignore-missing SHA256SUMS
```

On macOS, `shasum -a 256 go-python-macos-arm64` prints a file's hash. On
Windows, this PowerShell command prints it in lower case, as `SHA256SUMS`
writes it: `(Get-FileHash go-python-windows-x86_64.exe).Hash.ToLower()`.
Compare it with the file's line in `SHA256SUMS`.

## Install with pipx

[pipx](https://pipx.pypa.io/) installs Python apps in their own environment.
With Python 3.14, pipx and git installed, this gives you both commands,
`go-python` for the window and `go-python-tui` for the terminal. On
Windows, write `--python 3.14` in place of `--python python3.14`, here and
below.

```sh
pipx install --python python3.14 git+https://github.com/JakeBrxwn/go-game-python.git
```

To install from a downloaded release instead, use the wheel, the file that
ends in `.whl`. Run this in the folder you downloaded it to, with the
version in your file's name:

```sh
pipx install --python python3.14 go_python-0.1.0-py3-none-any.whl
```

## How to play

### The rules

- Players take turns placing one stone where two lines cross, or passing.
  Black moves first, then White, then Red and Blue in games of 3 or 4.
- A chain of stones with no empty point next to it is captured and removed.
- Suicide is not allowed: you cannot play a stone that would leave your own
  chain with no empty point next to it, unless it captures first.
- Ko: under simple ko, no move may bring back the board as it was one move
  ago. Under superko, no move may bring back any earlier board.
- The game ends when every player passes in a row. The most area wins:
  your stones plus the empty points that only your stones surround. A game
  also ends after 3 x size x size moves and passes, so a 19 x 19 game stops
  at 1,083.

### In the window

Run `go-python`, or open the downloaded game window.

- **Menu:** Play, Watch bots or Quit.
- **Setup:** pick the board size (− and +, or 9 x 9, 13 x 13 and 19 x 19),
  the ko rule, the number of players, and who sits in each seat: Human,
  Random bot or Smart bot. Then click **Start game**, or **Start watching**
  when every seat is a bot.
- **Playing:** a faint stone follows the mouse to show where a click plays.
  Let go of the mouse button to place it. **Pass** passes your turn.
  **Leave match (Esc)** asks once to make sure, then press Esc or click it
  again to leave. If a click does nothing, a note on the right says why.
- **Game over:** small squares mark owned empty points in each player's
  colour; shared empty points stay unmarked. The side panel shows the winner
  and the score. **Play again** starts a new match with the same board and
  players, and **Menu** goes back.

### In the terminal

Run `go-python-tui`, or open the downloaded terminal game. It asks
questions, and Enter keeps the answer in brackets.

- **Menu:** type `1` to play, `2` to watch bots, or `3` to quit.
- **Setup:** the board size, the ko rule (`simple` or `superko`), then a
  seat for each player: `human`, `random` or `smart`. Red and Blue start as
  `none`, which ends the list of players.
- **Your turn:** the board is printed with column letters and row numbers.

| Type | To |
|---|---|
| `D4` | Play at column D, row 4. Case does not matter. There is no column I, as on real boards. Boards over 25 wide go on to `AA`, `AB` and so on. |
| `pass` | Pass your turn. |
| `hint` | Ask the smart bot for a move. Nothing is played. |
| `quit` | End the match with no winner. |

Ctrl+C stops a match you are watching. On your turn, Ctrl+C or Ctrl+D ends
the match with no winner, like `quit`. During setup either one goes back to
the menu, and at the menu either one quits. The terminal needs UTF-8 to show
the stones, which almost every terminal has.

## Bot mode

There are two bots:

- **Random bot** plays a random legal move, but never fills its own eye and
  never takes a ko.
- **Smart bot** rates every move by the chains next to it: it captures,
  saves its own stones, presses on weak enemy chains and keeps off the edge.
  The evals hold it to winning at least 90% of 9 x 9 games against Random
  bot.

To play against a bot, set any seat to Random bot or Smart bot in setup. To
watch bots play, choose **Watch bots** in the menu: the window starts you
on 9 x 9 with Smart bot as Black and Random bot as White, and you can
change any of these before you start.

To play many bot games with no display and see the totals, use the `bots`
test command from [Development](#development).

## Build from source

You need Python 3.14 and git. On Debian or Ubuntu, also install Python's
venv module with `sudo apt install python3.14-venv`, which those systems
leave out. On Windows, run the commands in PowerShell,
with `py -3.14 -m venv .venv` in place of the `python3.14` line and
`.venv\Scripts\Activate.ps1` in place of the `source` line. If PowerShell
refuses to run that script, run `Set-ExecutionPolicy -Scope Process
RemoteSigned` first; it lasts until you close the window.

```sh
git clone https://github.com/JakeBrxwn/go-game-python.git
cd go-game-python
python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
go-python
```

`requirements.txt` installs the game in editable mode, along with the test
tools, so your changes to `src/` take effect when you next run it.

Building the standalone apps needs binutils on Linux, so install it first
if you lack it: `sudo apt install binutils` or `sudo dnf install binutils`.
To build the two apps for your OS into `dist/`, then check them the way the
release does:

```sh
pip install -e ".[release]"
python scripts/freeze.py
python scripts/smoke.py
```

The smoke test takes about a minute and needs no display, as it uses SDL's
dummy drivers. It checks each app's version, opens the menu and, except on
Windows, checks it quits when asked. It plays one whole bot match in the
window and one in the terminal game, and except on Windows, sends Ctrl+C's
signal to each app's launcher midway, which must not pass it on: the game
gets Ctrl+C from the terminal already. It also runs the `bots` command and
checks that the terminal game holds no pygame.

## Development

With the environment from [Build from source](#build-from-source)
activated:

```sh
python -m pytest
python -m pytest evals -s
ruff check .
mypy
```

- `python -m pytest` runs the unit tests in `tests/`, in about 30 seconds.
- `python -m pytest evals -s` runs the evals in `evals/` and prints their
  numbers, in about 3 minutes: the rules against
  [sgfmill](https://github.com/mattheww/sgfmill), invariants over random
  games, the bots' strength, and speed.
- `ruff check .` and `mypy` are the lint and type checks.

`go-python` has three commands for testing that skip the menu:

- `go-python gui` starts one match in the window, and `go-python tui`
  plays one in the terminal. Both take `-s` or `--size` (6 to 30),
  `--ko simple` or `--ko super`, and `--seats` with 2 to 4 seats in turn
  order, each `human`, `random` or `smart`. For example:
  `go-python gui -s 9 --ko super --seats human,smart,random`. With
  `--close-at-end`, the window closes when the match ends and prints how
  it ended, which the smoke test uses.
- `go-python bots` plays bot games with no display and prints the totals,
  for example `go-python bots -n 20 -s 9 -1 smart -2 random`.

Run any command with `--help` for its options.

Every pull request runs `.github/workflows/ci.yml`: the lint and type
checks, the tests on Linux, Windows and macOS, the evals, and the package
smoke test, which builds both apps on each OS and runs `scripts/smoke.py`.

## Architecture

```text
cli.py      the commands, and the only code that reads arguments
 ├─ gui.py  the window, with pygame
 └─ tui.py  the terminal game, with input() and print()
     │
match.py    one match: its settings (GameConfig), seats, turns and result,
 │          and the only code that changes the game
 ├─ bot.py    Random and Smart
 └─ go.py     the rules: moves, captures, ko, scoring
     └─ board.py  the grid of stones
```

The window and the terminal game never change a game themselves: they ask
`Match` to play a move, pass or let a bot move, then show what it says. So
both frontends play by the same rules, and bots work the same in each.

## Release process

1. Set `__version__` in `src/go_python/__init__.py`, and merge that to
   `main` through a pull request.
2. Tag the merged commit on `main` and push the tag:

   ```sh
   git switch main
   git pull
   git tag v0.1.0
   git push origin v0.1.0
   ```

3. `.github/workflows/release.yml` checks that the tag is `v` followed by
   the version in the code, and is on `main`. Then it runs the whole CI,
   which builds and smoke-tests both apps on each OS. Only then does it
   publish a GitHub Release with the six apps, the wheel, the sdist, the
   screenshot above, `THIRD_PARTY_LICENSES.txt`, the source of the LGPL
   parts the window apps bundle, and `SHA256SUMS`.

For a pre-release, set a version like `0.1.0rc1` and push the tag
`v0.1.0rc1` from any branch. Its files carry that version, so pip never
mistakes it for `0.1.0`.

## Credits and licence

The original game was built by a team of four:

- **Marcus Longo**, the game window
- **Aditya Singh**, testing
- **Daniel Fields**, the terminal game
- **Jake Brown**, the bots

I picked it back up to play around with it, and this version builds on
their work. The rules now follow Go on ko and suicide, and one `Match` core
runs every game, so the window and the terminal game both offer a menu,
bots in any seat and watching bots play, and check board sizes and player
counts the same way. The smart bot is rewritten and wins at least 90% of
9 x 9 games against the random one, and the apps download with no Python
needed. Tests and builds run on three operating systems on every change,
and evals check the rules and the bots.

Go Python is released under the [MIT licence](LICENSE). The downloaded apps
also hold Python, pygame-ce, SDL and other software, each under its own
licence: [`THIRD_PARTY_LICENSES.txt`](THIRD_PARTY_LICENSES.txt), here, in
each release and inside each app, gives every licence and where to get the
source.
