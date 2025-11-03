import os
import csv
import glob
import re
from typing import Dict, Any
from log_extractor import DEFAULT_FILTERS


class ContextInjector:
    def __init__(self, domain_knowledge_path: str = "domain_knowledge"):
        self.domain_knowledge_path = domain_knowledge_path

    def extract_feature_and_scenario(self, user_prompt: str) -> tuple[str, str]:
        """Extract feature and scenario names from user prompt."""
        # Look for pattern like "SCENARIO_NAME scenario of the FEATURE_NAME feature"
        pattern = r"(\w+)\s+scenario\s+of\s+the\s+(\w+)\s+feature"
        match = re.search(pattern, user_prompt, re.IGNORECASE)

        if match:
            scenario_name = match.group(1).upper()
            feature_name = match.group(2)
            return feature_name, scenario_name

        # Fallback: look for common patterns in prompts
        # This is a more flexible approach for different prompt formats
        words = user_prompt.split()
        feature_name = None
        scenario_name = None

        # Look for feature patterns
        for i, word in enumerate(words):
            if "flow" in word.lower() and i > 0:
                # Check if previous word + current word forms a feature name
                potential_feature = f"{words[i - 1]}_{word}"
                if self._feature_exists(potential_feature):
                    feature_name = potential_feature
                    break

        # Look for scenario patterns in uppercase
        for word in words:
            if word.isupper() and len(word) > 3:
                if self._scenario_exists(feature_name, word):
                    scenario_name = word
                    break

        return (
            feature_name or "100_ElephantFlows",
            scenario_name or "ELEPHANTFLOW_ENHANCED",
        )

    def _feature_exists(self, feature_name: str) -> bool:
        """Check if feature directory exists."""
        return os.path.exists(os.path.join(self.domain_knowledge_path, feature_name))

    def _scenario_exists(self, feature_name: str, scenario_name: str) -> bool:
        """Check if scenario directory exists within feature."""
        if not feature_name:
            return False
        return os.path.exists(
            os.path.join(self.domain_knowledge_path, feature_name, scenario_name)
        )

    def load_microservices(self, feature_name: str) -> str:
        """Load microservices from the feature's microservices.txt file."""
        microservices_path = os.path.join(
            self.domain_knowledge_path, feature_name, "microservices.txt"
        )

        try:
            with open(microservices_path, "r", encoding="utf-8") as f:
                microservices = f.read().strip()
                return microservices
        except FileNotFoundError:
            print(f"Warning: microservices.txt not found for feature {feature_name}")
            return ""
        except Exception as e:
            print(f"Error reading microservices for {feature_name}: {str(e)}")
            return ""

    def update_filters(self, microservices: str) -> str:
        """Update DEFAULT_FILTERS with the microservices and return the updated content."""
        try:
            # Use DEFAULT_FILTERS from log_extractor instead of reading from file
            filters_content = DEFAULT_FILTERS

            # Replace the {microservices} placeholder
            updated_filters = filters_content.replace("{microservices}", microservices)

            return updated_filters

        except Exception as e:
            print(f"Error updating filters: {str(e)}")
            return ""

    def load_successful_runs(self, feature_name: str, scenario_name: str) -> str:
        """Load successful runs from the scenario's successful_runs directory."""
        successful_runs_path = os.path.join(
            self.domain_knowledge_path, feature_name, scenario_name, "successful_runs"
        )

        if not os.path.exists(successful_runs_path):
            return f"No successful runs directory found for {feature_name}/{scenario_name}."

        # Look for CSV files in the successful_runs directory
        csv_files = glob.glob(os.path.join(successful_runs_path, "*.csv"))

        if not csv_files:
            return f"No CSV files found in successful runs for {feature_name}/{scenario_name}."

        all_examples = []

        for csv_file_path in sorted(csv_files):
            try:
                filename = os.path.basename(csv_file_path)
                filename_without_ext = os.path.splitext(filename)[0]
                heading = filename_without_ext.replace("_", " ").title()

                with open(csv_file_path, "r", newline="", encoding="utf-8") as csvfile:
                    csv_reader = csv.reader(csvfile)
                    rows = list(csv_reader)

                    if rows:
                        example_content = f"\n=== {heading} ===\n\n"

                        # Add header if exists
                        if len(rows) > 0:
                            example_content += "Headers: " + " | ".join(rows[0]) + "\n"
                            example_content += "-" * 80 + "\n"

                        # Add data rows (limit to first 5 for brevity)
                        for i, row in enumerate(rows[1:], 1):
                            example_content += f"Row {i}: " + " | ".join(row) + "\n"

                        all_examples.append(example_content)
                    else:
                        all_examples.append(
                            f"\n=== {heading} ===\n\nCSV file appears to be empty.\n"
                        )

            except Exception as e:
                filename = os.path.basename(csv_file_path)
                filename_without_ext = os.path.splitext(filename)[0]
                heading = filename_without_ext.replace("_", " ").title()
                all_examples.append(
                    f"\n=== {heading} ===\n\nError reading file: {str(e)}\n"
                )

        if all_examples:
            return f"Examples from successful runs:\n" + "\n".join(all_examples)
        else:
            return "CSV files found but no readable content available."

    def load_context(self, feature_name: str, scenario_name: str) -> str:
        """Load context from the scenario's context.md file."""
        context_path = os.path.join(
            self.domain_knowledge_path, feature_name, scenario_name, "context.md"
        )

        try:
            with open(context_path, "r", encoding="utf-8") as f:
                context_content = f.read().strip()
                return (
                    context_content
                    if context_content
                    else f"Context file is empty for {feature_name}/{scenario_name}."
                )
        except FileNotFoundError:
            return f"No context.md file found for {feature_name}/{scenario_name}."
        except Exception as e:
            return (
                f"Error reading context.md for {feature_name}/{scenario_name}: {str(e)}"
            )

    def inject_context(self, user_prompt: str) -> Dict[str, Any]:
        """Extract context from user prompt and inject relevant data."""
        feature_name, scenario_name = self.extract_feature_and_scenario(user_prompt)

        print(f"Detected feature: {feature_name}, scenario: {scenario_name}")

        # Load microservices and update filters
        microservices = self.load_microservices(feature_name)
        updated_filters = self.update_filters(microservices)

        # Load successful runs
        successful_runs = self.load_successful_runs(feature_name, scenario_name)

        # Load context
        context = self.load_context(feature_name, scenario_name)

        return {
            "feature_name": feature_name,
            "scenario_name": scenario_name,
            "microservices": microservices,
            "updated_filters": updated_filters,
            "successful_runs": successful_runs,
            "context": context,
        }
