#!/usr/bin/env python3

import contextlib
import logging
import os
import re
import time

import flask

import flask_migrate

import flask_sqlalchemy

from slack_bolt import App, BoltContext
from slack_bolt.adapter.socket_mode import SocketModeHandler

from slack_sdk import WebClient

from sqlalchemy.sql import func


##########
# Init
##########

logging.basicConfig(level=logging.DEBUG)

app = App(token=os.environ["SLACK_BOT_TOKEN"])
socket_mode_handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])

flask_app = flask.Flask(__name__)

flask_app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['SQLALCHEMY_DATABASE_URI']
flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

flask_app_db = flask_sqlalchemy.SQLAlchemy(flask_app)

flask_app_migrate = flask_migrate.Migrate(flask_app, flask_app_db)


##########
# Params
##########

parent_max_age = 3600 * 24 * 7   # Drop parent messages from the list after 7 days
parent_regexp = re.compile(r'^Reminder: Hello')   # Regexp to determine if the message is "share your status" one
child_regexp = re.compile(r'^([Dd]one|[Bb]locker)')   # Regexp to determine if the message contains status


##########
# DB Models
##########

class ThreadsToFollow(flask_app_db.Model):
    thread_ts = flask_app_db.Column(flask_app_db.Float, primary_key=True)
    created_at = flask_app_db.Column(flask_app_db.DateTime(timezone=True), server_default=func.now())

    def age(self):
        now = time.time()
        return now - self.thread_ts

    def serialize(self):
        return {
            "thread_ts": self.thread_ts,
            "created_at": self.created_at,
        }

    def __repr__(self):
        return f'<ThreadsToFollow {self.thread_ts}>'


class Message(flask_app_db.Model):
    ts = flask_app_db.Column(flask_app_db.Float, primary_key=True)
    user = flask_app_db.Column(flask_app_db.String)
    message = flask_app_db.Column(flask_app_db.Text)
    thread_ts = flask_app_db.Column(flask_app_db.Float)
    created_at = flask_app_db.Column(flask_app_db.DateTime(timezone=True), server_default=func.now())

    def age(self):
        now = time.time()
        return now - self.ts

    def serialize(self):
        return {
            "ts": self.ts,
            "user": self.user,
            "message": self.message,
            "thread_ts": self.thread_ts,
            "created_at": self.created_at,
        }

    def __repr__(self):
        return f'<Message {self.ts} from {self.user}>'


##########
# Slack
##########

@contextlib.contextmanager
def session_scope(db):
    """Provide a transactional scope around a series of operations."""
    session = db.session
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()

@app.middleware
def set_db_object(context, body, next):
    context["db"] = flask_app_db
    next()


@app.event("app_mention")
def event_test(body: dict, client: WebClient, context: BoltContext, logger: logging.Logger):
    channel_id = body["event"]["channel"]
    message_ts = body["event"]["ts"]
    result = client.chat_postMessage(
        channel=channel_id,
        thread_ts=message_ts,
        text="Hello world!",
    )


def message_new_parent(body: dict, client: WebClient, context: BoltContext, logger: logging.Logger):
    message_text = body["event"]["text"]
    message_ts = body["event"]["ts"]

    if re.search(parent_regexp, message_text):
        logger.info(f"Processing new parent message {body}")

        with session_scope(context["db"]) as session:
            t = ThreadsToFollow()
            t.thread_ts = float(message_ts)
            session.add(t)

            # Remove too old threads
            parent_count_before = ThreadsToFollow.query.count()
            now = time.time()
            parent_limit = now - parent_max_age
            ThreadsToFollow.query.filter(ThreadsToFollow.thread_ts < parent_limit).delete()
            parent_count_after = ThreadsToFollow.query.count()
            if parent_count_before != parent_count_after:
                logging.info(f"Expired some parent messages. Before we had {parent_count_before} and now we have {parent_count_after} of them")


def handle_message_child(context, message_text, message_ts, message_thread_ts, message_user, client):
    if re.search(child_regexp, message_text):
        with session_scope(context["db"]) as session:
            parent_list = [i[0] for i in ThreadsToFollow.query.with_entities(ThreadsToFollow.thread_ts).all()]
            if float(message_thread_ts) in parent_list:
                m_exists = Message.query.filter_by(ts=float(message_ts)).first()

                if m_exists is None:
                    m = Message()
                    m.ts = float(message_ts)
                    m.user = message_user
                    m.message = message_text
                    m.thread_ts = float(message_thread_ts)
                else:
                    m = m_exists
                    m.message = message_text

                context["db"].session.add(m)

                if m_exists is None:
                    client.reactions_add(
                        channel=context.channel_id,
                        timestamp=message_ts,
                        name="eyes",
                    )

                return True


def message_new_child(body: dict, client: WebClient, context: BoltContext, logger: logging.Logger):
    message_text = body["event"]["text"]
    message_ts = body["event"]["ts"]
    message_thread_ts = body["event"]["thread_ts"]
    message_user = body["event"]["user"]

    if handle_message_child(context, message_text, message_ts, message_thread_ts, message_user, client):
        logger.info(f"Added message {message_ts}")


def message_changed_child(body: dict, client: WebClient, context: BoltContext, logger: logging.Logger):
    message_text = body["event"]["message"]["text"]
    message_ts = body["event"]["message"]["ts"]
    message_thread_ts = body["event"]["message"]["thread_ts"]
    message_user = body["event"]["message"]["user"]

    if handle_message_child(context, message_text, message_ts, message_thread_ts, message_user, client):
        logger.info(f"Changed message {message_ts}")


@app.event("message")
def message(body: dict, client: WebClient, context: BoltContext, logger: logging.Logger):
    if "subtype" not in body["event"]:   # this is a new message
        if "thread_ts" not in body["event"]:   # this is a new parent message
            message_new_parent(body, client, context, logger)
        else:   # this is a new child message
            message_new_child(body, client, context, logger)

    elif "subtype" in body["event"] and body["event"]["subtype"] == "message_changed":   # this is an updated message
        if "thread_ts" in body["event"]["message"]:   # this is an updated child message
            message_changed_child(body, client, context, logger)

    else:
        logger.info(f"Unknown message {body}")


##########
# Flask
##########

def _serialize(query):
    if 'page' in flask.request.args:
        page = int(flask.request.args['page'])
    else:
        page = 1

    data = query.paginate(page=page)

    return {
        "total": data.total,
        "page": data.page,
        "pages": data.pages,
        "per_page": data.per_page,
        "items": [d.serialize() for d in data.items],
    }


@flask_app.route("/api/threads-to-follow", methods=["GET"])
def api_threads_to_follow():
    return _serialize(ThreadsToFollow.query)


@flask_app.route("/api/messages", methods=["GET"])
def api_messages():
    return _serialize(Message.query)


@flask_app.route("/health", methods=["GET"])
def slack_events():
    if (
        socket_mode_handler.client is not None
        and socket_mode_handler.client.is_connected()
    ):
        return flask.make_response("OK", 200)
    return flask.make_response("The Socket Mode client is inactive", 503)


##########
# Main
##########

if __name__ == "__main__":
    socket_mode_handler.connect()  # does not block the current thread
    flask_app.run(host="0.0.0.0", port=8080)
