# AIOps E2E Testing

End-to-End tests for AIOps

### Formatting files

#### To format the files manually

```bash
pre-commit run --all-files
```

#### To Automatically run the formatter pre commit run:

```bash
pre-commit install
```

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
sh ./download_prometheus.sh
sh ./download_mimirtool.sh
```
3. Getting a helios token -> https://cisco.sharepoint.com/sites/HeliosAI/SitePages/How-to-use-Api-key-to-call-Helios-Api.aspx

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