FROM registry.access.redhat.com/ubi8/ubi

MAINTAINER Jan Hutar <jhutar@redhat.com>

WORKDIR /usr/src/app

ENV SQLALCHEMY_DATABASE_URI=sqlite:////tmp/database.db
ENV SLACK_BOT_TOKEN=xoxb-...
ENV SLACK_APP_TOKEN=xapp-...

EXPOSE 8080/tcp

RUN INSTALL_PKGS="python3" \
  && yum -y install $INSTALL_PKGS \
  && yum clean all

COPY requirements.txt .

RUN python3 -m pip install --no-cache-dir -U pip \
    && python3 -m pip install --no-cache-dir -r /usr/src/app/requirements.txt

COPY . /usr/src/app

CMD ./app.py
