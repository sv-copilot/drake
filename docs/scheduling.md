# Running slices unattended

Everything up to this page proves a slice can be run. This page is how to let it run without
you: one slice per tick, with evidence, and an exit code that monitoring can act on.

`scripts/slice-cron.sh` is the scheduler's entry point. It runs the next ready slice through
whatever harness the repository configures, writes one log per run under `.drake/logs/`, and
propagates the runner's exit code unchanged.

## Exit codes are the contract with your scheduler

| code | meaning | what monitoring should do |
| --- | --- | --- |
| `0` | a slice ran | nothing; read the evidence when convenient |
| `1` | configuration, harness or selector error — the run never started | **alert**: the pipeline is misconfigured |
| `2` | the harness ran but did not finish cleanly | **alert**: the attempt needs a human look |
| `3` | nothing runnable (nothing ready, unblocked and automation-eligible) | nothing — this is a normal state |

That third row is why exit `3` exists. A scheduler cannot distinguish "no work" from "broken"
if both look like failure, and a pipeline that cries wolf every quiet hour gets ignored within a
week.

## Cron

```cron
# every 30 minutes, between 07:00 and 20:00 on weekdays
*/30 7-20 * * 1-5  cd /srv/my-product && /srv/drake/scripts/slice-cron.sh --repo /srv/my-product
```

Cron mails whatever the job prints, which is one line plus a status line — and the full output
lands in `.drake/logs/`.

## systemd timer

`/etc/systemd/system/drake-slice.service`:

```ini
[Unit]
Description=Run one Drake slice
After=network-online.target

[Service]
Type=oneshot
User=deploy
WorkingDirectory=/srv/my-product
ExecStart=/srv/drake/scripts/slice-cron.sh --repo /srv/my-product
# exit 3 means "nothing to do" and must not be reported as a failure
SuccessExitStatus=0 3
```

`/etc/systemd/system/drake-slice.timer`:

```ini
[Unit]
Description=Run a Drake slice every 30 minutes

[Timer]
OnCalendar=Mon..Fri *-*-* 07..20:00/30
Persistent=true

[Install]
WantedBy=timers.target
```

`SuccessExitStatus=0 3` is the important line: without it systemd marks every quiet tick as a
failure. With it, only exits `1` and `2` reach `systemctl --failed` or your alerting.

## What a tick leaves behind

- `.drake/logs/<timestamp>.log` — the runner's output for that tick
- `.drake/runs/<run-label>/` — `task-packet.json`, `prompt.txt`, `evidence.json`, the harness's
  own stdout/stderr, and the changed files the harness left behind
- nothing else: the lock is removed on exit, and run artifacts are gitignored

## Safety, because unattended means unattended

- **A disposable branch.** Harnesses configured to run without prompting (`--auto-approve true`
  for Cline, `--permission-mode acceptEdits` for Claude Code) can edit files and run commands.
  Keep the work on `slice/*` branches and review the evidence record before merging.
- **Constrain what the harness may execute.** Cline reads `CLINE_COMMAND_PERMISSIONS`; use it.
  For any harness: keep the validation commands in `.drake/slice-pipeline.config.json` honest,
  because that file is what "proves" the slice afterwards.
- **One slice per tick, no fan-out.** The dependency tree's `default_fanout_limit` and the
  selector enforce this; do not work around it from cron by running two ticks in parallel. The
  lock will make the second one exit `0` without doing anything.
- **Operator-gated slices never run.** A slice with `operator_gates` and `state: gated` is skipped
  by the selector, so your decisions stay yours.

## Before you schedule it

Run it by hand once, in this order:

```bash
./scripts/run-slice.sh --dry-run                        # what would run
./scripts/run-slice.sh --harness generic \
  --harness-command "bash scripts/harness_stub.sh {prompt_file}"   # the wiring, no model, no cost
./scripts/slice-cron.sh --repo .                        # exactly what the scheduler will do
```

If the third command exits `0` and the evidence record names the file the harness changed, the
schedule is safe to enable. See [`README.md`](../README.md) for the from-scratch path and
[`docs/harnesses.md`](harnesses.md) for wiring a real harness.
