"""Memory mediation between the projects of one machine: the reservations ledger.py makes and hub.py shows.

One file per machine, ~/.foreman/memoria.json (FOREMAN_MEMORIA names another path; memoria.lock sits beside it):

  {"reservas": [{"projeto", "nome", "rotulo", "gb", "desde", "renovada"}],
   "pedidos": [{"projeto", "nome", "gb", "copias", "desde", "renovado"}],
   "prioridades": {"<projeto>": {"nome", "prioridade"}}}

A project is the normcase'd real path of its main worktree (key; ledger.py finds it through git, so a front's
ledger in a worktree is the same project), nome its folder name. A reservation is the peak of one heavy job
(preparing or verifying) under a label (LABEL: a dev task id, qa, or manager:<task>; QA matches the labels of a qa's copies, all freed by its add). Each
ledger.py command of the
project but status --json (the mod's and the hub's read) renews its reservations (renew; never creates the file);
one not renewed for 2 h no longer counts, and a request (pedido) not renewed for 5 min neither: load drops both, and the
next write removes them. Times are UTC ISO to the second; FOREMAN_MEMORIA_AGORA fixes the clock (tests).

reserve grants labels in order while fits(free - what the other projects reserve) allows, counting the others'
reservations whole (shortcut: a running job's memory is then counted twice, in the free memory and in its
reservation, so a project waits longer than needed, never crashes another; upgrade to discounting what is already in
use if the waits weigh on the deliveries' clock). A project's own reservations are not subtracted: the free memory
already shows its running copies. A request of another project with a higher priority, or the same priority and an
older desde, makes this one wait even when memory fits, except for a label manager:<task> of a task it already holds (decided
label by label): the suite that checks a held task's report finishes that task, or it would never free what the other
waits for, and granting it keeps the project's place in the queue. A new job of a project that holds memory waits its
turn like any other. A request that would not fit even with every other
reservation released is refused at once and never queued. Only a waiting caller (esperando) writes or drops the
project's request; a grant drops it.

A file that is not a JSON object of that shape (gb a number, copias an integer) raises Corrupt and is never overwritten. Writers hold memoria.lock
(lock: created exclusively, its owner's token inside, taken over after 30 s, removed only by the token that wrote it;
hub.py's hub.lock uses the same lock).
"""
import contextlib, datetime, json, os, re, tempfile, time

RESERVA_TTL = 2 * 3600  # seconds a reservation lives with no renewal
PEDIDO_TTL = 300  # seconds a request lives with no renewal
LABEL = re.compile(r"[A-Za-z0-9._:-]{1,60}")
QA = re.compile(r"qa(?:[-_:.].*)?")  # the labels of a qa's copies: qa, qa-full-1, qa:ciclo6


def number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


class Busy(Exception):
    pass


class Corrupt(Exception):
    pass


def path():
    return os.environ.get("FOREMAN_MEMORIA") or os.path.join(os.path.expanduser("~"), ".foreman", "memoria.json")


def key(root):
    return os.path.normcase(os.path.realpath(root))


def now():
    fixed = os.environ.get("FOREMAN_MEMORIA_AGORA")
    if fixed:
        return datetime.datetime.fromisoformat(fixed.replace("Z", "+00:00")).astimezone(datetime.timezone.utc)
    return datetime.datetime.now(datetime.timezone.utc)


def iso(t):
    return t.isoformat(timespec="seconds")


def age(stamp, at):
    try:
        return (at - datetime.datetime.fromisoformat(stamp)).total_seconds()
    except (TypeError, ValueError):
        return float("inf")


def drop(lock_path, token):
    """Removes the lock file only while it still holds token: a taken-over lock is never deleted by its old owner."""
    token = token.encode("utf-8") if isinstance(token, str) else token
    for _ in range(100):  # a waiter's stat can hold the file for a moment on Windows
        try:
            with open(lock_path, "rb") as f:
                if f.read() != token:
                    return
            os.remove(lock_path)
            return
        except FileNotFoundError:
            return
        except OSError:
            time.sleep(0.05)


@contextlib.contextmanager
def lock(lock_path, wait=10, stale=30):
    """One writer at a time: lock_path created exclusively, retried for wait seconds (Busy after), removed after."""
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    token = f"{os.getpid()} {os.urandom(8).hex()}"
    end, denied = time.time() + wait, 0
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            denied = 0
        except PermissionError:  # Windows says "denied" for a file that is being deleted; with no file, retry briefly
            denied = 0 if os.path.exists(lock_path) else denied + 1
            if denied > 20:
                raise
        with contextlib.suppress(OSError):
            if time.time() - os.path.getmtime(lock_path) > stale:
                with open(lock_path, "rb") as f:
                    old = f.read()
                drop(lock_path, old)  # deletes only the content just read, so a newer taker's lock stays
        if time.time() > end:
            raise Busy(lock_path)
        time.sleep(0.05)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(token)
        yield
    finally:
        drop(lock_path, token)


def valid(d):
    return (isinstance(d, dict) and isinstance(d.get("reservas", []), list) and isinstance(d.get("pedidos", []), list)
            and isinstance(d.get("prioridades", {}), dict)
            and all(isinstance(x, dict) for x in d.get("reservas", []) + d.get("pedidos", []))
            and all(isinstance(x, dict) for x in d.get("prioridades", {}).values())
            and all(number(x.get("gb")) for x in d.get("reservas", []) + d.get("pedidos", []))
            and all(isinstance(x.get("copias", 1), int) for x in d.get("pedidos", [])))


def load(at=None):
    """The file with the expired reservations and requests left out; an empty one when there is no file."""
    at = at or now()
    for attempt in range(20):
        try:
            with open(path(), encoding="utf-8") as f:
                d = json.load(f)
            break
        except FileNotFoundError:
            d = {}
            break
        except PermissionError:  # Windows: another process is replacing the file for a moment
            if attempt == 19:
                raise Corrupt(path())
            time.sleep(0.05)
        except (OSError, ValueError):
            raise Corrupt(path())
    if not valid(d):
        raise Corrupt(path())
    return {"reservas": [r for r in d.get("reservas", []) if age(r.get("renovada"), at) <= RESERVA_TTL],
            "pedidos": [p for p in d.get("pedidos", []) if age(p.get("renovado"), at) <= PEDIDO_TTL],
            "prioridades": d.get("prioridades", {})}


def save(d):
    target = path()
    os.makedirs(os.path.dirname(target), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="memoria.", suffix=".tmp", dir=os.path.dirname(target))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
            f.write("\n")
        for attempt in range(20):  # on Windows a reader holding the file makes the replace fail for a moment
            try:
                os.replace(tmp, target)
                break
            except PermissionError:
                if attempt == 19:
                    raise
                time.sleep(0.05)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


@contextlib.contextmanager
def changing(wait=10):
    """Load, change and save as one step, under memoria.lock."""
    with lock(os.path.join(os.path.dirname(path()), "memoria.lock"), wait=wait):
        d = load()
        yield d
        save(d)


def others(d, projeto):
    return sum(r.get("gb") or 0 for r in d["reservas"] if r.get("projeto") != projeto)


def priority(d, projeto):
    value = (d["prioridades"].get(projeto) or {}).get("prioridade")
    return value if isinstance(value, (int, float)) else 0


def holders(d, projeto):
    return ", ".join(f"{r.get('nome')} {r.get('gb'):g} GB ({r.get('rotulo')})" for r in d["reservas"]
                     if r.get("projeto") != projeto) or "none"


def reserve(projeto, nome, rotulos, gb, free, fits, esperando=False):
    """(granted labels, reason, impossible): fits(free GB) is how many copies the project may run with that free."""
    at = now()
    with changing() as d:
        mine = priority(d, projeto)
        request = next((p for p in d["pedidos"] if p.get("projeto") == projeto), None)
        since = request["desde"] if request else iso(at)
        if esperando:
            d["pedidos"] = [p for p in d["pedidos"] if p.get("projeto") != projeto]
        reserved = others(d, projeto)
        if fits(free + reserved) < 1:
            return [], (f"{free:.1f} GB free and {reserved:g} GB reserved by other projects: one copy would not fit "
                        "even with them released"), True
        held = {r.get("rotulo") for r in d["reservas"] if r.get("projeto") == projeto}

        def finishing(label):  # manager:<task> of a task this project holds: the suite that lets it free the task
            task = label[len("manager:"):]
            return label.startswith("manager:") and ":" not in task and task in held

        done = [r for r in rotulos if finishing(r)]
        new = [r for r in rotulos if not finishing(r)]
        ahead = [p for p in d["pedidos"] if p.get("projeto") != projeto and (
            priority(d, p.get("projeto")) > mine or priority(d, p.get("projeto")) == mine and str(p.get("desde")) < since)]
        room = max(0, fits(free - reserved))
        granted = done[:room]
        if not ahead:
            granted += new[:room - len(granted)]
        if granted:
            if any(r in new for r in granted):  # the project's turn came: its request is answered
                d["pedidos"] = [p for p in d["pedidos"] if p.get("projeto") != projeto]
            elif esperando and new:  # only the finishing labels: the new jobs keep their place
                d["pedidos"].append({"projeto": projeto, "nome": nome, "gb": gb, "copias": len(new), "desde": since,
                                     "renovado": iso(at)})
            elif esperando and request:  # another caller's request of this project stays as it was
                d["pedidos"].append(request)
            d["reservas"] = [r for r in d["reservas"] if not (r.get("projeto") == projeto and r.get("rotulo") in granted)]
            d["reservas"] += [{"projeto": projeto, "nome": nome, "rotulo": r, "gb": gb, "desde": iso(at),
                               "renovada": iso(at)} for r in granted]
            return granted, f"reserved {gb:g} GB each (other projects reserve {reserved:g} GB)", False
        if esperando and new:
            d["pedidos"].append({"projeto": projeto, "nome": nome, "gb": gb, "copias": len(new), "desde": since,
                                 "renovado": iso(at)})
        elif esperando and request:  # finishing labels wait for memory, never for a turn: no request of their own
            d["pedidos"].append(request)
        if ahead:
            first = ahead[0]
            return [], (f"waits for {first.get('nome')} (priority {priority(d, first.get('projeto')):g}), asking "
                        f"since {first.get('desde')}"), False
        return [], f"other projects reserve {reserved:g} GB: {holders(d, projeto)}", False


def withdraw(projeto):
    """Drops the project's waiting request (a waiter that gave up)."""
    if not os.path.exists(path()):
        return
    with changing() as d:
        d["pedidos"] = [p for p in d["pedidos"] if p.get("projeto") != projeto]


def release(projeto, rotulo=None, family=None):
    """Drops the project's reservation with that label, or whose label family (a compiled pattern) matches; every
    reservation and its request with neither. The count."""
    if not os.path.exists(path()):
        return 0
    with changing() as d:
        before = len(d["reservas"])
        d["reservas"] = [r for r in d["reservas"] if not (r.get("projeto") == projeto and (
            family.fullmatch(str(r.get("rotulo"))) if family else rotulo is None or r.get("rotulo") == rotulo))]
        if rotulo is None and family is None:
            d["pedidos"] = [p for p in d["pedidos"] if p.get("projeto") != projeto]
        return before - len(d["reservas"])


def renew(projeto):
    """Renews the project's reservations; best effort, and never creates the file."""
    if not os.path.exists(path()):
        return
    try:
        with lock(os.path.join(os.path.dirname(path()), "memoria.lock"), wait=2):
            d = load()
            mine = [r for r in d["reservas"] if r.get("projeto") == projeto]
            if mine:
                for r in mine:
                    r["renovada"] = iso(now())
                save(d)
    except (Busy, Corrupt, OSError):
        pass


def set_priority(projeto, nome, value):
    with changing() as d:
        d["prioridades"][projeto] = {"nome": nome, "prioridade": value}
