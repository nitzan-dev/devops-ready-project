"""Grades answers. Every function returns a score from 0 to 100."""

import re

# Commands whose short flags can be combined in any order (ls -la == ls -al == ls -l -a),
# mapped to the flags that take a value (tail -n 100, kubectl -n prod).
CLUSTER_CMDS = {
    "ls": "", "ps": "pou", "rm": "", "cp": "", "mv": "", "grep": "eABCmf", "egrep": "eABCm", "du": "d",
    "df": "t", "free": "", "uname": "", "ss": "", "netstat": "", "tail": "nc", "head": "nc", "sort": "ktS",
    "uniq": "f", "wc": "", "chmod": "", "chown": "", "mkdir": "m", "ln": "", "tar": "fC", "lsof": "ip",
    "useradd": "gGsdmu", "usermod": "gGsdl", "journalctl": "unpS", "systemctl": "", "curl": "XHdoAuwe",
    "ssh-keygen": "tbfCN", "dig": "", "nc": "w", "xargs": "nIP", "top": "dpn", "lsblk": "", "kill": "s",
    "pkill": "u", "cut": "dfc", "git": "mbC", "docker": "pvewum", "kubectl": "nolc", "helm": "nf",
    "ssh": "ipLRo", "scp": "Pi", "rsync": "e", "sed": "e", "awk": "Fv", "nslookup": "", "ping": "cWi",
    "traceroute": "m", "tcpdump": "inwc", "ip": "", "ab": "nc", "watch": "n", "nice": "n", "renice": "n",
    "crontab": "u",
}

# Tools whose first word is a subcommand (git log, kubectl get).
SUBCOMMAND_CMDS = {"git", "docker", "kubectl", "helm", "terraform", "systemctl", "ip"}


def verdict(score):
    if score >= 85:
        return "correct"
    if score >= 40:
        return "partial"
    return "incorrect"


def grade_mcq(q, picked):
    """One correct option: all or nothing. Several: correct picks minus wrong picks."""
    correct = set(q["correct"])
    picked = set(picked)
    hits = len(picked & correct)
    wrong = len(picked - correct)
    if len(correct) == 1:
        return 100 if hits == 1 and wrong == 0 else 0
    return max(0, round((hits - wrong) / len(correct) * 100))


def normalize_command(raw):
    """Spaces, quotes, a leading prompt and sudo don't matter."""
    s = raw.strip()
    s = re.sub(r"^[$#]\s+", "", s)
    s = re.sub(r"^sudo\s+(-\w+\s+)*", "", s)
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'").replace('"', "'")
    s = re.sub(r"(?<!\\)\s*;\s*$", "", s)
    return re.sub(r"\s+", " ", s)


def canonical_command(raw):
    """Puts flags in a fixed order, so 'ls -al' and 'ls -l -a' compare as equal."""
    segments = []
    for segment in re.split(r"\s*\|\s*", normalize_command(raw)):
        tokens = segment.split(" ")
        cmd = tokens[0]
        if cmd not in CLUSTER_CMDS:
            segments.append(segment)
            continue
        value_flags = CLUSTER_CMDS[cmd]
        letters, pairs, rest = [], [], []
        i = 1
        while i < len(tokens):
            t = tokens[i]
            if re.fullmatch(r"-[a-zA-Z]", t) and t[1] in value_flags and i + 1 < len(tokens):
                pairs.append(f"{t} {tokens[i + 1]}")
                i += 1
            elif re.fullmatch(r"-[a-zA-Z]{1,5}", t):
                letters.extend(t[1:])
            else:
                rest.append(t)
            i += 1
        cluster = ["-" + "".join(sorted(set(letters)))] if letters else []
        sub = [rest.pop(0)] if cmd in SUBCOMMAND_CMDS and rest and re.fullmatch(r"[a-z][\w-]*", rest[0]) else []
        segments.append(" ".join([cmd, *sub, *cluster, *sorted(pairs), *rest]))
    return " | ".join(segments)


def grade_command(q, answer):
    norm = normalize_command(answer)
    if not norm:
        return 0
    canon = canonical_command(answer)
    if any(canonical_command(a) == canon for a in q["answers"]):
        return 100
    if any(re.search(p, norm) or re.search(p, canon) for p in q.get("patterns", [])):
        return 100
    # Right tool, wrong flags: partial credit.
    tools = {normalize_command(a).split(" ")[0] for a in q["answers"]}
    return 30 if norm.split(" ")[0] in tools else 0


def grade_order(q, order):
    """order = the step indexes in the order the user chose. Partial credit for pairs in the right order."""
    if order == list(range(len(q["steps"]))):
        return 100
    pairs = good = 0
    for i in range(len(order)):
        for j in range(i + 1, len(order)):
            pairs += 1
            good += order[i] < order[j]
    # Capped at 80, so any wrong order shows as "partial", never "correct".
    return min(80, round(good / pairs * 100))


def grade_self(q, checked):
    """Open questions: the weights of the key points the user says they covered."""
    points = q["rubric"]["keyPoints"]
    total = sum(kp["weight"] for kp in points)
    got = sum(points[i]["weight"] for i in checked)
    return round(got / total * 100)
