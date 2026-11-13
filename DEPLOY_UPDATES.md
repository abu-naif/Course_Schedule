# Updating Course Schedule through GitHub

Your Mac repository already uses branch `main` and remote
`git@github.com:abu-naif/Course_Schedule.git`.

## 1. Push your changes from your Mac

Run inside the project directory:

```bash
cd ~/Desktop/Course_Schedule
git status
```

Review the listed changes, then save a version and upload it:

```bash
git add .
git commit -m "Improve mobile layout and collapsible preferences"
git push origin main
```

`add` stages files, `commit` records a local version, and `push` uploads commits.
The `.gitignore` excludes virtual environments and `node_modules`. Environment
files and credentials should not be committed.

If SSH reports `Permission denied (publickey)`, configure a GitHub SSH key on
that computer. Do not copy your Mac's private SSH key onto the server.

## 2. Check whether Ubuntu has a Git checkout

SSH into Ubuntu and use your actual deployment directory:

```bash
cd ~/course-schedule
git rev-parse --show-toplevel
git remote -v
git status
```

If it is already a checkout of the correct repository and has no uncommitted
changes, continue to step 3. If you uploaded it using rsync and it is not a Git
checkout, use the first-time migration below instead of running `git pull`.

## 3. Pull and restart on Ubuntu

For the systemd + virtual environment deployment discussed in the hosting guide:

```bash
cd ~/course-schedule
git pull --ff-only origin main
./venv/bin/python -m pip install -r requirements.txt
sudo systemctl restart course-schedule
sudo systemctl status course-schedule --no-pager
```

Run commands one at a time; stop and investigate any failure before continuing.
`--ff-only` refuses to combine divergent histories automatically. If local edits
block the pull, review and back them up or commit them deliberately before trying
again. Do not force-reset a server checkout to fix an unexplained error.

The updated stylesheet and icon assets are committed in `static/`, so Node.js
is not needed on Ubuntu for normal updates. If the local application port and
address stay the same, the existing Tailscale Funnel keeps working.

If your live deployment uses Docker instead of systemd, pull in its build folder
and run its existing Compose workflow (`sudo docker compose up -d --build`) or
rebuild/recreate its container with the same settings. Do not switch an existing
Docker deployment to systemd just to follow these example commands.

## First-time migration: an rsync folder to a Git checkout

Preserve the current deployment and clone into a new folder:

```bash
cd ~
git clone https://github.com/abu-naif/Course_Schedule.git course-schedule-git
cd ~/course-schedule-git
python3 -m venv venv
./venv/bin/python -m pip install -r requirements.txt
```

A private repository requires GitHub authentication. For an automated server,
a read-only SSH deploy key is an option; register it on this repository and
clone using `git@github.com:abu-naif/Course_Schedule.git` instead.

Inspect the current service definition:

```bash
sudo systemctl cat course-schedule
sudo nano /etc/systemd/system/course-schedule.service
```

Change `WorkingDirectory` and the Python executable path in `ExecStart` to the
absolute paths in `course-schedule-git`. Keep the existing username, bind address
and local port. Preserve any actual server configuration or environment files.

```bash
sudo systemctl daemon-reload
sudo systemctl restart course-schedule
sudo systemctl status course-schedule --no-pager
```

Then use `~/course-schedule-git` for future pulls. Retain the old folder until
the updated app works. You can restore the old service paths if migration fails.

## Check an update

```bash
sudo journalctl -u course-schedule -n 60 --no-pager
sudo tailscale funnel status
```

Open the existing public URL, test course generation, and refresh the browser.
Android Chrome supports the install prompt when eligible. On iPhone, use Safari
> Share > Add to Home Screen. Schedule generation still needs internet access.

## Rebuild styles after future interface edits (on your Mac)

```bash
npm ci
npm run build:css
```

Commit the updated `static/css/tailwind.css` alongside template or JavaScript
changes that introduce utility classes. The production page loads this stylesheet
instead of compiling Tailwind CSS in each visitor's browser.

References:
- https://docs.github.com/en/get-started/using-git/pushing-commits-to-a-remote-repository
- https://git-scm.com/docs/git-pull
- https://docs.github.com/en/authentication/connecting-to-github-with-ssh

## Verify the exact analyzer after an update

```bash
./venv/bin/python -m unittest discover -s tests -v
```

The search reuses pair-conflict checks and keeps the best requested schedules
with stable ties. It counts the complete valid set rather than stopping after
50,000 results. Proven noncompetitive branches can be counted without scoring
every leaf; class, lab, parsed-exam and exact-day checks remain in effect.

Identical web requests reuse a bounded in-memory result cache only for the same
feed object and request settings. A fetched or manually refreshed feed invalidates
reuse. Restarting the application also clears that cache. Initial feed downloads
and difficult searches can still take time; the server's CPU affects performance.

Phones start with the By day routine; Week and Expand provide a larger overview.
The production stylesheet is already built and committed with these changes.
