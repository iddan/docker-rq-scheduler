FROM python:3.6

ARG VERSION

RUN pip3 install rq-scheduler==${VERSION}

ENTRYPOINT ["rqscheduler"]
