import importlib.util, json, os, shutil, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("memoria", os.path.join(HERE, "..", "memoria.py"))
memoria = importlib.util.module_from_spec(spec)
spec.loader.exec_module(memoria)
results = []
folder = tempfile.mkdtemp(prefix="memoria_")
FILE = os.path.join(folder, "maquina", "memoria.json")
os.environ["FOREMAN_MEMORIA"] = FILE


def check(name, ok, detail=""):
    results.append(bool(ok))
    print("PASS" if ok else "FAIL", name, "" if ok else f"| {str(detail)[-300:]}")


def at(stamp):
    os.environ["FOREMAN_MEMORIA_AGORA"] = stamp


def saved():
    with open(FILE, encoding="utf-8") as f:
        return json.load(f)


def one_per(peak, floor):
    return lambda free: 0 if free < floor else max(1, int((free - max(peak, floor)) / peak))


at("2030-01-01T00:00:00Z")
memoria.renew("a")
check("renew with no file creates nothing", not os.path.exists(os.path.dirname(FILE)))
check("release with no file is 0", memoria.release("a", "T1") == 0)

fits = one_per(4, 4)
got, reason, impossible = memoria.reserve("a", "A", ["T1", "T2", "T3"], 4, 12, fits)
check("two of three labels fit and are granted in order", got == ["T1", "T2"] and not impossible, (got, reason))
got, reason, impossible = memoria.reserve("b", "B", ["X"], 4, 10, fits)
check("another project sees the reservations and gets none", got == [] and "A 4 GB (T1)" in reason, reason)
check("a request is kept only for a waiting caller", saved()["pedidos"] == [])
got, reason, impossible = memoria.reserve("b", "B", ["X"], 4, 2, one_per(4, 12))
check("a job that would not fit with every reservation released is impossible", impossible and got == [], reason)
check("release drops only that label", memoria.release("a", "T1") == 1
      and [r["rotulo"] for r in saved()["reservas"]] == ["T2"])

memoria.release("a")
memoria.reserve("c", "C", ["Q"], 8, 9, one_per(8, 1))
memoria.set_priority("b", "B", 2)
got, _, _ = memoria.reserve("a", "A", ["T9"], 1, 8.5, one_per(1, 1), esperando=True)
check("with memory short, a waiting caller leaves a request", got == [] and len(saved()["pedidos"]) == 1, saved())
at("2030-01-01T00:01:00Z")
got, _, _ = memoria.reserve("b", "B", ["X"], 1, 8.5, one_per(1, 1), esperando=True)
memoria.release("c")
got, reason, _ = memoria.reserve("a", "A", ["T9"], 1, 9, one_per(1, 1), esperando=True)
check("a request of higher priority makes the older one wait even when memory fits", got == []
      and "waits for B (priority 2)" in reason, reason)
got, _, _ = memoria.reserve("b", "B", ["X"], 1, 9, one_per(1, 1), esperando=True)
check("the higher priority gets it and its request goes", got == ["X"]
      and [p["projeto"] for p in saved()["pedidos"]] == ["a"], saved())
memoria.set_priority("b", "B", 0)
memoria.release("b")
memoria.reserve("z", "Z", ["late"], 1, 0.5, one_per(1, 1), esperando=True)  # impossible: never queued
check("an impossible request is never queued", [p["projeto"] for p in saved()["pedidos"]] == ["a"], saved())

at("2030-01-01T00:07:00Z")
check("a request not renewed for 5 min no longer counts", memoria.load()["pedidos"] == [])
memoria.reserve("a", "A", ["T1"], 1, 9, one_per(1, 1))
at("2030-01-01T01:59:00Z")
memoria.renew("a")
at("2030-01-01T03:58:00Z")
check("renew keeps a reservation past 2 h from its start", len(memoria.load()["reservas"]) == 1)
at("2030-01-01T04:00:00Z")
check("a reservation not renewed for 2 h no longer counts", memoria.load()["reservas"] == [])

with open(FILE, "w", encoding="utf-8") as f:
    f.write("[1, 2]")
try:
    memoria.reserve("a", "A", ["T1"], 1, 9, one_per(1, 1))
    corrupt = False
except memoria.Corrupt:
    corrupt = True
check("a file of the wrong shape is Corrupt and left untouched", corrupt and open(FILE).read() == "[1, 2]")
memoria.renew("a")
check("renew leaves a corrupt file alone", open(FILE).read() == "[1, 2]")
os.remove(FILE)

lk = os.path.join(folder, "maquina", "memoria.lock")
with open(lk, "w") as f:
    f.write("dead")
os.utime(lk, (time.time() - 120, time.time() - 120))
memoria.reserve("a", "A", ["T1"], 1, 9, one_per(1, 1))
check("a stale lock is taken over", saved()["reservas"] and not os.path.exists(lk))
with open(lk, "w") as f:
    f.write("held")
try:
    with memoria.lock(lk, wait=0.1):
        pass
    busy = False
except memoria.Busy as x:
    busy = lk in str(x)
check("a held lock is Busy and names the file", busy)
os.remove(lk)
check("key folds the case on Windows and resolves the path", memoria.key(folder) == os.path.normcase(os.path.realpath(folder)))

at("2030-02-01T00:00:00Z")
memoria.reserve("h", "H", ["t1"], 4, 20, one_per(4, 4))
memoria.set_priority("w", "W", 10)
memoria.reserve("w", "W", ["big"], 30, 20, one_per(30, 22), esperando=True)  # 16 free after H: waits
got, reason, _ = memoria.reserve("h", "H", ["t2"], 4, 20, one_per(4, 4))
check("a holder asking for a new job waits behind a higher priority", got == [] and "waits for W" in reason, reason)
got, _, _ = memoria.reserve("h", "H", ["manager:t1"], 4, 20, one_per(4, 4))
check("a holder finishing a job it holds (manager:<task>) is not queued", got == ["manager:t1"], got)
memoria.release("h", "manager:t1")
got, _, _ = memoria.reserve("h", "H", ["manager:t1", "t2"], 4, 20, one_per(4, 4), esperando=True)
check("a mixed call gets the finishing label and leaves the new job waiting", got == ["manager:t1"], got)
memoria.release("h", "manager:t1")
memoria.reserve("h", "H", ["t3"], 4, 20, one_per(4, 4), esperando=True)  # H queues behind W
mine = [p["desde"] for p in memoria.load()["pedidos"] if p["projeto"] == "h"]
memoria.reserve("h", "H", ["manager:t1"], 4, 20, one_per(4, 4))
check("a finishing grant keeps the project's place in the queue",
      [p["desde"] for p in memoria.load()["pedidos"] if p["projeto"] == "h"] == mine and mine, memoria.load()["pedidos"])
memoria.release("h", "manager:t1")
memoria.reserve("h", "H", ["manager:t1"], 4, 20, one_per(4, 4), esperando=True)
check("a waiting call with only finishing labels keeps the project's place too",
      [p["desde"] for p in memoria.load()["pedidos"] if p["projeto"] == "h"] == mine, memoria.load()["pedidos"])
memoria.release("h", "manager:t1")
FILE = os.path.join(folder, "outra", "memoria.json")  # a fresh file: no queue left by the cases above
os.environ["FOREMAN_MEMORIA"] = FILE
memoria.reserve("q", "Q", ["big"], 8, 20, one_per(8, 4))
memoria.reserve("p", "P", ["u1"], 4, 20, one_per(4, 4))
memoria.reserve("p", "P", ["manager:u1"], 4, 10, one_per(4, 4), esperando=True)  # 10 - 8 leaves no room yet
check("a waiting call with only finishing labels writes no request", not [p for p in memoria.load()["pedidos"]
                                                                          if p["projeto"] == "p"], memoria.load())
memoria.release("q")
memoria.release("p")
FILE = os.path.join(folder, "maquina", "memoria.json")  # back to the shared file of the cases around
os.environ["FOREMAN_MEMORIA"] = FILE
got, _, _ = memoria.reserve("h", "H", ["manager:manager:t1"], 4, 20, one_per(4, 4))
check("a chained manager: label is not a finishing one", got == [], got)

shutil.rmtree(folder, True)
print("ALL PASS" if all(results) else "SOME FAILED")
sys.exit(0 if all(results) else 1)
