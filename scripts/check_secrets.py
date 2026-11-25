"""Look for API keys, tokens, passwords and private keys before they go public.

This repo and the site in docs/ are public: anything committed and pushed can
be read by anyone, and stays in the git history even after the file is
deleted. Run this before pushing (the pre-push hook in .githooks/ does it for
you) and keep keys in environment variables or an untracked .env file.

Matches are printed with the secret masked, so the output itself is safe to
share.

Usage:
    python scripts/check_secrets.py                 # files tracked or staged now
    python scripts/check_secrets.py --history       # every file version ever committed
    python scripts/check_secrets.py --commits A..B  # files changed in those commits (hook);
                                                    # takes any `git rev-list` arguments

A false alarm? Add `secret-scan: ignore` to the end of that line, or add the
path to ALLOW_PATHS below with a comment saying why.

Exit status 1 if anything is found.
"""
import re
import subprocess
import sys

PATTERNS = [
    ("OpenRouter API key", r"sk-or-(?:v1-)?[A-Za-z0-9]{32,}"),
    ("Anthropic API key", r"sk-ant-[A-Za-z0-9_\-]{20,}"),
    ("OpenAI API key", r"sk-(?:proj-|svcacct-)?[A-Za-z0-9_\-]{20,}T3BlbkFJ[A-Za-z0-9_\-]{20,}|sk-proj-[A-Za-z0-9_\-]{40,}"),
    ("GitHub token", r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{60,}"),
    ("AWS access key", r"(?:AKIA|ASIA)[0-9A-Z]{16}"),
    ("Google API key", r"AIza[0-9A-Za-z_\-]{35}"),
    ("Slack token", r"xox[baprs]-[0-9A-Za-z\-]{10,}"),
    ("Hugging Face token", r"hf_[A-Za-z0-9]{34,}"),
    ("Stripe key", r"(?:sk|rk)_live_[0-9A-Za-z]{20,}"),
    ("Private key", r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY-----"),
    ("Password in URL", r"[a-z][a-z0-9+.\-]*://[^/\s:@\"']{1,64}:[^/\s:@\"']{6,}@[A-Za-z0-9.\-]+"),
    # name = "long value" where the name says key/token/secret/password
    ("Key or password assigned in code",
     r"(?i)\b[\w\-]*(?:api[_\-]?key|secret|token|passw(?:or)?d|access[_\-]?key|auth)[\w\-]*\b"
     r"[\"']?\s*[:=]\s*[\"']([A-Za-z0-9_\-/+=.]{20,})[\"']"),
]
# A key must not sit inside a longer run of base64 (embedded files): letters
# such as "AIza" turn up there by chance.
PATTERNS = [(name, re.compile(r"(?<![A-Za-z0-9+/])(?:" + rx + ")" if i < 9 else rx))
            for i, (name, rx) in enumerate(PATTERNS)]

# Files that should never be committed, whatever they contain.
BAD_NAMES = re.compile(r"(?:^|/)(?:\.env(?:\.[\w.-]+)?|\.Renviron|\.netrc|\.npmrc|\.pypirc|"
                       r"id_rsa|id_ed25519|credentials(?:\.json)?|[^/]*\.(?:p12|pfx|keystore|jks))$", re.I)
# .pem/.key files are checked by content instead: certificate bundles are public.
SAFE_ENV = re.compile(r"\.env\.(?:example|sample|template)$", re.I)

# Paths whose matches are known to be harmless (keep short; say why).
ALLOW_PATHS = [
    "scripts/check_secrets.py",  # the patterns themselves
]
# Values that look like keys but are not: placeholders and integrity hashes.
PLACEHOLDER = re.compile(r"(?i)x{6,}|your[_\-]?|example|placeholder|dummy|changeme|<[^>]+>|\$\{?\w+\}?|sha(?:256|384|512)-")
TEXT_LIMIT = 20_000_000  # skip blobs bigger than this (data dumps)


def git(*args, binary=False):
    out = subprocess.run(["git", *args], capture_output=True, check=True).stdout
    return out if binary else out.decode("utf-8", "replace")


def mask(s):
    return s[:6] + "..." + s[-2:] if len(s) > 12 else s[:2] + "..."


def scan_text(path, text):
    hits = []
    if path in ALLOW_PATHS:
        return hits
    for lineno, line in enumerate(text.splitlines(), 1):
        if "secret-scan: ignore" in line:
            continue
        # Very long lines are minified data/JSON: only the distinctive key formats,
        # not the looser "name = value" and URL patterns, which misfire on data.
        checks = PATTERNS[:10] if len(line) > 5000 else PATTERNS
        for name, rx in checks:
            for m in rx.finditer(line):
                value = m.group(m.lastindex or 0)
                if PLACEHOLDER.search(m.group(0)):
                    continue
                hits.append((path, lineno, name, mask(value)))
    return hits


def blobs_current():
    """(path, blob id) for every file in the index (tracked plus staged)."""
    for row in git("ls-files", "-s", "-z").split("\0"):
        if row:
            meta, path = row.split("\t", 1)
            yield path, meta.split()[1]


def blobs_history():
    """(path, blob id) for every file version in every commit on every branch."""
    seen = set()
    for row in git("rev-list", "--all", "--objects").splitlines():
        parts = row.split(" ", 1)
        if len(parts) == 2 and parts[0] not in seen:
            seen.add(parts[0])
            yield parts[1], parts[0]


def blobs_commits(rng):
    seen = set()
    for commit in git("rev-list", *rng).split():
        out = git("diff-tree", "-r", "--no-commit-id", "--root", commit)
        for line in out.splitlines():
            meta, path = line.split("\t", 1)
            blob = meta.split()[3]
            if blob.strip("0") and blob not in seen:
                seen.add(blob)
                yield path, blob


def main():
    if "--history" in sys.argv:
        source, label = blobs_history(), "every file version in the git history"
    elif "--commits" in sys.argv:
        rng = sys.argv[sys.argv.index("--commits") + 1:]  # any git rev-list arguments
        source, label = blobs_commits(rng), "the commits being pushed"
    else:
        source, label = blobs_current(), "tracked and staged files"

    items = list(source)
    sizes = {}
    if items:
        check = subprocess.run(["git", "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
                               input="\n".join(b for _, b in items).encode(), capture_output=True).stdout.decode()
        for row in check.splitlines():
            parts = row.split()
            if len(parts) == 3 and parts[1] == "blob":
                sizes[parts[0]] = int(parts[2])

    hits, bad_files, skipped = [], [], 0
    proc = subprocess.Popen(["git", "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    for path, blob in items:
        if BAD_NAMES.search(path) and not SAFE_ENV.search(path):
            bad_files.append(path)
        size = sizes.get(blob)
        if size is None:
            continue
        if size > TEXT_LIMIT:
            skipped += 1
            continue
        proc.stdin.write((blob + "\n").encode())
        proc.stdin.flush()
        header = proc.stdout.readline().split()
        data = proc.stdout.read(int(header[2]))
        proc.stdout.read(1)
        if b"\0" in data[:8000]:
            continue  # binary (images etc.)
        hits += scan_text(path, data.decode("utf-8", "replace"))
    proc.stdin.close()
    proc.wait()

    hits = sorted(set(hits))
    bad_files = sorted(set(bad_files))
    if not hits and not bad_files:
        extra = f" ({skipped} files over 20 MB skipped)" if skipped else ""
        print(f"OK: no API keys, tokens, passwords or private keys found in {label}{extra}.")
        return 0

    print(f"POSSIBLE SECRETS FOUND in {label}:\n")
    for path in bad_files:
        print(f"  {path}: this kind of file normally holds credentials; do not commit it")
    for path, lineno, name, shown in hits:
        print(f"  {path}:{lineno}: {name}: {shown}")
    print("\nIf any of these is a real key: remove it, put it in an environment variable or an\n"
          "untracked .env file, and REVOKE/ROTATE it with the provider (once pushed, assume it\n"
          "has been copied). A false alarm: add `secret-scan: ignore` to that line.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
