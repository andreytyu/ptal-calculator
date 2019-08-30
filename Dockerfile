FROM python:3.6
LABEL maintainer="Andrey Tyukavin <geotyukavin@gmail.com>"

# Install system dependencies
RUN apt-get -yqq update && apt-get -yqq install \
    libgdal-dev \
    libgeos-dev \
    python-gdal

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app
RUN pip install --no-cache-dir -r requirements.txt

COPY . /usr/src/app

CMD ["python3","-u", "ptal.py"]