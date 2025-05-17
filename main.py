# GILT Web Server with Safe Image Loading and Folder Check

from flask import Flask, render_template, request, redirect, url_for, session
import os
import random
import math

app = Flask(__name__)
app.secret_key = 'gilt_demo_secret'

# CONFIG
IMAGE_FOLDER = "static/images"
TRIALS_PER_LEVEL = 5
LEVEL_IMAGE_MAP = {}  # {level: [list of files]}
LEVELS = []

# Helper to parse filenames and extract level/letter

def load_images():
    global LEVELS, LEVEL_IMAGE_MAP
    if not os.path.exists(IMAGE_FOLDER):
        print("❌ IMAGE FOLDER NOT FOUND:", IMAGE_FOLDER)
        return
    files = os.listdir(IMAGE_FOLDER)
    for f in files:
        if not f.endswith(".png") or "Intact-" not in f:
            continue
        parts = f.split("Intact-")
        if len(parts) != 2:
            continue
        level_str = parts[0].split("-")[-1]  # e.g., from Set1-50.12Intact-C.png → 50.12
        try:
            round(float(level_str), 2)
        except ValueError:
            continue
        LEVEL_IMAGE_MAP.setdefault(level_str, []).append(f)
    CUSTOM_ORDER = ['100.00', '89.12', '50.12', '28.18', '15.85', '8.91', '5.01', '2.81', '1.58']
    global LEVELS
    LEVELS = [lvl for lvl in CUSTOM_ORDER if lvl in LEVEL_IMAGE_MAP]
    CUSTOM_ORDER = ['100.00', '89.12', '50.12', '28.18', '15.85', '8.91', '5.01', '2.81', '1.58']


load_images()

@app.route('/')
def index():
    print("🟢 Home page loaded")
    session.clear()
    return render_template('index.html')

@app.route('/start')
def start():
    session['current_level_idx'] = 0
    session['trial_in_level'] = 0
    session['correct_in_level'] = 0
    session['total_correct'] = 0
    session['total_trials'] = 0
    session['responses'] = []
    session['used_images'] = {}
    return redirect(url_for('trial'))

@app.route('/trial', methods=['GET', 'POST'])
def trial():
    if session['current_level_idx'] >= len(LEVELS):
        return redirect(url_for('results'))

    level = LEVELS[session['current_level_idx']]
    all_choices = LEVEL_IMAGE_MAP.get(level, [])
    used = session['used_images'].get(level, [])
    unused = list(set(all_choices) - set(used))

    if request.method == 'POST':
        user_input = request.form.get('answer', '').strip().upper()
        shown_letter = session.get('current_letter')
        if shown_letter is None:
            return redirect(url_for('trial'))

        correct = int(user_input == shown_letter)

        session['responses'].append({
            'level': level,
            'letter': shown_letter,
            'user_input': user_input,
            'correct': correct
        })

        session['trial_in_level'] += 1
        session['total_trials'] += 1
        session['correct_in_level'] += correct
        session['total_correct'] += correct

        if session['trial_in_level'] >= TRIALS_PER_LEVEL:
            accuracy = session['correct_in_level'] / TRIALS_PER_LEVEL
            if accuracy >= 0.8:
                session['current_level_idx'] += 1
                session['trial_in_level'] = 0
                session['correct_in_level'] = 0
            else:
                return redirect(url_for('results'))
        return redirect(url_for('trial'))

    remaining_trials = TRIALS_PER_LEVEL - session['trial_in_level']
    if not unused or len(unused) < remaining_trials:
        print(f"⚠ Not enough unused images left at level {level} to complete {remaining_trials} more trials.")
        session['current_level_idx'] += 1
        session['trial_in_level'] = 0
        session['correct_in_level'] = 0
        if session['current_level_idx'] >= len(LEVELS):
            return redirect(url_for('results'))
        return redirect(url_for('trial'))

    filename = random.choice(unused)
    if not filename:
        print("🚨 No valid filename selected. Skipping.")
        return redirect(url_for('results'))

    letter = filename.split("Intact-")[-1].replace(".png", "")
    session['current_letter'] = letter
    session['used_images'].setdefault(level, []).append(filename)

    print(f"✅ Showing {filename} at level {level} | Trial {session['trial_in_level'] + 1} of {TRIALS_PER_LEVEL}")

    return render_template('trial.html', 
                           level_number=session['current_level_idx'] + 1, 
                           trial_number=session['trial_in_level'] + 1,
                           image_file=filename,
                           level=level)

@app.route('/results')
def results():
    s = session['total_correct'] * 0.05
    threshold = round(1 / (10 ** s), 3)
    return render_template('results.html', 
        score=session['total_correct'], 
        total=session['total_trials'], 
        threshold=threshold,
        responses=session['responses'])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
