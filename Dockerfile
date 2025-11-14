FROM python:3.10

SHELL ["/bin/bash", "-c"]

RUN apt update
RUN apt install -y sbcl ripgrep

RUN apt-get install -y expect
WORKDIR /root
RUN curl -O https://beta.quicklisp.org/quicklisp.lisp
COPY quicklisp-install.exp .
RUN chmod +x quicklisp-install.exp
RUN ./quicklisp-install.exp

WORKDIR /root/quicklisp/local-projects/
# RUN git clone https://github.com/genelkim/ulf-lib.git
# RUN git clone https://github.com/genelkim/ttt.git
# RUN git clone https://github.com/genelkim/gute.git

# WORKDIR /root/quicklisp/local-projects/ulf2penman
# COPY requirements.txt .
# RUN pip install -r requirements.txt
# RUN rm -rf requirements.txt

CMD ["bash"]
