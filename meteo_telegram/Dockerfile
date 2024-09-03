FROM python:3

COPY . /
WORKDIR /

RUN apt-get update && apt-get install -y tzdata
ENV TZ=Europe/Kiev
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN pip3 install --no-cache-dir -r requirements.txt

RUN pip3 install yacron

ENTRYPOINT ["yacron", "-c", "crontab.yaml"]