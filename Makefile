.PHONY: help backfill backfill-21d backfill-7d backfill-1d test-backfill push-live push-live-30m push-live-1h push-live-2h test-push clean install format lint

METRIC_NAME ?= vpn
LABELS ?= instance=127.0.0.2:9273,job=metrics_generator:8123
TREND_COEFFICIENT ?= 0.1
DESCRIPTION ?= "Backfilled metric data"
DURATION ?= 30

help:
	@echo "Available targets:"
	@echo ""
	@echo "Backfill Commands (historical data):"
	@echo "  make backfill          - Run backfill with custom parameters"
	@echo "  make backfill-21d      - Backfill 21 days of data (default for RAVPN)"
	@echo "  make backfill-7d       - Backfill 7 days of data"
	@echo "  make backfill-1d       - Backfill 1 day of data"
	@echo "  make test-backfill     - Test backfill script with help command"
	@echo ""
	@echo "Live Push Commands (real-time data):"
	@echo "  make push-live         - Push live metrics with custom duration"
	@echo "  make push-live-30m     - Push live metrics for 30 minutes"
	@echo "  make push-live-1h      - Push live metrics for 1 hour (60 minutes)"
	@echo "  make push-live-2h      - Push live metrics for 2 hours (120 minutes)"
	@echo "  make test-push         - Test push script with help command"
	@echo ""
	@echo "Utility Commands:"
	@echo "  make clean             - Clean up generated files"
	@echo "  make install           - Install dependencies with Poetry"
	@echo "  make format            - Format code with Black"
	@echo "  make lint              - Run linting checks"
	@echo ""
	@echo "Variables (with defaults):"
	@echo "  METRIC_NAME=$(METRIC_NAME)"
	@echo "  LABELS=$(LABELS)"
	@echo "  TREND_COEFFICIENT=$(TREND_COEFFICIENT)"
	@echo "  DESCRIPTION=$(DESCRIPTION)"
	@echo "  DURATION=$(DURATION) (for live push, in minutes)"
	@echo "  START_EPOCH=<calculated based on target> (for backfill)"
	@echo "  END_EPOCH=<calculated based on target> (for backfill)"
	@echo ""
	@echo "Examples:"
	@echo "  make backfill METRIC_NAME=cpu LABELS='cpu=lina_cp_avg,uuid=abc123' START_EPOCH=1702800000 END_EPOCH=1704614400"
	@echo "  make backfill-21d METRIC_NAME=vpn LABELS='instance=127.0.0.2:9273,uuid=xyz789,vpn=active_ravpn_tunnels'"
	@echo "  make push-live METRIC_NAME=cpu LABELS='cpu=lina_cp_avg,uuid=abc123' DURATION=60"
	@echo "  make push-live-1h METRIC_NAME=memory LABELS='mem=used_percentage_lina,uuid=xyz789'"

install:
	poetry install

format:
	poetry run black features/ scripts/

lint:
	poetry run black --check features/ scripts/

test-backfill:
	poetry run python scripts/backfill.py --help

test-push:
	poetry run python scripts/push_live_metrics.py --help

push-live:
	@if [ -z "$(DURATION)" ]; then \
		echo "Error: DURATION is required (in minutes)"; \
		echo "Example: make push-live DURATION=60"; \
		exit 1; \
	fi
	poetry run python scripts/push_live_metrics.py \
		--metric-name $(METRIC_NAME) \
		--labels "$(LABELS)" \
		--duration $(DURATION) \
		--trend-coefficient $(TREND_COEFFICIENT) \
		--description $(DESCRIPTION)

push-live-30m:
	@echo "Pushing live metrics for 30 minutes (1 datapoint per minute)"
	poetry run python scripts/push_live_metrics.py \
		--metric-name $(METRIC_NAME) \
		--labels "$(LABELS)" \
		--duration 30 \
		--trend-coefficient $(TREND_COEFFICIENT) \
		--description $(DESCRIPTION)

push-live-1h:
	@echo "Pushing live metrics for 1 hour (60 minutes, 1 datapoint per minute)"
	poetry run python scripts/push_live_metrics.py \
		--metric-name $(METRIC_NAME) \
		--labels "$(LABELS)" \
		--duration 60 \
		--trend-coefficient $(TREND_COEFFICIENT) \
		--description $(DESCRIPTION)

push-live-2h:
	@echo "Pushing live metrics for 2 hours (120 minutes, 1 datapoint per minute)"
	poetry run python scripts/push_live_metrics.py \
		--metric-name $(METRIC_NAME) \
		--labels "$(LABELS)" \
		--duration 120 \
		--trend-coefficient $(TREND_COEFFICIENT) \
		--description $(DESCRIPTION)

backfill:
	@if [ -z "$(START_EPOCH)" ]; then \
		echo "Error: START_EPOCH is required"; \
		echo "Example: make backfill START_EPOCH=1702800000 END_EPOCH=1704614400"; \
		exit 1; \
	fi
	@if [ -z "$(END_EPOCH)" ]; then \
		echo "Error: END_EPOCH is required"; \
		echo "Example: make backfill START_EPOCH=1702800000 END_EPOCH=1704614400"; \
		exit 1; \
	fi
	poetry run python scripts/backfill.py \
		--metric-name $(METRIC_NAME) \
		--labels "$(LABELS)" \
		--start-epoch $(START_EPOCH) \
		--end-epoch $(END_EPOCH) \
		--trend-coefficient $(TREND_COEFFICIENT) \
		--description $(DESCRIPTION)

backfill-21d:
	@START_EPOCH=$$(date -v-21d +%s); \
	END_EPOCH=$$(date +%s); \
	echo "Backfilling 21 days of data ($$START_EPOCH to $$END_EPOCH)"; \
	poetry run python scripts/backfill.py \
		--metric-name $(METRIC_NAME) \
		--labels "$(LABELS)" \
		--start-epoch $$START_EPOCH \
		--end-epoch $$END_EPOCH \
		--trend-coefficient $(TREND_COEFFICIENT) \
		--description $(DESCRIPTION)

backfill-7d:
	@START_EPOCH=$$(date -v-7d +%s); \
	END_EPOCH=$$(date +%s); \
	echo "Backfilling 7 days of data ($$START_EPOCH to $$END_EPOCH)"; \
	poetry run python scripts/backfill.py \
		--metric-name $(METRIC_NAME) \
		--labels "$(LABELS)" \
		--start-epoch $$START_EPOCH \
		--end-epoch $$END_EPOCH \
		--trend-coefficient $(TREND_COEFFICIENT) \
		--description $(DESCRIPTION)

backfill-1d:
	@START_EPOCH=$$(date -v-1d +%s); \
	END_EPOCH=$$(date +%s); \
	echo "Backfilling 1 day of data ($$START_EPOCH to $$END_EPOCH)"; \
	poetry run python scripts/backfill.py \
		--metric-name $(METRIC_NAME) \
		--labels "$(LABELS)" \
		--start-epoch $$START_EPOCH \
		--end-epoch $$END_EPOCH \
		--trend-coefficient $(TREND_COEFFICIENT) \
		--description $(DESCRIPTION)

clean:
	@echo "Cleaning up generated files..."
	rm -f utils/*_historical_data.txt
	rm -f utils/*_backfill_*.txt
	rm -rf utils/*_data/
	rm -rf utils/*_backfill_data/
	@echo "Done!"
