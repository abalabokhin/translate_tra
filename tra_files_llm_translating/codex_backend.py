"""Codex CLI transport shared by production translation and diagnostic runners.

No model tools, retries, output cap or inference timeout. Preserve every request.
"""
import json
import os
import signal
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

CLI_INSTRUCTION = (
    'Translate using only the supplied instructions and dialogue data. '
    'Do not use tools, inspect files, browse, delegate, or change any files. '
    'Return only the JSON required by the output schema.\n\n'
)


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def run_cli(binary, model, system, user, schema, out, dry_run=False, effort=None):
    out.mkdir(parents=True)
    prompt = CLI_INSTRUCTION + system + '\n\nDIALOGUE DATA:\n' + user
    (out / 'prompt.txt').write_text(prompt, encoding='utf-8')
    save(out / 'schema.json', schema)
    record = {'status': 'prepared', 'model': model, 'reasoning_effort': effort, 'started_utc': now(),
              'wall_seconds': 0, 'usage': None, 'error': None}
    if dry_run:
        save(out / 'call.json', record)
        return record, None
    started = time.monotonic()
    try:
        # Fresh cwd outside the repository: no fixtures, references or project instructions.
        with tempfile.TemporaryDirectory(prefix='tra-codex-') as temporary:
            work = Path(temporary)
            save(work / 'schema.json', schema)
            command = [binary, 'exec', '--ignore-user-config', '--ephemeral',
                       '--skip-git-repo-check', '--sandbox', 'read-only', '--model', model,
                       '--color', 'never', '--json', '--output-schema', str(work / 'schema.json'),
                       '--output-last-message', str(work / 'response.txt'), '-']
            if effort is not None:
                command[2:2] = ['-c', f'model_reasoning_effort="{effort}"']
            record['command'] = command
            with (out / 'events.jsonl').open('w', encoding='utf-8') as events, \
                    (out / 'stderr.txt').open('w', encoding='utf-8') as stderr:
                process = subprocess.Popen(command, cwd=work, stdin=subprocess.PIPE,
                                           stdout=events, stderr=stderr, text=True,
                                           start_new_session=os.name == 'posix')
                try:
                    process.communicate(prompt)
                except KeyboardInterrupt:
                    if os.name == 'posix':
                        os.killpg(process.pid, signal.SIGTERM)
                    else:
                        process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        if os.name == 'posix':
                            os.killpg(process.pid, signal.SIGKILL)
                        else:
                            process.kill()
                        process.wait()
                    raise
            response = work / 'response.txt'
            if response.exists():
                (out / 'response.txt').write_bytes(response.read_bytes())
            record['returncode'] = process.returncode
        completed = False
        for line in (out / 'events.jsonl').read_text(encoding='utf-8').splitlines():
            event = json.loads(line)
            if event.get('type') == 'turn.completed':
                completed = True
                record['usage'] = event.get('usage')
            if event.get('type') in ('error', 'turn.failed'):
                raise ValueError(f'CLI failure: {event}')
            item = event.get('item', {})
            if item and item.get('type') not in ('agent_message', 'reasoning'):
                raise ValueError(f'Unexpected tool/activity in translation: {item.get("type")}')
        if process.returncode or not completed or not (out / 'response.txt').exists():
            raise ValueError(f'CLI did not complete successfully (exit {process.returncode}); see stderr.txt')
        record['status'] = 'completed'
        return record, (out / 'response.txt').read_text(encoding='utf-8')
    except KeyboardInterrupt:
        record.update(status='interrupted', error='Interrupted; no retry')
        raise
    except (OSError, ValueError) as exc:
        record.update(status='failed', error=str(exc))
        return record, None
    finally:
        record['wall_seconds'] = round(time.monotonic() - started, 3)
        record['finished_utc'] = now()
        save(out / 'call.json', record)

