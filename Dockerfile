FROM gorialis/discord.py:minimal

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install necessary packages for csdr and netcat
RUN apt-get update && apt-get install -y build-essential libfftw3-dev netcat && rm -rf /var/lib/apt/lists/*

# Download and compile csdr
RUN git clone https://github.com/ha7ilm/csdr.git
RUN cd csdr && make && make install

COPY atcbot.py .

CMD ["python", "atcbot.py"]