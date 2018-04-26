FROM python:3.6.5-slim
MAINTAINER HeyFireball


RUN apt-get update && apt-get install -y \
        build-essential

WORKDIR /app

# Install Requirements
COPY requirements.txt /app
RUN pip3 install -U -r /app/requirements.txt

# Now do rest of work
COPY . /app


#FROM gcr.io/distroless/python3
#EXPOSE 8080
#COPY --from=builder /app /app
WORKDIR /app

CMD ["python", "hey_fireball.py"]

