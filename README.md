Bot to record scrum status messages from MBU Perf&Scale team
============================================================

Good guide I have followed: <https://slack.dev/bolt-python/tutorial/getting-started>

Installation:

    python -m venv venv
    source venv/bin/activate
    pip install -U pip
    pip install -r requirements.txt

Running locally:

    export SQLALCHEMY_DATABASE_URI='sqlite:////tmp/database.db'
    flask db upgrade
    export SLACK_BOT_TOKEN=xoxb-...
    export SLACK_APP_TOKEN=xapp-...
    ./app.py

Building container:

    podman build -t localhost/jhutar-slack-bot:latest -f Containerfile .

Running container locally:

    touch db.sqlite
    podman run --rm -ti -v ./db.sqlite:/usr/src/app/db.sqlite:Z -e SQLALCHEMY_DATABASE_URI=sqlite:////usr/src/app/db.sqlite -e SLACK_BOT_TOKEN=xoxb-... -e SLACK_APP_TOKEN=xapp-... localhost/jhutar-slack-bot:latest flask db upgrade
    podman run --rm -ti -v ./db.sqlite:/usr/src/app/db.sqlite:Z -e SQLALCHEMY_DATABASE_URI=sqlite:////usr/src/app/db.sqlite -e SLACK_BOT_TOKEN=xoxb-... -e SLACK_APP_TOKEN=xapp-... --net host -p 8080:8080 localhost/jhutar-slack-bot:latest

Running in OpenShift:

    oc -n jenkins-csb-perf apply -f deploy.yaml
    (and edit secrets in secret/jhutar-slack-bot-secret)
