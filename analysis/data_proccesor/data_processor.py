from abc import ABC, abstractmethod
import os
import tempfile
import shutil
import re


class PipelineStage(ABC):
    @abstractmethod
    def process(self):
        pass


class LogExtractorStage(PipelineStage):
    INPUT_DIR = "./mock_data/archive"
    OUTPUT_DIR = "./mock_data/analysis/raw"

    def process(self):
        """
        data: str, path to the input directory
        Copies all *_error.txt files to 'analysis' directory from 'archive' directory
        """
        input_dir = self.INPUT_DIR
        analysis_dir = self.OUTPUT_DIR
        os.makedirs(analysis_dir, exist_ok=True)
        for fname in os.listdir(input_dir):
            fpath = os.path.join(input_dir, fname)
            if os.path.isfile(fpath) and fname.endswith("_error.txt"):
                shutil.copy2(fpath, analysis_dir)
        print(f"Copied all *_error.txt files from {input_dir} to {analysis_dir}")


class ScenarioSplitterStage(PipelineStage):
    INPUT_DIR = "./mock_data/analysis/raw"
    OUPUT_DIR = "./mock_data/analysis/processed"

    def split_logs_by_scenario(self, input_path, output_dir):
        scenario_files = {}
        common_lines = []
        current_scenario = None
        in_scenario = False
        in_common = True
        scenario_prefix = "Scenario: "
        failing_prefix = "Failing scenarios:"

        with open(input_path, "r") as infile:
            for line in infile:
                # Detect start of a scenario
                if line.strip().startswith(scenario_prefix):
                    import re

                    raw_name = line.strip()[len(scenario_prefix) :].strip()
                    scenario_name = re.sub(r"[^A-Za-z0-9]+", "_", raw_name).strip("_")
                    current_scenario = scenario_name
                    in_scenario = True
                    in_common = False
                    if scenario_name not in scenario_files:
                        scenario_files[scenario_name] = []
                    scenario_files[scenario_name].append(line)
                    continue
                # Detect start of failing scenarios (end of scenario blocks)
                if line.strip().startswith(failing_prefix):
                    in_scenario = False
                    in_common = True
                    common_lines.append(line)
                    continue
                if in_scenario and current_scenario:
                    scenario_files[current_scenario].append(line)
                else:
                    common_lines.append(line)
        # Write scenario files
        os.makedirs(output_dir, exist_ok=True)
        for scenario, lines in scenario_files.items():
            with open(os.path.join(output_dir, f"scenario_{scenario}.txt"), "w") as f:
                f.writelines(lines)

        # Write common file
        with open(os.path.join(output_dir, "preandpost_logs.txt"), "w") as f:
            f.writelines(common_lines)

    def process(self):
        # transform data
        input_dir = self.INPUT_DIR
        for fname in os.listdir(input_dir):
            # each of the file name (Feature) split into scenarios
            scenario_name = fname.split("_")[0]
            self.split_logs_by_scenario(
                os.path.join(input_dir, fname),
                os.path.join(self.OUPUT_DIR, scenario_name),
            )


class DateCleanupStage(PipelineStage):
    INPUT_DIR = "./mock_data/analysis/processed"

    KEYWORDS = [
        "Exported metric",
        "datapoints through live ingestion",
        "Created gauge",
        '"uploading block file"',
        '"will sleep and try again"',
        '"block uploaded successfully"',
        "Backfilling blocks",
        '"making request to start block upload"',
        '"uploading block file"',
        '"finished uploading blocks"',
    ]

    def should_skip_actual_insight(self, line, skip_json_block, brace_count):
        """
        Determines whether to skip the current line based on the Actual Insight JSON block logic.
        Returns updated (skip_json_block, brace_count, should_skip_line).
        """
        if not skip_json_block and line.lstrip().startswith("Actual Insight :"):
            json_start = line.find("{")
            if json_start != -1:
                brace_count = line[json_start:].count("{") - line[json_start:].count(
                    "}"
                )
                skip_json_block = True
            else:
                skip_json_block = True
                brace_count = 0
            return skip_json_block, brace_count, True
        if skip_json_block:
            brace_count += line.count("{") - line.count("}")
            if brace_count <= 0:
                skip_json_block = False
            return skip_json_block, brace_count, True
        return skip_json_block, brace_count, False

    def filter_lines_inplace(self, file_path):
        skip_json_block = False
        brace_count = 0
        block_ulid_keywords = ["BLOCK ULID", "MIN TIME", "MAX TIME"]
        skip_block = False
        # Regexes to resume writing after block table
        log_pattern = re.compile(r"^\s*\[(.*?)\] \[(.*?)\] (.*)$")
        alt_pattern = re.compile(r"^\s*(\w+):root:(.*)$")
        with tempfile.NamedTemporaryFile("w", delete=False) as tmpfile, open(
            file_path, "r"
        ) as infile:
            for line in infile:
                # Block ULID table detection
                if not skip_block and all(kw in line for kw in block_ulid_keywords):
                    skip_block = True
                    continue
                if skip_block:
                    # Resume if any regex matches
                    if log_pattern.match(line) or alt_pattern.match(line):
                        skip_block = False
                    else:
                        continue
                (
                    skip_json_block,
                    brace_count,
                    should_skip_line,
                ) = self.should_skip_actual_insight(line, skip_json_block, brace_count)
                if should_skip_line:
                    continue
                # Filter out lines with keywords
                if not any(keyword in line for keyword in self.KEYWORDS):
                    tmpfile.write(line)
        os.replace(tmpfile.name, file_path)

    def process(self):
        for root, dirs, files in os.walk(self.INPUT_DIR):
            for file in files:
                self.filter_lines_inplace(os.path.join(root, file))


class Pipeline:
    def __init__(self):
        self.stages = []

    def add_stage(self, stage):
        self.stages.append(stage)
        return self

    def execute(self):
        for stage in self.stages:
            stage.process()


if __name__ == "__main__":
    pipeline = Pipeline()
    pipeline.add_stage(LogExtractorStage())
    pipeline.add_stage(ScenarioSplitterStage())
    pipeline.add_stage(DateCleanupStage())

    result = pipeline.execute()
