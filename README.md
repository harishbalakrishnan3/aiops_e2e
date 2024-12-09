# e2e
End-to-End tests for AIOps

### Installation of Python Dependencies
Poetry is used for managing the Python dependencies. To install the dependencies, run the following command:

```bash
poetry install
```

### Pre-requisites for Behave Tests

1. Add your CDO token in `.env` file located at the project root directory.
2. Install [promtool](https://prometheus.io/docs/prometheus/latest/command-line/promtool/)
   and [mimirtool](https://grafana.com/docs/mimir/latest/manage/tools/mimirtool/). This is
   required for backfilling metrics to Grafana.

   i. To install mimirtool, follow the instructions
   mentioned [here](https://grafana.com/docs/mimir/latest/manage/tools/mimirtool/#installation). Ensure promtool is
   added in your PATH.

   ii. To install promtool, download the latest stable version of Prometheus artifacts that are compatible with your OS
   and architecture from [here](https://github.com/prometheus/prometheus/releases). Untar the downloaded file and copy
   the `promtool` binary to `/usr/local/bin` or any other directory in your PATH.

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