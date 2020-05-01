# Configure conda
if [[ "$TRAVIS_OS_NAME" =~ ^(linux|osx)$ ]]; then
  source $HOME/miniconda/bin/activate root
fi

conda update --yes conda
conda config --append channels conda-forge
conda create --name testenv --yes python=$PYTHON_VERSION

if [[ "$TRAVIS_OS_NAME" =~ ^(linux|osx)$ ]]; then
  conda activate testenv
else # windows
  . activate testenv
fi

# Install package with conda
conda install --yes $DEPS $TEST_DEPS
conda info
