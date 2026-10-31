"""One bounded Mistral request with durable GPU telemetry; no tuning changes."""
import csv
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import platform
import subprocess
import time

ROOT = Path(__file__).resolve().parent
OUT = ROOT / ('gpu-thermal-' + dt.datetime.now().strftime('%Y%m%d-%H%M%S'))
OUT.mkdir()
GPU = Path('/sys/bus/pci/devices/0000:0c:00.0')
HW = next(p for p in (GPU / 'hwmon').glob('hwmon*') if (p / 'temp2_input').exists())
MODEL = 'qwen2.5:14b'
MANUAL = False


def durable(f):
    f.flush()
    os.fsync(f.fileno())


def read(p):
    try:
        return int(p.read_text().strip())
    except (OSError, ValueError):
        return None


def main():
    request = {
        'model': MODEL,
        'messages': [{'role': 'user', 'content':
            'Translate the following fantasy dialogue into Russian. Preserve the tone.\n' +
            ('The road to the old fortress is dangerous. I saw strange lights near the '
             'abandoned tower last night. We should speak to the captain before leaving. '
             'If you will help us, we can offer supplies and a place to rest.\n') * 25}],
        'stream': True, 'keep_alive': 0,
        'options': {'num_ctx': 4096, 'num_batch': 512, 'num_predict': 256},
    }
    (OUT / 'request.json').write_text(json.dumps(request, indent=2))
    (OUT / 'metadata.json').write_text(json.dumps({
        'kernel': platform.release(), 'hwmon': str(HW),
        'cutoffs_C': {'edge': 85, 'junction': 95, 'memory': 85},
        'sample_interval_s': 0.25, 'max_request_s': 120,
        'note': 'Fans fixed at 60%.' if MANUAL else 'Automatic fan control unchanged.',
        'context_note': 'Controlled model comparison: qwen2.5:14b at 4096 context; same synthetic prompt, batch and cutoffs as Mistral 4K.'
    }, indent=2))
    with (OUT / 'events.log').open('w') as events, (OUT / 'temperatures.csv').open('w') as telemetry, (OUT / 'kernel.log').open('w') as kernel, (OUT / 'response.jsonl').open('w') as response:
        def event(message):
            line = dt.datetime.now().astimezone().isoformat() + ' ' + message
            print(line, flush=True)
            events.write(line + '\n')
            durable(events)

        writer = csv.writer(telemetry)
        writer.writerow(['timestamp', 'elapsed_s', 'phase', 'edge_C', 'junction_C',
                         'memory_C', 'fan_rpm', 'pwm_0_255', 'fan_mode', 'power_W', 'gpu_busy_percent'])
        durable(telemetry)
        journal = subprocess.Popen(['journalctl', '-k', '-f', '-n', '0', '--no-pager', '-o', 'short-iso'], stdout=kernel, stderr=subprocess.STDOUT)
        workload = None
        started = time.monotonic()
        launched = None
        stop_at = None
        reason = 'completed'
        event(f'LOG DIRECTORY: {OUT}')
        event('10-second idle baseline; then qwen2.5:14b starts. Watch the GPU fans.')
        # Persist directory entries as well as individual readings.
        for directory in (OUT, ROOT):
            fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        try:
            while True:
                now = time.monotonic()
                temps = [read(HW / f'temp{i}_input') for i in (1, 2, 3)]
                phase = 'cooldown' if stop_at is not None else ('request' if launched else 'baseline')
                writer.writerow([dt.datetime.now().astimezone().isoformat(), round(now-started, 3), phase,
                    *[v / 1000 if v is not None else '' for v in temps],
                    read(HW/'fan1_input'), read(HW/'pwm1'), read(HW/'pwm1_enable'),
                    (read(HW/'power1_average') or 0)/1e6, read(GPU/'gpu_busy_percent')])
                durable(telemetry)
                durable(kernel)
                if stop_at is None:
                    hot = any(t is not None and t >= limit for t, limit in zip(temps, (85000, 95000, 85000)))
                    missing = any(t is None for t in temps)
                    fan_failed = MANUAL and now-started >= 8 and (read(HW/'fan1_input') or 0) < 800
                    timed_out = launched is not None and now-launched >= 120
                    finished = workload is not None and workload.poll() is not None
                    if hot or missing or fan_failed or timed_out or finished:
                        reason = 'TEMPERATURE CUTOFF' if hot else ('SENSOR FAILURE' if missing else ('FAN BELOW 800 RPM' if fan_failed else ('TIME LIMIT' if timed_out else f'REQUEST EXIT {workload.returncode}')))
                        event(f'{reason}; temperatures mC={temps}. Stopping request and unloading model.')
                        if workload is not None and workload.poll() is None:
                            workload.terminate()
                            workload.wait(timeout=5)
                        # Keep monitoring while Ollama processes unload/cancellation.
                        unload = subprocess.Popen(['curl', '-sS', '--max-time', '10', 'http://localhost:11434/api/generate', '-H', 'Content-Type: application/json', '-d', json.dumps({'model': MODEL, 'keep_alive': 0})], stdout=response, stderr=response)
                        stop_at = now
                    elif launched is None and now-started >= 10:
                        event('STARTING qwen2.5:14b NOW: comparison 4096 context, batch 512, maximum 256 output tokens.')
                        workload = subprocess.Popen(['curl', '-sS', '-N', '--max-time', '120', 'http://localhost:11434/api/chat', '-H', 'Content-Type: application/json', '--data-binary', '@' + str(OUT/'request.json')], stdout=response, stderr=response)
                        launched = now
                if stop_at is not None and now-stop_at >= 15:
                    break
                time.sleep(0.25)
        finally:
            if workload is not None and workload.poll() is None:
                workload.terminate()
            journal.terminate()
            journal.wait(timeout=5)
            for f in (telemetry, kernel, response):
                durable(f)
            event('TEST FINISHED: ' + reason)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manual-fans', action='store_true')
    MANUAL = parser.parse_args().manual_fans
    if MANUAL:
        mode = (HW/'pwm1_enable').read_text().strip()
        pwm = (HW/'pwm1').read_text().strip()
        try:
            (HW/'pwm1_enable').write_text('1')
            (HW/'pwm1').write_text('153')
            print('Fans set to 60%; qwen2.5:14b will only start if RPM is at least 800.', flush=True)
            main()
        finally:
            if mode == '1':
                (HW/'pwm1').write_text(pwm)
            (HW/'pwm1_enable').write_text(mode)
            print(f'Restored fan mode {mode} (2 = automatic).', flush=True)
    else:
        main()
