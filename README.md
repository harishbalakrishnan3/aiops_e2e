# AIOps E2E Testing
End-to-End tests for AIOps

### Installation of Python Dependencies
Poetry is used for managing the Python dependencies. To install the dependencies, run the following command:

```bash
poetry install
```

### Pre-requisites for Behave Tests

1. Add your CDO token in `.env` file located at the project root directory.
2. Download and install promtool and mimirtool by running the shell scripts located in the `utils` directory.
```bash
cd utils
sh ./download_promtool.sh
sh ./download_mimirtool.sh
```

### Running Behave Tests

If you are using PyCharm full-version, you can right-click and run the feature file. 

If you want to run it through the
terminal, you can run the following command:

```bash
# To run all the features
poetry run behave

# To run a specific feature
poetry run behave features/000_Onboard.feature 
```