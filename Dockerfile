FROM ubuntu:14.04.3

MAINTAINER codemeow codemeow@yahoo.com

RUN cp /etc/apt/sources.list /etc/apt/sources.list.raw
ADD https://github.com/codemeow5/Scripts/raw/master/ubt_1404_aliyun_sources.list /etc/apt/sources.list
RUN apt-get update && apt-get install wget -y

RUN apt-get install python-pip build-essential python-dev -y
RUN pip install tornado
RUN pip install BeautifulSoup4

EXPOSE 80
#VOLUME ['/etc/localtime']

RUN echo Asia/Shanghai > /etc/timezone && dpkg-reconfigure --frontend noninteractive tzdata

COPY web.py /root/
COPY common.py /root/
COPY config.py /root/
RUN mkdir /root/vehiclenet
COPY vehiclenet /root/vehiclenet/
CMD /usr/bin/python /root/web.py -P

