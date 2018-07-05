FROM python:2.7-slim

WORKDIR /brokernode-manager
ADD . /brokernode-manager
RUN pip install --trusted-host pypi.python.org -r requirements.txt

EXPOSE 80
CMD ["python", "-u", "brokernode_manager.py"]