# Moving files between Windows and WSL

Recordings arrive from Windows; the XML goes back to Windows for Premiere. Both
directions go through `win-bridge`, which exposes exactly two Windows folders and
nothing else.

This machine has `automount` disabled in `/etc/wsl.conf`, so no Windows drive appears
on its own, and `interop` is disabled too, so Windows executables cannot be launched
from inside WSL — everything below is pure Linux.

| Windows | Inside WSL | Access |
| --- | --- | --- |
| `C:\raw` | `/mnt/win-raw` | read-only |
| `C:\xml` | `/mnt/win-xml` | read-write |

The rest of `C:` is not hidden from WSL, it is absent: nothing else is mounted, and
`/mnt/win-raw/..` is `/mnt`, not the drive root.

## Install, once

```bash
sudo ~/eng/running/install-win-bridge.sh
```

This copies `running/win-bridge` to `/usr/local/sbin/` as a root-owned file and adds
one line to `/etc/sudoers.d/win-bridge`:

```
<your-user> ALL=(root) NOPASSWD: /usr/local/sbin/win-bridge
```

## Mount, once per WSL session

```bash
sudo win-bridge mount
```

No password: that is what the sudoers line above buys. The mounts survive until
`wsl --shutdown` or a reboot, not until the next file. To see what is up:

```bash
sudo win-bridge status
```

## Windows → WSL

A new recording and its script are dropped into `C:\raw` from Explorer, then copied
into the project:

```bash
cp "/mnt/win-raw/Sequence 07.mp4" ~/eng/recordings/
cp "/mnt/win-raw/text_for_Sequence 07.txt" ~/eng/recordings/
```

`/mnt/win-raw` is mounted read-only, so nothing in this direction can write back over
the originals — a mistyped `cp` fails instead of overwriting a take.

## WSL → Windows

The rendered sequence, so Premiere can import it:

```bash
cp ~/eng/out/sequence.xml /mnt/win-xml/
```

A whole directory needs `-r`:

```bash
cp -r ~/eng/out /mnt/win-xml/
```

The copy is the whole of it — write, then stop. `/mnt` is fenced off from the agent
by deny rules in `~/.claude/settings.json` (`Read(//mnt/**)`, `Bash(ls /mnt/*)`,
`Bash(find /mnt/*)`), so listing the folder, `stat`-ing the file, or reading back what
was just written is refused, and a `cp` with `&& ls` on the end is refused whole
rather than in part. `cp` exits non-zero if the folder is unmounted or not writable,
so a silent `cp` is what a successful copy looks like from this side. There is no
second confirmation to go and get.

The two folders carry different rights, and not the same ones for everybody:
`/mnt/win-raw` is mounted read-only, so nobody writes to it; `/mnt/win-xml` is
mounted read-write, but the deny rules take the reading back, so to the agent it is
write-only.

## Unmount

```bash
sudo win-bridge umount
```

`target is busy` means a shell is sitting inside the mount — `cd ~` first, then
unmount.

## Changing which folders are bridged

The two Windows paths are hardcoded near the top of `running/win-bridge`, and the
script takes no path argument. That is deliberate: the sudoers rule runs it without a
password, so a script that accepted a path would be a password-free mount of anything
on the drive.

Editing the repo copy is not enough — `sudo` runs the installed copy under
`/usr/local/sbin/`. Edit `running/win-bridge`, then re-run the installer.

## What this does and does not fence off

The Windows side is closed except for the two folders. The agent cannot reach
`C:\Users`, other drives, or removable media; it cannot mount them either, because
every `sudo` other than `win-bridge` still asks for a password, and `win-bridge`
itself is root-owned, so its hardcoded paths cannot be edited from the account the
agent runs as.

The Linux side is not fenced off. The agent runs as your own account and can read and write
anything in that home directory. Closing that too would mean running the agent as a
separate user.

## Translating a path

`C:\raw\Sequence 07.mp4` becomes `/mnt/win-raw/Sequence 07.mp4`: the folder prefix
maps per the table above, backslashes become forward slashes, and a path containing
spaces is quoted.

## Where the project's files live

- Recordings and scripts go in `~/eng/recordings/`.
- `sequence.xml`, `sequence.report.txt` and `sequence.analysis.json` are written to
  `~/eng/out/`.

Premiere needs the XML and the MP4 on the Windows side, and the bridge puts them in
different folders — the XML in `C:\xml`, the recording still in `C:\raw`. The XML
references the recording by bare filename, so the relink prompt will ask for it. That
prompt is answered by hand, in Premiere, by the person importing — point it at
`C:\raw` once and Premiere finds the rest. Copying the MP4 into `C:\xml` alongside
the XML would avoid the prompt, at the cost of a second copy of a large file; we take
the prompt.

## If Explorer is preferred

The WSL filesystem is also reachable from Windows at
`\\wsl.localhost\<DISTRO>\home\<user>\eng\media` — `wsl -l -v` gives the exact distro
name and shows whether it is running, which it must be for the path to resolve. That
route is independent of the bridge and of the `wsl.conf` settings, but it depends on
the WSL network redirector, which is the part that tends to fail.
