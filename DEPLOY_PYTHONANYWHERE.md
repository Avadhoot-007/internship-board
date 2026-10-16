# Deploy to PythonAnywhere (free)

Replace `USERNAME` with your PythonAnywhere username everywhere.

## 1. Sign up

Create a free "Beginner" account at pythonanywhere.com. No card needed.

## 2. Get the code

Open a **Bash console**. Then:

```bash
git clone https://github.com/USERNAME/internship-board.git
cd internship-board
mkvirtualenv --python=python3.12 internship
pip install -r requirements.txt
```

Use a Python version PythonAnywhere offers. Match it in step 3.

## 3. Create the web app

1. Web tab → **Add a new web app** → Manual configuration → same Python version.
2. Set **Source code** to `/home/USERNAME/internship-board`.
3. Set **Virtualenv** to `/home/USERNAME/.virtualenvs/internship`.

## 4. Set the WSGI file

Click the WSGI configuration file link on the Web tab. Replace its contents with `wsgi.py` from this repo, after changing `USERNAME`. Save.

## 5. Reload and test

1. Click the green **Reload** button.
2. Open `https://USERNAME.pythonanywhere.com/`. You should see the board.
3. Check `https://USERNAME.pythonanywhere.com/api/health` returns `{"status": "ok"}`.
4. Check `https://USERNAME.pythonanywhere.com/api/internships` returns JSON.

## Maintenance

- **Monthly:** the free web app expires after one month. Click **Extend** on the Web tab.
- **Updates:** `git pull` in a Bash console, then Reload.
- **Data:** applications live in `data/applications.db`. Back it up from the Files tab.
- **Logs:** Error log and Server log links on the Web tab.

## Troubleshooting

- **Error page:** check the Error log link on the Web tab.
- **Everyone rate-limited at once:** `TRUST_PROXY` is off, or the proxy does not send `X-Forwarded-For`. Check the server log for the real client IP.
- **Database errors:** the app creates `data/` on start. If it still fails, check that the Bash console user can write to the project folder.
- **Health check fails (503):** open `/api/health` and check the error log for the traceback.
