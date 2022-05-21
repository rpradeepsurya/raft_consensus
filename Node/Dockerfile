FROM python:3.7-alpine3.14
EXPOSE 5555
EXPOSE 5554
ADD . /dsweb
WORKDIR /dsweb
RUN pip install -r requirements.txt
ENTRYPOINT ["python", "-u", "app.py"]
