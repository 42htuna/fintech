FROM debian:trixie
    
# 1. Python derleme bağımlılıklarını ve pyenv için gerekli araçları kurun
RUN apt-get update && apt-get install -y \
    git \
    curl \
    make \
    build-essential \
    libssl-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    libffi-dev \
    liblzma-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Pyenv'i yükleyin
ENV PYENV_ROOT="/root/.pyenv"
ENV PATH="$PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH"

RUN curl https://pyenv.run | bash

# 3. İstediğiniz Python sürümünü pyenv ile indirin ve derleyin
ENV PYTHON_VERSION=3.14.6
RUN pyenv install $PYTHON_VERSION && \
    pyenv global $PYTHON_VERSION

# 4. Pip bileşenlerini güncelleyin (Derlenen sürümün kendi pip'idir, sisteme dokunmaz)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# 5. Proje dosyalarını hazırlayın
WORKDIR /opt/fintech/
COPY requirements.txt .

# Paketleri kurun (PEP 668 engeline takılmaz, çünkü bağımsız bir Python'dır)
RUN pip install --no-cache-dir -r requirements.txt

# Projenin geri kalanını kopyalayın
COPY . .

# Django komutları artık pyenv'in ayağa kaldırdığı Python 3.14.6 ile çalışır
RUN python manage.py collectstatic --noinput
RUN python manage.py makemigrations investments
RUN python manage.py makemigrations
RUN python manage.py migrate

CMD ["bash", "start.sh"]
