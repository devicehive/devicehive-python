FROM python:3.6
MAINTAINER Dmitry Platon <platon.dimka@gmail.com>

ENV TEST=''
ENV TRANSPORT_URLS='http://playground-dev.devicehive.com/api/rest,ws://playground-dev.devicehive.com/api/websocket'
ENV ADMIN_REFRESH_TOKEN=''
ENV CLIENT_REFRESH_TOKEN=''
ENV ADMIN_ACCESS_TOKEN=''
ENV CLIENT_ACCESS_TOKEN=''
ENV ADMIN_LOGIN=''
ENV ADMIN_PASSWORD=''
ENV CLIENT_LOGIN=''
ENV CLIENT_PASSWORD=''
ENV LOG_LEVEL='INFO'

ADD devicehive /opt/devicehive-python/devicehive
ADD tests /opt/devicehive-python/tests
ADD setup.py README.md /opt/devicehive-python/
RUN cd /opt/devicehive-python && pip install . pytest

ENTRYPOINT pytest -xsv /opt/devicehive-python/tests/$TEST\
                  --transport-urls=$TRANSPORT_URLS\
                  --admin-refresh-token=$ADMIN_REFRESH_TOKEN\
                  --admin-access-token=$ADMIN_ACCESS_TOKEN\
                  --client-refresh-token=$CLIENT_REFRESH_TOKEN\
                  --client-access-token=$CLIENT_ACCESS_TOKEN\
                  --admin-login=$ADMIN_LOGIN\
                  --admin-password=$ADMIN_PASSWORD\
                  --client-login=$CLIENT_LOGIN\
                  --client-password=$CLIENT_PASSWORD\
                  --log-level=$LOG_LEVEL
