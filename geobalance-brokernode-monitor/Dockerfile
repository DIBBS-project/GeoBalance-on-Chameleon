FROM python:2.7-slim

WORKDIR /brokernode-monitor
ADD . /brokernode-monitor
RUN pip install --trusted-host pypi.python.org -r requirements.txt

CMD ["python", "-u", "brokernode_monitor.py"]