# C tracker

Consent-based live location sharing. People join a group with a name and a group code. No accounts needed.

## Run on your computer
    pip install -r requirements.txt
    python app.py
Open http://localhost:5000

## Put it online (free hosts such as Render or PythonAnywhere)
Upload this folder. Start command: `gunicorn app:app`. Browsers only allow GPS on HTTPS, which these hosts provide.

## How to use
1. One person opens the site, enters a name, ticks both consent boxes, leaves the code empty and taps Continue. A group code appears.
2. Others open the same site, enter their name and that code, tick consent, and join.
3. Each person taps Start sharing. Stop deletes their location. Leave removes them from the group.

## Privacy
Only the latest position is stored. It is deleted on Stop or Leave, and after 24 hours. Use only with people who know about it and agree.
