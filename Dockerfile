ARG BASE

FROM ${BASE}

ARG VERSION

RUN pip3 install rq-scheduler==${VERSION}

ENTRYPOINT ["rqscheduler"]
