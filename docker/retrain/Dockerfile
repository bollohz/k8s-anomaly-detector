FROM conda/miniconda3

MAINTAINER "ls2-team-architecture"

RUN apt update -y
RUN apt install build-essential -y \
	&& apt-get install manpages-dev

# We copy just the requirements.txt first to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . /app

EXPOSE 5000
