# According to
# https://github.com/cclauss/Travis-CI-Python-on-three-OSes/blob/master/.travis.yml:
# 'python' points to Python 2.7 on macOS, but points to Python 3.7 on Linux and Windows
# 'python3' is a 'command not found' error on Windows, but 'python' works on Windows only

# Install Python3 on Windows
if [ "$TRAVIS_OS_NAME" == windows ]; then
  PATH="/c/Python37:/c/Python37/Scripts:$PATH"
  choco install -y python --version=3.7.5 --allow-downgrades
  python -m pip install --upgrade pip
fi

# Check Python and pip version
if [[ "$TRAVIS_OS_NAME" =~ ^(linux|osx)$ ]]; then
  python3 --version
else # windows
  python --version
fi
pip3 --version

# Create virtual environment
if [[ "$TRAVIS_OS_NAME" =~ ^(linux|osx)$ ]]; then
  python3 -m pip3 install --upgrade virtualenv
  virtualenv -p python3 --system-site-packages $HOME/testenv
else # windows
  python -m pip install --upgrade virtualenv
  virtualenv -p python --system-site-packages $HOME/testenv
fi
source $HOME/testenv/bin/activate

# Install package with pip
pip3 install --upgrade $DEPS $TEST_DEPS
pip3 list installed
