ARG BASE
ARG VERSION

FROM ${BASE}

RUN pip3 install rq-scheduler==${VERSION}

ENTRYPOINT ["rqscheduler"]
