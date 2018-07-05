FROM centos:7

RUN yum update -y && \
    yum install -y \
    wget \
    gcc \
    bzip2-devel \
    sudo \
    tar \
    make \
    zlib-dev
    
RUN yum install -y java-1.8.0-openjdk java-1.8.0-openjdk-devel && \
    yum clean all

RUN cd /tmp && \
    wget https://www.python.org/ftp/python/2.7.15/Python-2.7.15.tgz && \
    tar xvfz Python-2.7.15.tgz && \
    cd Python-2.7.15 && \
    ./configure --prefix=/usr/local && \
    make && \
    make altinstall

RUN cd /tmp && \
    curl "https://bootstrap.pypa.io/get-pip.py" -o "get-pip.py" && \
    python get-pip.py

WORKDIR /geobalance-broker-node
ADD . /geobalance-broker-node

RUN pip install --trusted-host pypi.python.org -r requirements.txt

CMD ["./run.sh"]