Bot to record scrum status messages from MBU Perf&Scale team
============================================================

The bot is supposed to be part of #team-perfscale and there it waits for `Reminder: Hello @perfscale ! share your daily scrum update.` messages. Once there is some message like that, bot waits for messages in that thread and if they start with `Done`, they are recorded as a status message.

Good guide I have followed: <https://slack.dev/bolt-python/tutorial/getting-started>

Development
-----------

Installation:

    python -m venv venv
    source venv/bin/activate
    pip install -U pip
    pip install -r requirements.txt

Running locally:

    export SQLALCHEMY_DATABASE_URI='sqlite:////tmp/database.db'
    export SLACK_BOT_TOKEN=xoxb-...
    export SLACK_APP_TOKEN=xapp-...
    flask db upgrade
    ./app.py

Running it
----------

Building container:

    podman build -t localhost/jhutar-slack-bot:latest -f Containerfile .

Running container locally:

    touch db.sqlite
    podman run --rm -ti -v ./db.sqlite:/usr/src/app/db.sqlite:Z -e SQLALCHEMY_DATABASE_URI=sqlite:////usr/src/app/db.sqlite -e SLACK_BOT_TOKEN=xoxb-... -e SLACK_APP_TOKEN=xapp-... localhost/jhutar-slack-bot:latest flask db upgrade
    podman run --rm -ti -v ./db.sqlite:/usr/src/app/db.sqlite:Z -e SQLALCHEMY_DATABASE_URI=sqlite:////usr/src/app/db.sqlite -e SLACK_BOT_TOKEN=xoxb-... -e SLACK_APP_TOKEN=xapp-... 8080:8080 localhost/jhutar-slack-bot:latest

Running in OpenShift:

    oc -n <namespace> apply -f deploy.yaml
    (and edit secrets in secret/jhutar-slack-bot-secret)

And rolling out latest image when running it in OpenShift:

    oc -n <namespace> rollout latest DeploymentConfig/jhutar-slack-bot
    oc -n <namespace> rollout status DeploymentConfig/jhutar-slack-bot
